from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.arxiv_client import Paper, PaperAnalysis
from paper_digest.config import (
    AnalysisConfig,
    AppConfig,
    FeedConfig,
    RankingConfig,
    RankingWeights,
    StateConfig,
)
from paper_digest.digest import (
    DigestRun,
    FeedDigest,
    FocusItem,
    TopicDigest,
    filter_papers,
    render_markdown,
    render_notification_markdown,
    summarize_digest,
    summarize_focus_items,
    write_outputs,
)


def build_paper(
    *,
    title: str,
    summary: str,
    hours_ago: int,
    authors: list[str] | None = None,
    paper_id: str = "http://arxiv.org/abs/2604.00001v1",
    abstract_url: str = "https://arxiv.org/abs/2604.00001v1",
    pdf_url: str | None = "https://arxiv.org/pdf/2604.00001v1",
    source: str = "arxiv",
    doi: str | None = None,
    arxiv_id: str | None = None,
    source_variants: list[str] | None = None,
    base_relevance_score: int = 0,
    relevance_score: int = 0,
    match_reasons: list[str] | None = None,
) -> Paper:
    now = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    published_at = now - timedelta(hours=hours_ago)
    return Paper(
        title=title,
        summary=summary,
        authors=authors or [],
        categories=["cs.AI"],
        paper_id=paper_id,
        abstract_url=abstract_url,
        pdf_url=pdf_url,
        published_at=published_at,
        updated_at=published_at,
        source=source,
        doi=doi,
        arxiv_id=arxiv_id,
        source_variants=source_variants or [],
        base_relevance_score=base_relevance_score,
        relevance_score=relevance_score,
        match_reasons=match_reasons or [],
    )


class DigestTests(unittest.TestCase):
    def test_filter_papers_applies_age_and_keyword_rules(self) -> None:
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=["survey"],
            max_results=50,
            max_items=10,
        )
        now = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
        papers = [
            build_paper(
                title="Useful agent paper",
                summary="A benchmark for agent evaluation.",
                hours_ago=1,
                authors=["Alice"],
            ),
            build_paper(
                title="Outdated agent paper",
                summary="Still about agents.",
                hours_ago=36,
                authors=["Bob"],
            ),
            build_paper(
                title="Agent survey",
                summary="A survey of agents.",
                hours_ago=2,
                authors=["Carol"],
            ),
        ]

        filtered = filter_papers(
            papers,
            feed,
            now=now,
            lookback_hours=24,
            ranking=RankingConfig(),
        )

        self.assertEqual([paper.title for paper in filtered], ["Useful agent paper"])

    def test_render_markdown_handles_missing_authors(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="Asia/Shanghai",
            lookback_hours=24,
            feeds=[
                FeedDigest(
                    name="LLM",
                    papers=[
                        build_paper(
                            title="Reasoning paper",
                            summary="Reasoning summary.",
                            hours_ago=1,
                            authors=[],
                        )
                    ],
                )
            ],
        )

        markdown = render_markdown(digest)

        self.assertIn("# Daily Paper Digest", markdown)
        self.assertIn("Unknown authors", markdown)
        self.assertIn("Reasoning paper", markdown)
        self.assertIn("Published", markdown)
        self.assertIn("Sorting: hybrid", markdown)

    def test_render_markdown_includes_highlights_and_structured_analysis(self) -> None:
        analyzed_paper = build_paper(
            title="Reasoning paper",
            summary="Reasoning summary.",
            hours_ago=1,
            authors=["Alice"],
        )
        analyzed_paper.analysis = PaperAnalysis(
            conclusion="A concise verdict about the paper.",
            contributions=["Introduces a new benchmark", "Evaluates agent behavior"],
            audience="Researchers working on agent evaluation.",
            limitations=["Abstract-only analysis may miss setup details."],
        )
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            highlights=["LLM: Reasoning paper - A concise verdict about the paper."],
            feeds=[FeedDigest(name="LLM", papers=[analyzed_paper])],
        )

        markdown = render_markdown(digest)

        self.assertIn("## Today's Highlights", markdown)
        self.assertIn("Conclusion: A concise verdict about the paper.", markdown)
        self.assertIn("Contributions: Introduces a new benchmark", markdown)
        self.assertIn("Best For: Researchers working on agent evaluation.", markdown)
        self.assertIn(
            "Limitations: Abstract-only analysis may miss setup details.", markdown
        )

    def test_render_markdown_shows_merged_source_variants(self) -> None:
        merged_paper = build_paper(
            title="Reasoning paper",
            summary="Reasoning summary.",
            hours_ago=1,
            authors=["Alice"],
            source="semantic_scholar",
            doi="10.5555/example",
            source_variants=["arxiv", "semantic_scholar", "openalex"],
            relevance_score=92,
            match_reasons=['title matched "reasoning"', "seen in 3 sources"],
        )
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[merged_paper])],
        )

        markdown = render_markdown(digest)

        self.assertIn("Source: arxiv / semantic_scholar / openalex", markdown)
        self.assertIn("Relevance: 92", markdown)
        self.assertIn(
            'Match Reasons: title matched "reasoning"; seen in 3 sources',
            markdown,
        )

    def test_render_markdown_includes_feedback_status(self) -> None:
        paper = build_paper(
            title="Reasoning paper",
            summary="Reasoning summary.",
            hours_ago=1,
            authors=["Alice"],
        )
        paper.feedback_status = "follow_up"
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[paper])],
        )

        markdown = render_markdown(digest)

        self.assertIn("Feedback: follow_up", markdown)

    def test_render_markdown_includes_focus_section(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[])],
            focus_items=[
                FocusItem(
                    canonical_id="arxiv:2604.06170",
                    title="Paper Circle",
                    abstract_url="https://arxiv.org/abs/2604.06170v1",
                    summary="Multi-agent research discovery framework.",
                    source_label="arxiv",
                    feedback_status="star",
                    reasons=["new_starred", "starred_momentum"],
                    feed_names=["LLM"],
                    relevance_score=80,
                    active_days=2,
                    active_feeds=1,
                    appearance_count=2,
                    first_seen=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
                    last_seen=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
                )
            ],
        )

        markdown = render_markdown(digest)

        self.assertIn("## Focus", markdown)
        self.assertIn("Why it was pushed: newly starred", markdown)
        self.assertIn("Coverage: 2 active days / 1 feeds / 2 appearances", markdown)

    def test_render_notification_markdown_supports_feedback_only(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="Asia/Shanghai",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[])],
            focus_items=[
                FocusItem(
                    canonical_id="pubmed:41951858",
                    title="ClinicRealm",
                    abstract_url="https://pubmed.ncbi.nlm.nih.gov/41951858/",
                    summary="Clinical prediction benchmark.",
                    source_label="PubMed",
                    feedback_status="follow_up",
                    reasons=["follow_up_resurfaced"],
                    feed_names=["PubMed AI"],
                )
            ],
            template="zh_daily_brief",
        )

        markdown = render_notification_markdown(digest, feedback_only=True)

        self.assertIn("# 每日关注清单", markdown)
        self.assertIn("## Focus 区块", markdown)
        self.assertIn("推送原因：待跟进论文今天再次出现", markdown)
        self.assertNotIn("## 论文速览", markdown)

    def test_summarize_focus_items_reports_counts(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[],
            focus_items=[
                FocusItem(
                    canonical_id="a",
                    title="A",
                    abstract_url="https://example.com/a",
                    summary="A",
                    source_label="arxiv",
                    feedback_status="star",
                    reasons=["new_starred"],
                ),
                FocusItem(
                    canonical_id="b",
                    title="B",
                    abstract_url="https://example.com/b",
                    summary="B",
                    source_label="PubMed",
                    feedback_status="follow_up",
                    reasons=["follow_up_resurfaced"],
                ),
            ],
        )

        self.assertEqual(summarize_focus_items(digest), "Focus=2, star=1, follow_up=1")

    def test_render_markdown_supports_zh_daily_brief_template(self) -> None:
        analyzed_paper = build_paper(
            title="多模态推理论文",
            summary="原始摘要。",
            hours_ago=1,
            authors=["Alice", "Bob"],
        )
        analyzed_paper.tags = ["评测", "应用"]
        analyzed_paper.topics = ["多模态推理", "视频理解"]
        analyzed_paper.analysis = PaperAnalysis(
            conclusion="提出了一个适合日报消费的简明结论。",
            contributions=["统一了评测设置", "给出了更稳定的对比结果"],
            audience="关注多模态评测和应用落地的研究者。",
            limitations=["仅基于摘要，实验细节仍需阅读全文确认。"],
        )
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="Asia/Shanghai",
            lookback_hours=24,
            highlights=[
                "主题「多模态推理」：命中 1 篇，覆盖 LLM，"
                "代表论文包括 《多模态推理论文》。"
            ],
            topic_sections=[
                TopicDigest(
                    name="多模态推理",
                    paper_count=1,
                    feed_names=["LLM"],
                    paper_titles=["多模态推理论文"],
                    key_points=[
                        "《多模态推理论文》〔评测 / 应用〕：更适合日报阅读的研究结论。"
                    ],
                )
            ],
            feeds=[
                FeedDigest(
                    name="LLM",
                    papers=[analyzed_paper],
                    key_points=[
                        "《多模态推理论文》〔评测 / 应用〕："
                        "这篇工作更像一次高质量的评测整合。"
                    ],
                )
            ],
            template="zh_daily_brief",
        )

        markdown = render_markdown(digest)

        self.assertIn("# 每日论文简报", markdown)
        self.assertIn("## 今日重点", markdown)
        self.assertIn("## 主题聚焦", markdown)
        self.assertIn("### 多模态推理", markdown)
        self.assertIn("## LLM 观察", markdown)
        self.assertIn("排序策略：hybrid", markdown)
        self.assertIn("### 本组速览", markdown)
        self.assertIn("### 论文速览", markdown)
        self.assertIn("标签：评测 / 应用", markdown)
        self.assertIn("主题词：多模态推理 / 视频理解", markdown)
        self.assertIn("一句话结论：提出了一个适合日报消费的简明结论。", markdown)
        self.assertIn("主要贡献：统一了评测设置；给出了更稳定的对比结果", markdown)
        self.assertIn("适合谁看：关注多模态评测和应用落地的研究者。", markdown)
        self.assertIn("潜在局限：仅基于摘要，实验细节仍需阅读全文确认。", markdown)

    def test_render_zh_daily_brief_shows_merged_source_variants(self) -> None:
        paper = build_paper(
            title="多源论文",
            summary="原始摘要。",
            hours_ago=1,
            authors=["Alice"],
            source="openalex",
            doi="10.5555/example",
            source_variants=["arxiv", "semantic_scholar", "openalex"],
        )
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[paper])],
            template="zh_daily_brief",
        )

        markdown = render_markdown(digest)

        self.assertIn("来源：arxiv / semantic_scholar / openalex", markdown)

    def test_render_zh_daily_brief_includes_feedback_status(self) -> None:
        paper = build_paper(
            title="待跟进论文",
            summary="原始摘要。",
            hours_ago=1,
            authors=["Alice"],
        )
        paper.feedback_status = "follow_up"
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[paper])],
            template="zh_daily_brief",
        )

        markdown = render_markdown(digest)

        self.assertIn("反馈状态：待跟进", markdown)

    def test_filter_papers_without_keywords_sorts_and_limits(self) -> None:
        feed = FeedConfig(
            name="General",
            categories=["cs.AI"],
            keywords=[],
            exclude_keywords=[],
            max_results=50,
            max_items=2,
        )
        now = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
        papers = [
            build_paper(title="Third", summary="x", hours_ago=3),
            build_paper(title="First", summary="x", hours_ago=1),
            build_paper(title="Second", summary="x", hours_ago=2),
        ]

        filtered = filter_papers(
            papers,
            feed,
            now=now,
            lookback_hours=24,
            ranking=RankingConfig(),
        )

        self.assertEqual([paper.title for paper in filtered], ["First", "Second"])

    def test_filter_papers_scores_and_orders_by_relevance(self) -> None:
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent", "benchmark"],
            exclude_keywords=[],
            max_results=50,
            max_items=5,
        )
        now = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
        papers = [
            build_paper(
                title="Fresh paper",
                summary="An agent benchmark appears only in the summary.",
                hours_ago=1,
                authors=["Alice"],
            ),
            build_paper(
                title="Agent benchmark",
                summary="Compact abstract.",
                hours_ago=3,
                authors=["Alice", "Bob"],
                doi="10.5555/example",
            ),
        ]

        filtered = filter_papers(
            papers,
            feed,
            now=now,
            lookback_hours=24,
            ranking=RankingConfig(),
        )

        self.assertEqual(
            [paper.title for paper in filtered],
            ["Agent benchmark", "Fresh paper"],
        )
        self.assertGreater(filtered[0].relevance_score, filtered[1].relevance_score)
        self.assertIn('title matched "agent"', filtered[0].match_reasons)
        self.assertIn('title matched "benchmark"', filtered[0].match_reasons)
        self.assertIn("has DOI", filtered[0].match_reasons)
        self.assertIn("has PDF", filtered[0].match_reasons)
        self.assertIn("has complete metadata", filtered[0].match_reasons)

    def test_filter_papers_respects_published_at_sort_mode(self) -> None:
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=50,
            max_items=5,
            sort_by="published_at",
        )
        now = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
        papers = [
            build_paper(
                title="Older but richer",
                summary="An agent paper with more metadata and a longer abstract.",
                hours_ago=8,
                authors=["Alice", "Bob"],
                doi="10.5555/example",
            ),
            build_paper(
                title="Newest hit",
                summary="Agent summary.",
                hours_ago=1,
                authors=["Alice"],
                pdf_url=None,
            ),
        ]

        filtered = filter_papers(
            papers,
            feed,
            now=now,
            lookback_hours=24,
            ranking=RankingConfig(
                sort_by="hybrid",
                weights=RankingWeights(title_match_weight=50),
            ),
        )

        self.assertEqual(
            [paper.title for paper in filtered],
            ["Newest hit", "Older but richer"],
        )

    def test_render_markdown_includes_empty_feed_message(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="Empty", papers=[])],
        )

        markdown = render_markdown(digest)

        self.assertIn("## Empty", markdown)
        self.assertIn("No matching papers found.", markdown)

    def test_write_outputs_writes_dated_and_latest_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[],
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
            )
            digest = DigestRun(
                generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
                timezone="UTC",
                lookback_hours=24,
                feeds=[
                    FeedDigest(
                        name="LLM",
                        papers=[
                            build_paper(
                                title="Digest title",
                                summary="Body",
                                hours_ago=1,
                                relevance_score=88,
                                match_reasons=['title matched "digest"', "has PDF"],
                            )
                        ],
                    )
                ],
            )

            json_path, markdown_path = write_outputs(config, digest)
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertTrue((config.output_dir / "latest.json").exists())
            self.assertTrue((config.output_dir / "latest.md").exists())
            self.assertIn("Digest title", markdown_path.read_text(encoding="utf-8"))
            self.assertIn("sorting", payload)
            paper_payload = payload["feeds"][0]["papers"][0]
            self.assertIn("relevance_score", paper_payload)
            self.assertIn("match_reasons", paper_payload)
            self.assertNotIn("base_relevance_score", paper_payload)

    def test_summarize_digest_reports_counts(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[
                FeedDigest(
                    name="LLM",
                    papers=[build_paper(title="A", summary="x", hours_ago=1)],
                ),
                FeedDigest(name="Vision", papers=[]),
            ],
        )

        self.assertEqual(summarize_digest(digest), "LLM=1, Vision=0")
        self.assertEqual(
            summarize_digest(
                DigestRun(
                    generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
                    timezone="UTC",
                    lookback_hours=24,
                    feeds=[],
                )
            ),
            "no feeds",
        )

    def test_digest_has_papers_reports_presence(self) -> None:
        from paper_digest.digest import digest_has_papers

        self.assertTrue(
            digest_has_papers(
                DigestRun(
                    generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
                    timezone="UTC",
                    lookback_hours=24,
                    feeds=[
                        FeedDigest(
                            name="LLM",
                            papers=[build_paper(title="A", summary="x", hours_ago=1)],
                        )
                    ],
                )
            )
        )
        self.assertFalse(
            digest_has_papers(
                DigestRun(
                    generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
                    timezone="UTC",
                    lookback_hours=24,
                    feeds=[FeedDigest(name="LLM", papers=[])],
                )
            )
        )
