from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.arxiv_client import Paper, PaperAnalysis
from paper_digest.config import AnalysisConfig, AppConfig, FeedConfig, StateConfig
from paper_digest.digest import (
    DigestRun,
    FeedDigest,
    filter_papers,
    render_markdown,
    summarize_digest,
    write_outputs,
)


def build_paper(
    *,
    title: str,
    summary: str,
    hours_ago: int,
    authors: list[str] | None = None,
) -> Paper:
    now = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    published_at = now - timedelta(hours=hours_ago)
    return Paper(
        title=title,
        summary=summary,
        authors=authors or [],
        categories=["cs.AI"],
        paper_id="http://arxiv.org/abs/2604.00001v1",
        abstract_url="https://arxiv.org/abs/2604.00001v1",
        pdf_url="https://arxiv.org/pdf/2604.00001v1",
        published_at=published_at,
        updated_at=published_at,
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

        filtered = filter_papers(papers, feed, now=now, lookback_hours=24)

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

    def test_render_markdown_supports_zh_daily_brief_template(self) -> None:
        analyzed_paper = build_paper(
            title="多模态推理论文",
            summary="原始摘要。",
            hours_ago=1,
            authors=["Alice", "Bob"],
        )
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
            highlights=["LLM：多模态推理论文 - 更适合日报阅读的研究结论。"],
            feeds=[
                FeedDigest(
                    name="LLM",
                    papers=[analyzed_paper],
                    key_points=["多模态推理论文：这篇工作更像一次高质量的评测整合。"],
                )
            ],
            template="zh_daily_brief",
        )

        markdown = render_markdown(digest)

        self.assertIn("# 每日论文简报", markdown)
        self.assertIn("## 今日重点", markdown)
        self.assertIn("## LLM 观察", markdown)
        self.assertIn("### 今日重点", markdown)
        self.assertIn("### 论文速览", markdown)
        self.assertIn("一句话结论：提出了一个适合日报消费的简明结论。", markdown)
        self.assertIn("主要贡献：统一了评测设置；给出了更稳定的对比结果", markdown)
        self.assertIn("适合谁看：关注多模态评测和应用落地的研究者。", markdown)
        self.assertIn("潜在局限：仅基于摘要，实验细节仍需阅读全文确认。", markdown)

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

        filtered = filter_papers(papers, feed, now=now, lookback_hours=24)

        self.assertEqual([paper.title for paper in filtered], ["First", "Second"])

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
                    top_highlights=3,
                    feed_key_points=3,
                    language="English",
                    reasoning_effort="minimal",
                    template="default",
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
                            )
                        ],
                    )
                ],
            )

            json_path, markdown_path = write_outputs(config, digest)

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertTrue((config.output_dir / "latest.json").exists())
            self.assertTrue((config.output_dir / "latest.md").exists())
            self.assertIn("Digest title", markdown_path.read_text(encoding="utf-8"))

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
