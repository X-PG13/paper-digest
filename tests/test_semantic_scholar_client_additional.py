from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from paper_digest.config import FeedConfig
from paper_digest.semantic_scholar_client import (
    SemanticScholarClientError,
    build_semantic_scholar_query,
    fetch_latest_semantic_scholar_papers,
    parse_semantic_scholar_item,
    parse_semantic_scholar_response,
)


def _payload(items: list[object]) -> bytes:
    return json.dumps({"data": items}).encode("utf-8")


class SemanticScholarClientAdditionalTests(unittest.TestCase):
    def test_parse_response_rejects_non_mapping_and_invalid_data_list(self) -> None:
        with self.assertRaisesRegex(
            SemanticScholarClientError,
            "response payload is invalid",
        ):
            parse_semantic_scholar_response(json.dumps([]).encode("utf-8"))

        with self.assertRaisesRegex(
            SemanticScholarClientError,
            "valid data list",
        ):
            parse_semantic_scholar_response(
                json.dumps({"data": "not-a-list"}).encode("utf-8")
            )

    def test_parse_response_skips_non_mapping_items(self) -> None:
        papers = parse_semantic_scholar_response(
            _payload(
                [
                    "invalid",
                    {
                        "paperId": "abc123",
                        "publicationDate": "2026-04-08",
                    },
                ]
            )
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].paper_id, "semantic_scholar:abc123")

    def test_parse_item_applies_fallbacks_and_deduplicates_categories(self) -> None:
        paper = parse_semantic_scholar_item(
            {
                "paperId": "abc123",
                "publicationDate": "2026-04",
                "externalIds": {"DOI": "10.1000/example"},
                "fieldsOfStudy": ["Computer Science", " ", "computer science"],
                "publicationTypes": ["Review", " ", "review"],
                "authors": [{"name": " Alice "}, {"name": "  "}, "invalid"],
                "openAccessPdf": "not-a-dict",
            }
        )

        assert paper is not None
        self.assertEqual(paper.title, "Semantic Scholar abc123")
        self.assertEqual(paper.summary, "")
        self.assertEqual(paper.authors, ["Alice"])
        self.assertEqual(paper.categories, ["Computer Science", "Review"])
        self.assertEqual(paper.abstract_url, "https://doi.org/10.1000/example")
        self.assertIsNone(paper.pdf_url)
        self.assertEqual(paper.doi, "10.1000/example")
        self.assertEqual(paper.published_at, datetime(2026, 4, 1, tzinfo=UTC))

    def test_parse_item_supports_year_only_dates_and_default_urls(self) -> None:
        paper = parse_semantic_scholar_item(
            {
                "paperId": "year-only",
                "publicationDate": "2026",
                "url": "  ",
            }
        )

        assert paper is not None
        self.assertEqual(
            paper.abstract_url,
            "https://www.semanticscholar.org",
        )
        self.assertEqual(paper.published_at, datetime(2026, 1, 1, tzinfo=UTC))

    def test_parse_item_uses_url_when_external_ids_are_blank(self) -> None:
        paper = parse_semantic_scholar_item(
            {
                "paperId": "fallback-url",
                "publicationDate": "2026-04-08",
                "externalIds": {"ArXiv": " ", "DOI": " "},
                "url": " https://example.com/paper/fallback-url ",
            }
        )

        assert paper is not None
        self.assertEqual(
            paper.abstract_url,
            "https://example.com/paper/fallback-url",
        )

    def test_parse_item_rejects_invalid_dates_and_missing_required_fields(self) -> None:
        self.assertIsNone(
            parse_semantic_scholar_item(
                {
                    "paperId": None,
                    "publicationDate": "2026-04-08",
                }
            )
        )
        self.assertIsNone(
            parse_semantic_scholar_item(
                {
                    "paperId": "abc123",
                    "publicationDate": None,
                }
            )
        )
        with self.assertRaisesRegex(
            SemanticScholarClientError,
            "invalid Semantic Scholar publication date",
        ):
            parse_semantic_scholar_item(
                {
                    "paperId": "abc123",
                    "publicationDate": "2026/04/08",
                }
            )

    def test_build_query_returns_single_query_unchanged(self) -> None:
        feed = FeedConfig(
            name="Semantic Scholar AI",
            source="semantic_scholar",
            queries=["agent systems"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        self.assertEqual(build_semantic_scholar_query(feed), "agent systems")

    @patch(
        "paper_digest.semantic_scholar_client.fetch_bytes_with_retry",
        return_value=_payload(
            [
                {
                    "paperId": "abc123",
                    "publicationDate": "2026-04-08",
                    "publicationTypes": ["Review"],
                    "title": "Semantic Scholar Test Paper",
                    "url": "https://www.semanticscholar.org/paper/abc123",
                }
            ]
        ),
    )
    def test_fetch_latest_papers_returns_all_results_without_type_filter(
        self,
        mock_fetch_bytes_with_retry,
    ) -> None:
        feed = FeedConfig(
            name="Semantic Scholar AI",
            source="semantic_scholar",
            queries=["agent systems"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_semantic_scholar_papers(
            feed,
            now=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            lookback_hours=48,
            request_delay_seconds=0.0,
        )

        self.assertEqual(len(papers), 1)
        request = mock_fetch_bytes_with_retry.call_args.args[0]
        query = parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(query["query"], ["agent systems"])
        self.assertEqual(query["publicationDateOrYear"], ["2026-04-07:2026-04-09"])
        self.assertEqual(
            request.get_header("User-agent"),
            "paper-digest/0.1 (https://github.com/X-PG13/paper-digest)",
        )
