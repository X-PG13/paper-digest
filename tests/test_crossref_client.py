from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from paper_digest.config import FeedConfig
from paper_digest.crossref_client import (
    CrossrefClientError,
    fetch_latest_crossref_papers,
    parse_crossref_response,
)


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def build_payload() -> bytes:
    return json.dumps(
        {
            "message": {
                "items": [
                    {
                        "DOI": "10.1000/example-doi",
                        "URL": "https://doi.org/10.1000/example-doi",
                        "title": ["Crossref Test Paper"],
                        "subject": ["Computer Science"],
                        "abstract": "<jats:p>Reasoning paper</jats:p>",
                        "indexed": {"date-time": "2026-04-08T01:00:00Z"},
                        "author": [
                            {"given": "Alice", "family": "Example"},
                            {"literal": "Research Group"},
                        ],
                    }
                ]
            }
        }
    ).encode("utf-8")


class CrossrefClientTests(unittest.TestCase):
    def test_parse_crossref_response_extracts_papers(self) -> None:
        papers = parse_crossref_response(build_payload())

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "Crossref Test Paper")
        self.assertEqual(papers[0].authors, ["Alice Example", "Research Group"])
        self.assertEqual(papers[0].categories, ["Computer Science"])
        self.assertEqual(papers[0].summary, "Reasoning paper")
        self.assertEqual(papers[0].date_label, "Indexed")
        self.assertEqual(papers[0].source, "crossref")

    def test_parse_crossref_response_rejects_invalid_json(self) -> None:
        with self.assertRaises(CrossrefClientError):
            parse_crossref_response(b"not json")

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_crossref_papers_queries_api(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(build_payload())
        feed = FeedConfig(
            name="Crossref",
            source="crossref",
            queries=["agent", "reasoning"],
            types=["journal-article"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_crossref_papers(
            feed,
            now=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
            lookback_hours=24,
            request_delay_seconds=1.0,
            contact_email="bot@example.com",
        )

        self.assertEqual(len(papers), 1)
        request = mock_urlopen.call_args.args[0]
        query = parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(query["query.bibliographic"], ["agent reasoning"])
        self.assertEqual(query["rows"], ["10"])
        self.assertEqual(query["sort"], ["indexed"])
        self.assertEqual(query["order"], ["desc"])
        self.assertEqual(query["mailto"], ["bot@example.com"])
        self.assertIn("from-index-date:2026-04-07", query["filter"][0])
        self.assertIn("type:journal-article", query["filter"][0])
        mock_sleep.assert_called_once_with(1.0)

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_crossref_papers_retries_timeout_errors(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.side_effect = [
            TimeoutError("The read operation timed out"),
            DummyHTTPResponse(build_payload()),
        ]
        feed = FeedConfig(
            name="Crossref",
            source="crossref",
            queries=["agent", "reasoning"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_crossref_papers(
            feed,
            now=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
            lookback_hours=24,
            request_delay_seconds=1.0,
            request_timeout_seconds=45,
            retry_attempts=3,
            retry_backoff_seconds=4.0,
            contact_email="bot@example.com",
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(mock_urlopen.call_count, 2)
        self.assertEqual(mock_sleep.call_args_list[0].args, (4.0,))
        self.assertEqual(mock_sleep.call_args_list[1].args, (1.0,))

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_crossref_papers_retries_retry_after_header(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        retryable = HTTPError(
            url="https://api.crossref.org/works",
            code=503,
            msg="Service Unavailable",
            hdrs={"Retry-After": "9"},
            fp=None,
        )
        mock_urlopen.side_effect = [
            retryable,
            DummyHTTPResponse(build_payload()),
        ]
        feed = FeedConfig(
            name="Crossref",
            source="crossref",
            queries=["agent", "reasoning"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_crossref_papers(
            feed,
            now=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
            lookback_hours=24,
            request_delay_seconds=1.0,
            contact_email="bot@example.com",
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(mock_urlopen.call_count, 2)
        self.assertEqual(mock_sleep.call_args_list[0].args, (10.0,))
        self.assertEqual(mock_sleep.call_args_list[1].args, (1.0,))
