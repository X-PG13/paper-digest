from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from paper_digest.arxiv_client import Paper
from paper_digest.config import FeedConfig
from paper_digest.digest import (
    DigestRun,
    FeedDigest,
    filter_papers,
    render_markdown,
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
