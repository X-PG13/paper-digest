from __future__ import annotations

import unittest
from datetime import UTC, date, datetime

from paper_digest import arxiv_client
from paper_digest.arxiv_client import Paper


class ArxivClientAdditionalTests(unittest.TestCase):
    def test_paper_post_init_normalizes_relevance_and_optional_fields(self) -> None:
        published_at = datetime(2026, 4, 8, 0, 0, tzinfo=UTC)
        paper = Paper(
            title="  Agent Systems: A Survey  ",
            summary="Summary",
            authors=[" Alice ", "alice"],
            categories=["cs.AI", "cs.AI"],
            paper_id="title-only-id",
            abstract_url="https://example.com/abs",
            pdf_url=None,
            published_at=published_at,
            updated_at=published_at,
            source="custom",
            source_urls={" custom ": " https://example.com/custom "},
            tags=["agents", "Agents"],
            topics=["planning", "Planning"],
            base_relevance_score=12,
            relevance_score=1,
            feedback_note="   ",
            feedback_next_action=" review appendix ",
            feedback_due_date="bad-date",
            feedback_snoozed_until=datetime(2026, 4, 11, 9, 0, tzinfo=UTC),
            feedback_review_interval_days=0,
        )

        self.assertEqual(paper.relevance_score, 12)
        self.assertEqual(paper.authors, ["Alice"])
        self.assertEqual(paper.categories, ["cs.AI"])
        self.assertEqual(paper.tags, ["agents"])
        self.assertEqual(paper.topics, ["planning"])
        self.assertEqual(paper.feedback_note, None)
        self.assertEqual(paper.feedback_next_action, "review appendix")
        self.assertEqual(paper.feedback_due_date, None)
        self.assertEqual(paper.feedback_snoozed_until, date(2026, 4, 11))
        self.assertEqual(paper.feedback_review_interval_days, None)
        self.assertEqual(paper.canonical_id(), "title:agent systems a survey")

    def test_arxiv_helper_normalizers_cover_empty_and_invalid_values(self) -> None:
        self.assertIsNone(arxiv_client._extract_doi(None))
        self.assertIsNone(arxiv_client._normalize_optional_note("   "))
        self.assertEqual(
            arxiv_client._normalize_optional_date(date(2026, 4, 8)),
            date(2026, 4, 8),
        )
        self.assertEqual(
            arxiv_client._normalize_optional_date(
                datetime(2026, 4, 9, 12, 0, tzinfo=UTC)
            ),
            date(2026, 4, 9),
        )
        self.assertIsNone(arxiv_client._normalize_optional_date(object()))
        self.assertIsNone(arxiv_client._normalize_optional_date("bad-date"))
        self.assertIsNone(arxiv_client._normalize_optional_positive_int(True))
        self.assertIsNone(arxiv_client._normalize_optional_positive_int(0))
        self.assertEqual(arxiv_client._normalize_optional_positive_int(7), 7)

    def test_source_url_helpers_skip_blank_entries(self) -> None:
        normalized = arxiv_client._normalize_source_urls(
            {
                " ": "https://example.com/ignored-key",
                "doi": " ",
                " custom ": " https://example.com/custom ",
            },
            source=" ",
            paper_id="custom:example",
            abstract_url=" ",
            doi="10.5555/example",
            arxiv_id="2604.00001",
        )

        self.assertEqual(
            normalized,
            {
                "custom": "https://example.com/custom",
                "doi": "https://doi.org/10.5555/example",
                "arxiv": "https://arxiv.org/abs/2604.00001",
            },
        )

        merged = arxiv_client._merge_source_urls(
            {" ": "https://example.com/ignored-key", "doi": " https://doi.org/10.1/a "},
            {"openalex": " ", "arxiv": " https://arxiv.org/abs/2604.00001 "},
        )

        self.assertEqual(
            merged,
            {
                "doi": "https://doi.org/10.1/a",
                "arxiv": "https://arxiv.org/abs/2604.00001",
            },
        )
