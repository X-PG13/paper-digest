from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from paper_digest.config import FeedConfig
from paper_digest.crossref_client import (
    CrossrefClientError,
    fetch_latest_crossref_papers,
    parse_crossref_item,
    parse_crossref_response,
)


def _payload(items: list[object]) -> bytes:
    return json.dumps({"message": {"items": items}}).encode("utf-8")


class CrossrefClientAdditionalTests(unittest.TestCase):
    def test_parse_response_rejects_missing_message_and_invalid_items(self) -> None:
        with self.assertRaisesRegex(
            CrossrefClientError,
            "message object",
        ):
            parse_crossref_response(json.dumps({}).encode("utf-8"))

        with self.assertRaisesRegex(
            CrossrefClientError,
            "items payload is invalid",
        ):
            parse_crossref_response(
                json.dumps({"message": {"items": "bad"}}).encode("utf-8")
            )

    def test_parse_item_uses_fallback_fields_and_timestamp_indexed_dates(self) -> None:
        paper = parse_crossref_item(
            {
                "DOI": "10.1000/example-doi",
                "indexed": {"timestamp": 1775696400000},
                "author": [
                    {"given": "Alice"},
                    {"family": "Example"},
                    {"given": "Bob", "family": "Builder"},
                    {"literal": "Research Group"},
                    {"given": " ", "family": " "},
                    {"literal": " "},
                    "invalid",
                ],
                "subject": "not-a-list",
                "abstract": None,
            }
        )

        self.assertEqual(paper.title, "10.1000/example-doi")
        self.assertEqual(
            paper.abstract_url,
            "https://doi.org/10.1000/example-doi",
        )
        self.assertEqual(
            paper.authors,
            ["Alice", "Example", "Bob Builder", "Research Group"],
        )
        self.assertEqual(paper.categories, [])
        self.assertEqual(paper.summary, "")
        self.assertEqual(
            paper.published_at,
            datetime(2026, 4, 9, 1, 0, tzinfo=UTC),
        )

    def test_parse_item_rejects_missing_doi_and_invalid_indexed_formats(self) -> None:
        with self.assertRaisesRegex(CrossrefClientError, "DOI is missing"):
            parse_crossref_item(
                {
                    "indexed": {"date-time": "2026-04-08T01:00:00Z"},
                }
            )

        with self.assertRaisesRegex(
            CrossrefClientError,
            "indexed date information",
        ):
            parse_crossref_item(
                {
                    "DOI": "10.1000/example-doi",
                    "indexed": None,
                }
            )

        with self.assertRaisesRegex(
            CrossrefClientError,
            "indexed date format is invalid",
        ):
            parse_crossref_item(
                {
                    "DOI": "10.1000/example-doi",
                    "indexed": {"timestamp": "bad"},
                }
            )

        with self.assertRaisesRegex(CrossrefClientError, "invalid Crossref datetime"):
            parse_crossref_item(
                {
                    "DOI": "10.1000/example-doi",
                    "indexed": {"date-time": "bad-timestamp"},
                }
            )

    @patch(
        "paper_digest.crossref_client.fetch_bytes_with_retry",
        return_value=_payload(
            [
                {
                    "DOI": "10.1000/example-doi",
                    "indexed": {"date-time": "2026-04-08T01:00:00Z"},
                }
            ]
        ),
    )
    def test_fetch_latest_crossref_papers_omits_optional_query_fields_when_absent(
        self,
        mock_fetch_bytes_with_retry,
    ) -> None:
        feed = FeedConfig(
            name="Crossref",
            source="crossref",
            queries=["agent"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_crossref_papers(
            feed,
            now=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
            lookback_hours=24,
            request_delay_seconds=0.0,
        )

        self.assertEqual(len(papers), 1)
        request = mock_fetch_bytes_with_retry.call_args.args[0]
        query = parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(query["query.bibliographic"], ["agent"])
        self.assertEqual(query["filter"], ["from-index-date:2026-04-07"])
        self.assertNotIn("mailto", query)
