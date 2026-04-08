from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.arxiv_client import Paper
from paper_digest.config import AppConfig, FeedConfig, StateConfig
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
