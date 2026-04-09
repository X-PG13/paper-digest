from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from paper_digest.config import FeedConfig
from paper_digest.semantic_scholar_client import (
    SemanticScholarClientError,
    fetch_latest_semantic_scholar_papers,
    parse_semantic_scholar_response,
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


def build_search_payload() -> bytes:
    return json.dumps(
        {
            "total": 2,
            "data": [
                {
                    "paperId": "abc123",
                    "externalIds": {"ArXiv": "2604.06666"},
                    "url": "https://www.semanticscholar.org/paper/abc123",
                    "title": "Semantic Scholar Test Paper",
                    "openAccessPdf": {
                        "url": "https://arxiv.org/pdf/2604.06666.pdf"
                    },
                    "fieldsOfStudy": ["Computer Science"],
                    "publicationTypes": ["Review"],
                    "publicationDate": "2026-04-08",
                    "authors": [
                        {"name": "Alice Smith"},
                        {"name": "Bob Jones"},
                    ],
                    "abstract": "Agent systems with benchmark gains.",
                },
                {
                    "paperId": "skip-me",
                    "title": "Missing date should be skipped",
                    "publicationDate": None,
                },
            ],
        }
    ).encode("utf-8")


class SemanticScholarClientTests(unittest.TestCase):
    def test_parse_semantic_scholar_response_extracts_papers(self) -> None:
        papers = parse_semantic_scholar_response(build_search_payload())

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "Semantic Scholar Test Paper")
        self.assertEqual(papers[0].summary, "Agent systems with benchmark gains.")
        self.assertEqual(papers[0].authors, ["Alice Smith", "Bob Jones"])
        self.assertEqual(papers[0].categories, ["Computer Science", "Review"])
        self.assertEqual(papers[0].paper_id, "semantic_scholar:abc123")
        self.assertEqual(
            papers[0].abstract_url,
            "https://arxiv.org/abs/2604.06666",
        )
        self.assertEqual(
            papers[0].pdf_url,
            "https://arxiv.org/pdf/2604.06666.pdf",
        )
        self.assertEqual(
            papers[0].published_at,
            datetime(2026, 4, 8, 0, 0, tzinfo=UTC),
        )
        self.assertEqual(papers[0].source, "semantic_scholar")
        self.assertEqual(papers[0].date_label, "Published")

    def test_parse_semantic_scholar_response_rejects_invalid_json(self) -> None:
        with self.assertRaises(SemanticScholarClientError):
            parse_semantic_scholar_response(b"not json")

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_semantic_scholar_papers_queries_api(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(build_search_payload())
        feed = FeedConfig(
            name="Semantic Scholar AI",
            source="semantic_scholar",
            queries=["large language model", "agent systems"],
            types=["Review"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_semantic_scholar_papers(
            feed,
            now=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            lookback_hours=48,
            request_delay_seconds=1.0,
            contact_email="bot@example.com",
        )

        self.assertEqual(len(papers), 1)
        request = mock_urlopen.call_args.args[0]
        query = parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(query["limit"], ["10"])
        self.assertEqual(query["sort"], ["publicationDate:desc"])
        self.assertEqual(query["publicationDateOrYear"], ["2026-04-07:2026-04-09"])
        self.assertEqual(
            query["query"],
            ["(large language model) OR (agent systems)"],
        )
        self.assertIn("publicationDate", query["fields"][0])
        self.assertEqual(mock_sleep.call_args_list[0].args, (1.0,))
