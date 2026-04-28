from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import patch

from paper_digest.analysis import (
    AnalysisError,
    _analyze_paper,
    _display_topic,
    _extract_paper_topics,
    _extract_topic_terms,
    _format_digest_highlight,
    _format_topic_highlight,
    _normalize_topic_candidates,
    _select_papers_for_analysis,
    _truncate_text,
    build_digest_highlights,
    build_feed_key_points,
    build_topic_sections,
    enrich_digest_with_analysis,
)
from paper_digest.arxiv_client import Paper
from paper_digest.config import AnalysisConfig
from paper_digest.digest import DigestRun, FeedDigest, TopicDigest
from paper_digest.openai_analysis import OpenAIAnalysisError


def build_paper(title: str, *, summary: str | None = None) -> Paper:
    published_at = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)
    return Paper(
        title=title,
        summary=summary if summary is not None else f"{title} summary",
        authors=["Alice"],
        categories=["cs.AI"],
        paper_id=f"https://arxiv.org/abs/{title}",
        abstract_url=f"https://arxiv.org/abs/{title}",
        pdf_url=None,
        published_at=published_at,
        updated_at=published_at,
    )


def build_config() -> AnalysisConfig:
    return AnalysisConfig(
        provider="openai",
        model="gpt-5-mini",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1/responses",
        timeout_seconds=60,
        max_papers=2,
        max_output_tokens=600,
        language="English",
        reasoning_effort="minimal",
    )


class AnalysisAdditionalTests(unittest.TestCase):
    @patch("paper_digest.analysis.analyze_paper_with_openai")
    def test_enrich_digest_with_analysis_skips_analysis_when_max_papers_is_zero(
        self,
        mock_analyze_paper_with_openai,
    ) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[build_paper("Agent benchmark")])],
        )

        enrich_digest_with_analysis(
            replace(build_config(), max_papers=0),
            digest,
            template="default",
            top_highlights=1,
            feed_key_points=1,
        )

        mock_analyze_paper_with_openai.assert_not_called()
        self.assertEqual(
            digest.highlights,
            ["LLM: Agent benchmark - Agent benchmark summary"],
        )

    @patch(
        "paper_digest.analysis.analyze_paper_with_openai",
        side_effect=OpenAIAnalysisError("analysis failed"),
    )
    def test_enrich_digest_with_analysis_wraps_openai_errors(
        self,
        _mock_analyze_paper_with_openai,
    ) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[build_paper("Agent benchmark")])],
        )

        with self.assertRaisesRegex(AnalysisError, "analysis failed"):
            enrich_digest_with_analysis(
                build_config(),
                digest,
                template="default",
                top_highlights=1,
                feed_key_points=1,
            )

    def test_highlight_and_key_point_builders_skip_blank_summary_lines(self) -> None:
        paper = build_paper("Blank summary", summary="   ")
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[paper])],
        )

        self.assertEqual(build_digest_highlights(digest, 2), [])
        self.assertEqual(build_feed_key_points([paper], 2), [])

    def test_topic_and_formatting_helpers_cover_fallbacks_and_display_rules(
        self,
    ) -> None:
        self.assertEqual(
            _normalize_topic_candidates([" agent ", "", "Agent", "多模态"]),
            [("agent", "Agent"), ("多模态", "多模态")],
        )
        self.assertEqual(_display_topic("vision__language"), "Vision Language")
        self.assertEqual(_display_topic("__vision__nlp"), "Vision NLP")
        self.assertEqual(_display_topic("视觉理解"), "视觉理解")
        self.assertEqual(
            _extract_topic_terms("agent AGENT model foo_bar 视觉 视觉"),
            ["Agent", "FOO", "BAR", "视觉"],
        )

        topic_highlight = _format_topic_highlight(
            TopicDigest(
                name="Agent",
                paper_count=3,
                feed_names=["LLM", "Vision", "PubMed"],
                paper_titles=["A", "B"],
            )
        )
        self.assertIn("覆盖 LLM、Vision 等", topic_highlight)
        self.assertEqual(
            _format_digest_highlight(
                "LLM",
                "Agent benchmark",
                "重点摘要",
                "zh_daily_brief",
            ),
            "LLM：关注《Agent benchmark》，今日要点：重点摘要",
        )
        self.assertEqual(_truncate_text("a  b", 10), "a b")
        self.assertEqual(_truncate_text("x" * 12, 10), "xxxxxxxxx…")

    def test_select_and_topic_builders_cover_empty_and_fallback_paths(self) -> None:
        empty_digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[
                FeedDigest(name="LLM", papers=[]),
                FeedDigest(name="Vision", papers=[]),
            ],
        )
        self.assertEqual(_select_papers_for_analysis(empty_digest, 2), [])

        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[
                FeedDigest(name="LLM", papers=[]),
                FeedDigest(
                    name="Vision",
                    papers=[
                        build_paper("Agent planning"),
                        build_paper("Graph planner"),
                    ],
                ),
            ],
        )
        self.assertEqual(
            [paper.title for paper in _select_papers_for_analysis(digest, 2)],
            ["Agent planning", "Graph planner"],
        )

        no_topic_paper = build_paper(
            "with from model",
            summary="about systems with work",
        )
        self.assertEqual(_extract_paper_topics(no_topic_paper, [], {}), [])
        self.assertEqual(build_topic_sections(DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[no_topic_paper])],
        ), max_items=3), [])

        fallback_paper = build_paper(
            "Vision planning",
            summary="Benchmarking planner adapters",
        )
        self.assertEqual(
            _extract_paper_topics(fallback_paper, [], {"Vision": 1, "Planning": 1}),
            ["Vision", "Planning"],
        )

    def test_build_topic_sections_deduplicates_titles_and_key_points(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[
                FeedDigest(
                    name="LLM",
                    papers=[build_paper("Agent benchmark", summary="Same summary")],
                ),
                FeedDigest(
                    name="Vision",
                    papers=[build_paper("Agent benchmark", summary="Same summary")],
                ),
            ],
        )

        sections = build_topic_sections(
            digest,
            max_items=3,
            topic_candidates=["Agent"],
        )

        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].feed_names, ["LLM", "Vision"])
        self.assertEqual(sections[0].paper_titles, ["Agent benchmark"])
        self.assertEqual(sections[0].key_points, ["Agent benchmark: Same summary"])

    def test_analyze_paper_rejects_unsupported_provider(self) -> None:
        with self.assertRaisesRegex(AnalysisError, "unsupported analysis provider"):
            _analyze_paper(
                replace(build_config(), provider="custom"),
                build_paper("Agent benchmark"),
                template="default",
            )
