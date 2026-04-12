from __future__ import annotations

import unittest
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zoneinfo import ZoneInfo

from paper_digest.arxiv_client import Paper
from paper_digest.config import (
    AnalysisConfig,
    AppConfig,
    DigestConfig,
    FeedbackConfig,
    FeedConfig,
    NotifyConfig,
    RankingConfig,
    RankingWeights,
    StateConfig,
)
from paper_digest.digest import DigestRun, FeedDigest, write_outputs
from paper_digest.feedback import FeedbackEntry, FeedbackState
from paper_digest.service import generate_digest
from paper_digest.state import DigestState


class GenerateDigestTests(unittest.TestCase):
    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_uses_configured_timezone_and_filters(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        recent_paper = Paper(
            title="Agent systems",
            summary="Agent summary",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00001v1",
            abstract_url="https://arxiv.org/abs/2604.00001v1",
            pdf_url="https://arxiv.org/pdf/2604.00001v1",
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        non_matching_paper = Paper(
            title="Compiler optimizations",
            summary="Nothing about the topic",
            authors=["Bob"],
            categories=["cs.PL"],
            paper_id="http://arxiv.org/abs/2604.00002v1",
            abstract_url="https://arxiv.org/abs/2604.00002v1",
            pdf_url=None,
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_feed_papers.return_value = [recent_paper, non_matching_paper]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="Asia/Shanghai",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )

            digest = generate_digest(config, now=now)

        self.assertEqual(digest.generated_at, now)
        self.assertEqual(len(digest.feeds), 1)
        self.assertEqual(
            [paper.title for paper in digest.feeds[0].papers],
            ["Agent systems"],
        )
        mock_fetch_feed_papers.assert_called_once_with(
            feed,
            now=now.astimezone(ZoneInfo("UTC")),
            lookback_hours=24,
            request_delay_seconds=0.0,
            request_timeout_seconds=60,
            retry_attempts=4,
            retry_backoff_seconds=10.0,
            contact_email=None,
            openalex_api_key=None,
        )

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_dedupes_against_state(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        paper = Paper(
            title="Agent systems",
            summary="Agent summary",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00001v1",
            abstract_url="https://arxiv.org/abs/2604.00001v1",
            pdf_url="https://arxiv.org/pdf/2604.00001v1",
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_feed_papers.return_value = [paper]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )

            first_digest = generate_digest(config, now=now)
            second_digest = generate_digest(config, now=now)

        self.assertEqual(len(first_digest.feeds[0].papers), 1)
        self.assertEqual(len(second_digest.feeds[0].papers), 0)

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_passes_openalex_api_key_from_env(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="OpenAlex AI",
            source="openalex",
            queries=["agent systems"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        mock_fetch_feed_papers.return_value = []

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
                openalex_api_key_env="OPENALEX_API_KEY",
            )

            with patch.dict("os.environ", {"OPENALEX_API_KEY": "openalex-secret"}):
                generate_digest(config, now=now)

        mock_fetch_feed_papers.assert_called_once_with(
            feed,
            now=now,
            lookback_hours=24,
            request_delay_seconds=0.0,
            request_timeout_seconds=60,
            retry_attempts=4,
            retry_backoff_seconds=10.0,
            contact_email=None,
            openalex_api_key="openalex-secret",
        )

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_merges_cross_feed_duplicates_by_canonical_id(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        arxiv_feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        openalex_feed = FeedConfig(
            name="OpenAlex AI",
            source="openalex",
            queries=["agent systems"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        arxiv_paper = Paper(
            title="Agent systems",
            summary="Short summary.",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00001v1",
            abstract_url="https://arxiv.org/abs/2604.00001v1",
            pdf_url="https://arxiv.org/pdf/2604.00001v1",
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            source="arxiv",
            doi="10.5555/example",
        )
        openalex_paper = Paper(
            title="Agent systems",
            summary="Longer and more complete summary for the same paper.",
            authors=["Alice", "Bob"],
            categories=["Artificial Intelligence"],
            paper_id="openalex:W123",
            abstract_url="https://doi.org/10.5555/example",
            pdf_url=None,
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 1, 0, tzinfo=ZoneInfo("UTC")),
            source="openalex",
            date_label="Published",
            doi="10.5555/example",
        )
        mock_fetch_feed_papers.side_effect = [[arxiv_paper], [openalex_paper]]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[arxiv_feed, openalex_feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )

            digest = generate_digest(config, now=now)

        self.assertEqual(len(digest.feeds[0].papers), 1)
        self.assertEqual(len(digest.feeds[1].papers), 0)
        merged_paper = digest.feeds[0].papers[0]
        self.assertEqual(
            merged_paper.source_variants,
            ["arxiv", "openalex"],
        )
        self.assertIn("seen in 2 sources", merged_paper.match_reasons)
        self.assertEqual(
            merged_paper.summary,
            "Longer and more complete summary for the same paper.",
        )
        self.assertEqual(merged_paper.pdf_url, "https://arxiv.org/pdf/2604.00001v1")
        self.assertEqual(merged_paper.authors, ["Alice", "Bob"])
        self.assertEqual(merged_paper.canonical_id(), "doi:10.5555/example")
        self.assertGreater(merged_paper.relevance_score, 80)

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_boosts_starred_papers(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        starred = Paper(
            title="Agent planning with verification",
            summary="Agent planning benchmark.",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00002v1",
            abstract_url="https://arxiv.org/abs/2604.00002v1",
            pdf_url="https://arxiv.org/pdf/2604.00002v1",
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        unstarred = Paper(
            title="Agent benchmark recap",
            summary="A fresh agent benchmark.",
            authors=["Bob"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00003v1",
            abstract_url="https://arxiv.org/abs/2604.00003v1",
            pdf_url="https://arxiv.org/pdf/2604.00003v1",
            published_at=datetime(2026, 4, 8, 6, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 6, 30, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_feed_papers.return_value = [starred, unstarred]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )
            feedback_state = FeedbackState(
                papers={
                    "arxiv:2604.00002": FeedbackEntry(status="star"),
                }
            )

            digest = generate_digest(
                config,
                now=now,
                feedback_state=feedback_state,
            )

        self.assertEqual(
            [paper.title for paper in digest.feeds[0].papers],
            ["Agent planning with verification", "Agent benchmark recap"],
        )
        self.assertEqual(digest.feeds[0].papers[0].feedback_status, "star")
        self.assertIn("feedback: starred", digest.feeds[0].papers[0].match_reasons)
        self.assertGreater(
            digest.feeds[0].papers[0].relevance_score,
            digest.feeds[0].papers[1].relevance_score,
        )

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_hides_ignored_papers_by_default(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        ignored = Paper(
            title="Ignored agent paper",
            summary="An agent paper that should disappear.",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00004v1",
            abstract_url="https://arxiv.org/abs/2604.00004v1",
            pdf_url="https://arxiv.org/pdf/2604.00004v1",
            published_at=datetime(2026, 4, 8, 3, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 3, 30, tzinfo=ZoneInfo("UTC")),
        )
        visible = Paper(
            title="Visible agent paper",
            summary="An agent paper that remains.",
            authors=["Bob"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00005v1",
            abstract_url="https://arxiv.org/abs/2604.00005v1",
            pdf_url="https://arxiv.org/pdf/2604.00005v1",
            published_at=datetime(2026, 4, 8, 4, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 4, 30, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_feed_papers.return_value = [ignored, visible]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )
            feedback_state = FeedbackState(
                papers={
                    "arxiv:2604.00004": FeedbackEntry(status="ignore"),
                }
            )

            digest = generate_digest(
                config,
                now=now,
                feedback_state=feedback_state,
            )

        self.assertEqual(
            [paper.title for paper in digest.feeds[0].papers],
            ["Visible agent paper"],
        )

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_can_keep_ignored_papers_with_penalty(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        ignored = Paper(
            title="Ignored agent paper",
            summary="An agent paper that should be down-ranked.",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00006v1",
            abstract_url="https://arxiv.org/abs/2604.00006v1",
            pdf_url="https://arxiv.org/pdf/2604.00006v1",
            published_at=datetime(2026, 4, 8, 6, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 6, 30, tzinfo=ZoneInfo("UTC")),
        )
        baseline = Paper(
            title="Baseline agent paper",
            summary="An agent paper without feedback.",
            authors=["Bob"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00007v1",
            abstract_url="https://arxiv.org/abs/2604.00007v1",
            pdf_url="https://arxiv.org/pdf/2604.00007v1",
            published_at=datetime(2026, 4, 8, 4, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 4, 30, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_feed_papers.return_value = [ignored, baseline]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
                feedback=FeedbackConfig(
                    enabled=True,
                    path=Path(temp_dir) / "feedback.json",
                    hide_ignored=False,
                    ignore_penalty=120,
                ),
            )
            feedback_state = FeedbackState(
                papers={
                    "arxiv:2604.00006": FeedbackEntry(status="ignore"),
                }
            )

            digest = generate_digest(
                config,
                now=now,
                feedback_state=feedback_state,
            )

        self.assertEqual(
            [paper.title for paper in digest.feeds[0].papers],
            ["Baseline agent paper", "Ignored agent paper"],
        )
        ignored_paper = digest.feeds[0].papers[1]
        self.assertEqual(ignored_paper.feedback_status, "ignore")
        self.assertIn("feedback: ignored", ignored_paper.match_reasons)

    @patch("paper_digest.service.save_state")
    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_does_not_persist_when_state_is_provided(
        self,
        mock_fetch_feed_papers,
        mock_save_state,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        paper = Paper(
            title="Agent systems",
            summary="Agent summary",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00001v1",
            abstract_url="https://arxiv.org/abs/2604.00001v1",
            pdf_url="https://arxiv.org/pdf/2604.00001v1",
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_feed_papers.return_value = [paper]
        state = DigestState(seen_papers={})

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )

            digest = generate_digest(config, now=now, state=state)

        self.assertEqual(len(digest.feeds[0].papers), 1)
        self.assertIn(feed.name, state.seen_papers)
        mock_save_state.assert_not_called()

    @patch("paper_digest.service.enrich_digest_with_analysis")
    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_runs_analysis_when_configured(
        self,
        mock_fetch_feed_papers,
        mock_enrich_digest_with_analysis,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        paper = Paper(
            title="Agent systems",
            summary="Agent summary",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00001v1",
            abstract_url="https://arxiv.org/abs/2604.00001v1",
            pdf_url="https://arxiv.org/pdf/2604.00001v1",
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_feed_papers.return_value = [paper]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
                analysis=AnalysisConfig(
                    provider="openai",
                    model="gpt-5-mini",
                    api_key_env="OPENAI_API_KEY",
                    base_url="https://api.openai.com/v1/responses",
                    timeout_seconds=60,
                    max_papers=10,
                    max_output_tokens=600,
                    language="English",
                    reasoning_effort="minimal",
                ),
                digest=DigestConfig(template="zh_daily_brief"),
            )

            digest = generate_digest(config, now=now)

        self.assertEqual(len(digest.feeds[0].papers), 1)
        self.assertEqual(digest.template, "zh_daily_brief")
        mock_enrich_digest_with_analysis.assert_called_once()
        kwargs = mock_enrich_digest_with_analysis.call_args.kwargs
        self.assertEqual(kwargs["topic_candidates"], ["agent"])

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_builds_zh_daily_brief_without_analysis(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        paper = Paper(
            title="Agent systems",
            summary="A benchmark for agent evaluation.",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00001v1",
            abstract_url="https://arxiv.org/abs/2604.00001v1",
            pdf_url="https://arxiv.org/pdf/2604.00001v1",
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_feed_papers.return_value = [paper]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
                digest=DigestConfig(
                    template="zh_daily_brief",
                    top_highlights=2,
                    feed_key_points=1,
                ),
            )

            digest = generate_digest(config, now=now)

        self.assertEqual(digest.template, "zh_daily_brief")
        self.assertEqual(
            digest.highlights,
            [
                "主题「Agent」：命中 1 篇，覆盖 LLM，代表论文包括 《Agent systems》。"
            ],
        )
        self.assertEqual(
            digest.feeds[0].key_points,
            ["《Agent systems》〔评测 / 方法〕：A benchmark for agent evaluation."],
        )
        self.assertEqual(digest.topic_sections[0].name, "Agent")

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_applies_configured_sorting_summary(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
            sort_by="published_at",
        )
        mock_fetch_feed_papers.return_value = [
            Paper(
                title="Agent systems",
                summary="Agent summary",
                authors=["Alice"],
                categories=["cs.AI"],
                paper_id="http://arxiv.org/abs/2604.00001v1",
                abstract_url="https://arxiv.org/abs/2604.00001v1",
                pdf_url="https://arxiv.org/pdf/2604.00001v1",
                published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
                updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            )
        ]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
                ranking=RankingConfig(
                    sort_by="hybrid",
                    weights=RankingWeights(multi_source_weight=12),
                ),
            )

            digest = generate_digest(config, now=now)

        self.assertEqual(digest.default_sort_by, "hybrid")
        self.assertEqual(digest.feeds[0].sort_by, "published_at")
        self.assertEqual(
            digest.sort_summary,
            "published_at (newest first; relevance is auxiliary)",
        )
        self.assertEqual(digest.ranking_weights["multi_source_weight"], 12)

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_builds_feedback_focus_items(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 9, 9, 30, tzinfo=ZoneInfo("UTC"))
        llm_feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        pubmed_feed = FeedConfig(
            name="PubMed AI",
            source="pubmed",
            queries=["large language model"],
            keywords=["language model"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        starred_paper = Paper(
            title="Paper Circle",
            summary="Research discovery framework for agent systems.",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.06170v1",
            abstract_url="https://arxiv.org/abs/2604.06170v1",
            pdf_url="https://arxiv.org/pdf/2604.06170v1",
            published_at=datetime(2026, 4, 9, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 9, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        follow_up_paper = Paper(
            title="ClinicRealm language model benchmark",
            summary="Clinical prediction benchmark for large language models.",
            authors=["Bob"],
            categories=["Journal Article"],
            paper_id="pubmed:41951858",
            abstract_url="https://pubmed.ncbi.nlm.nih.gov/41951858/",
            pdf_url=None,
            published_at=datetime(2026, 4, 9, 1, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 9, 1, 30, tzinfo=ZoneInfo("UTC")),
            source="pubmed",
        )
        follow_up_canonical_id = follow_up_paper.canonical_id()
        mock_fetch_feed_papers.side_effect = [[starred_paper], [follow_up_paper]]

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            history_config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=output_dir,
                request_delay_seconds=0.0,
                feeds=[llm_feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "history-state.json",
                    retention_days=90,
                ),
            )
            history_digest = DigestRun(
                generated_at=datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC")),
                timezone="UTC",
                lookback_hours=24,
                feeds=[FeedDigest(name="LLM", papers=[starred_paper])],
            )
            write_outputs(history_config, history_digest)

            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=output_dir,
                request_delay_seconds=0.0,
                feeds=[llm_feed, pubmed_feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )
            state = DigestState(
                seen_papers={
                    "PubMed AI": {
                        follow_up_canonical_id: "2026-04-08T09:30:00+00:00",
                    }
                }
            )
            feedback_state = FeedbackState(
                papers={
                    "arxiv:2604.06170": FeedbackEntry(
                        status="star",
                        updated_at=datetime(2026, 4, 9, 8, 0, tzinfo=ZoneInfo("UTC")),
                        note="seed paper for the agent track",
                    ),
                    follow_up_canonical_id: FeedbackEntry(
                        status="follow_up",
                        updated_at=datetime(2026, 4, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
                        note="recheck if this resurfaces",
                    ),
                }
            )

            digest = generate_digest(
                config,
                now=now,
                state=state,
                feedback_state=feedback_state,
            )

        self.assertEqual(len(digest.focus_items), 2)
        focus_by_id = {item.canonical_id: item for item in digest.focus_items}
        self.assertEqual(
            focus_by_id["arxiv:2604.06170"].reasons,
            ["new_starred", "starred_momentum"],
        )
        self.assertEqual(
            focus_by_id["arxiv:2604.06170"].feedback_note,
            "seed paper for the agent track",
        )
        self.assertIn("LLM", focus_by_id["arxiv:2604.06170"].feed_names)
        self.assertEqual(
            focus_by_id[follow_up_canonical_id].reasons,
            ["follow_up_resurfaced"],
        )
        self.assertEqual(
            focus_by_id[follow_up_canonical_id].feedback_note,
            "recheck if this resurfaces",
        )
        self.assertIn("PubMed AI", focus_by_id[follow_up_canonical_id].feed_names)
        self.assertEqual(len(digest.feeds[1].papers), 0)

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_builds_action_items_from_due_dates_and_next_actions(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 9, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        starred_paper = Paper(
            title="Paper Circle",
            summary="Research discovery framework for agent systems.",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.06170v1",
            abstract_url="https://arxiv.org/abs/2604.06170v1",
            pdf_url="https://arxiv.org/pdf/2604.06170v1",
            published_at=datetime(2026, 4, 9, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 9, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        reading_paper = Paper(
            title="Agent Systems",
            summary="Another agent paper for the reading queue.",
            authors=["Bob"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00001v1",
            abstract_url="https://arxiv.org/abs/2604.00001v1",
            pdf_url="https://arxiv.org/pdf/2604.00001v1",
            published_at=datetime(2026, 4, 9, 1, 0, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 9, 1, 0, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_feed_papers.return_value = [starred_paper, reading_paper]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )
            feedback_state = FeedbackState(
                papers={
                    "arxiv:2604.06170": FeedbackEntry(
                        status="star",
                        updated_at=datetime(2026, 4, 9, 8, 0, tzinfo=ZoneInfo("UTC")),
                        note="anchor paper",
                        next_action="compare planner design",
                        due_date=date(2026, 4, 11),
                    ),
                    "arxiv:2604.00001": FeedbackEntry(
                        status="reading",
                        updated_at=datetime(2026, 4, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
                        note="finish sections 3 and 4",
                        due_date=date(2026, 4, 8),
                    ),
                }
            )

            digest = generate_digest(
                config,
                now=now,
                state=DigestState(seen_papers={}),
                feedback_state=feedback_state,
            )

        self.assertEqual(len(digest.action_items), 2)
        self.assertEqual(digest.action_items[0].canonical_id, "arxiv:2604.00001")
        self.assertEqual(digest.action_items[0].reasons, ["overdue"])
        self.assertEqual(digest.action_items[0].days_until_due, -1)
        self.assertEqual(digest.action_items[1].canonical_id, "arxiv:2604.06170")
        self.assertEqual(
            digest.action_items[1].reasons,
            ["due_soon", "next_action_pending"],
        )
        self.assertEqual(
            digest.action_items[1].next_action,
            "compare planner design",
        )

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_can_filter_action_items_by_due_window(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 9, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        papers = [
            Paper(
                title="Overdue Reading",
                summary="Agent paper with an overdue task.",
                authors=["Alice"],
                categories=["cs.AI"],
                paper_id="http://arxiv.org/abs/2604.00001v1",
                abstract_url="https://arxiv.org/abs/2604.00001v1",
                pdf_url="https://arxiv.org/pdf/2604.00001v1",
                published_at=datetime(2026, 4, 9, 1, 0, tzinfo=ZoneInfo("UTC")),
                updated_at=datetime(2026, 4, 9, 1, 0, tzinfo=ZoneInfo("UTC")),
            ),
            Paper(
                title="Due Soon Planning",
                summary="Agent paper with a due-soon action.",
                authors=["Bob"],
                categories=["cs.AI"],
                paper_id="http://arxiv.org/abs/2604.06170v1",
                abstract_url="https://arxiv.org/abs/2604.06170v1",
                pdf_url="https://arxiv.org/pdf/2604.06170v1",
                published_at=datetime(2026, 4, 9, 0, 30, tzinfo=ZoneInfo("UTC")),
                updated_at=datetime(2026, 4, 9, 0, 30, tzinfo=ZoneInfo("UTC")),
            ),
            Paper(
                title="Far Future Follow Up",
                summary="Agent paper with a later due date.",
                authors=["Carol"],
                categories=["cs.AI"],
                paper_id="http://arxiv.org/abs/2604.00002v1",
                abstract_url="https://arxiv.org/abs/2604.00002v1",
                pdf_url="https://arxiv.org/pdf/2604.00002v1",
                published_at=datetime(2026, 4, 9, 2, 0, tzinfo=ZoneInfo("UTC")),
                updated_at=datetime(2026, 4, 9, 2, 0, tzinfo=ZoneInfo("UTC")),
            ),
        ]
        mock_fetch_feed_papers.return_value = papers

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
                notify=NotifyConfig(
                    action_due_within_days=3,
                    max_action_items=5,
                ),
            )
            feedback_state = FeedbackState(
                papers={
                    "arxiv:2604.00001": FeedbackEntry(
                        status="reading",
                        updated_at=datetime(2026, 4, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
                        due_date=date(2026, 4, 8),
                    ),
                    "arxiv:2604.06170": FeedbackEntry(
                        status="star",
                        updated_at=datetime(2026, 4, 9, 8, 0, tzinfo=ZoneInfo("UTC")),
                        next_action="compare planner design",
                        due_date=date(2026, 4, 11),
                    ),
                    "arxiv:2604.00002": FeedbackEntry(
                        status="follow_up",
                        updated_at=datetime(2026, 4, 8, 10, 0, tzinfo=ZoneInfo("UTC")),
                        next_action="schedule a re-check",
                        due_date=date(2026, 4, 20),
                    ),
                }
            )

            digest = generate_digest(
                config,
                now=now,
                state=DigestState(seen_papers={}),
                feedback_state=feedback_state,
            )

        self.assertEqual(
            [item.canonical_id for item in digest.action_items],
            ["arxiv:2604.00001", "arxiv:2604.06170"],
        )

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_can_limit_action_items_to_overdue_only(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 9, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        mock_fetch_feed_papers.return_value = [
            Paper(
                title="Overdue Reading",
                summary="Agent paper with an overdue task.",
                authors=["Alice"],
                categories=["cs.AI"],
                paper_id="http://arxiv.org/abs/2604.00001v1",
                abstract_url="https://arxiv.org/abs/2604.00001v1",
                pdf_url="https://arxiv.org/pdf/2604.00001v1",
                published_at=datetime(2026, 4, 9, 1, 0, tzinfo=ZoneInfo("UTC")),
                updated_at=datetime(2026, 4, 9, 1, 0, tzinfo=ZoneInfo("UTC")),
            ),
            Paper(
                title="Due Soon Planning",
                summary="Agent paper with a due-soon action.",
                authors=["Bob"],
                categories=["cs.AI"],
                paper_id="http://arxiv.org/abs/2604.06170v1",
                abstract_url="https://arxiv.org/abs/2604.06170v1",
                pdf_url="https://arxiv.org/pdf/2604.06170v1",
                published_at=datetime(2026, 4, 9, 0, 30, tzinfo=ZoneInfo("UTC")),
                updated_at=datetime(2026, 4, 9, 0, 30, tzinfo=ZoneInfo("UTC")),
            ),
        ]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
                notify=NotifyConfig(
                    action_overdue_only=True,
                    max_action_items=5,
                ),
            )
            feedback_state = FeedbackState(
                papers={
                    "arxiv:2604.00001": FeedbackEntry(
                        status="reading",
                        updated_at=datetime(2026, 4, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
                        due_date=date(2026, 4, 8),
                    ),
                    "arxiv:2604.06170": FeedbackEntry(
                        status="star",
                        updated_at=datetime(2026, 4, 9, 8, 0, tzinfo=ZoneInfo("UTC")),
                        next_action="compare planner design",
                        due_date=date(2026, 4, 11),
                    ),
                }
            )

            digest = generate_digest(
                config,
                now=now,
                state=DigestState(seen_papers={}),
                feedback_state=feedback_state,
            )

        self.assertEqual(len(digest.action_items), 1)
        self.assertEqual(digest.action_items[0].canonical_id, "arxiv:2604.00001")
