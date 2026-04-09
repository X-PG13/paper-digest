from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from paper_digest.config import FeedConfig
from paper_digest.openalex_client import (
    OpenAlexClientError,
    fetch_latest_openalex_papers,
    parse_openalex_response,
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


def build_openalex_payload() -> bytes:
    return json.dumps(
        {
            "meta": {"count": 2},
            "results": [
                {
                    "id": "https://openalex.org/W1234567890",
                    "doi": "https://doi.org/10.5555/openalex",
                    "display_name": "OpenAlex Test Paper",
                    "publication_date": "2026-04-08",
                    "type": "article",
                    "primary_location": {
                        "landing_page_url": "https://doi.org/10.5555/openalex",
                        "pdf_url": None,
                    },
                    "best_oa_location": {
                        "pdf_url": "https://example.com/openalex.pdf",
                    },
                    "authorships": [
                        {"author": {"display_name": "Alice Smith"}},
                        {"author": {"display_name": "Bob Jones"}},
                    ],
                    "primary_topic": {
                        "field": {"display_name": "Computer Science"},
                        "subfield": {"display_name": "Artificial Intelligence"},
                    },
                    "topics": [
                        {"display_name": "Multi-agent Systems"},
                        {"display_name": "Language Model Evaluation"},
                    ],
                    "abstract_inverted_index": {
                        "Agent": [0],
                        "systems": [1],
                        "improve": [2],
                        "benchmarks.": [3],
                    },
                },
                {
                    "id": "https://openalex.org/Wskip",
                    "display_name": "Missing date should be skipped",
                    "publication_date": None,
                },
            ],
        }
    ).encode("utf-8")


class OpenAlexClientTests(unittest.TestCase):
    def test_parse_openalex_response_extracts_papers(self) -> None:
        papers = parse_openalex_response(build_openalex_payload())

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "OpenAlex Test Paper")
        self.assertEqual(papers[0].summary, "Agent systems improve benchmarks.")
        self.assertEqual(papers[0].authors, ["Alice Smith", "Bob Jones"])
        self.assertEqual(
            papers[0].categories,
            [
                "Article",
                "Computer Science",
                "Artificial Intelligence",
                "Multi-agent Systems",
                "Language Model Evaluation",
            ],
        )
        self.assertEqual(papers[0].paper_id, "openalex:W1234567890")
        self.assertEqual(papers[0].abstract_url, "https://doi.org/10.5555/openalex")
        self.assertEqual(papers[0].pdf_url, "https://example.com/openalex.pdf")
        self.assertEqual(
            papers[0].published_at,
            datetime(2026, 4, 8, 0, 0, tzinfo=UTC),
        )
        self.assertEqual(papers[0].source, "openalex")
        self.assertEqual(papers[0].date_label, "Published")

    def test_parse_openalex_response_rejects_invalid_json(self) -> None:
        with self.assertRaises(OpenAlexClientError):
            parse_openalex_response(b"not json")

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_openalex_papers_queries_api(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(build_openalex_payload())
        feed = FeedConfig(
            name="OpenAlex AI",
            source="openalex",
            queries=["large language model", "agent systems"],
            types=["article", "preprint"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_openalex_papers(
            feed,
            now=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            lookback_hours=48,
            request_delay_seconds=1.0,
            contact_email="bot@example.com",
            api_key="openalex-secret",
        )

        self.assertEqual(len(papers), 1)
        request = mock_urlopen.call_args.args[0]
        query = parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(query["per-page"], ["10"])
        self.assertEqual(query["sort"], ["publication_date:desc"])
        self.assertEqual(
            query["search"],
            ['"large language model" OR "agent systems"'],
        )
        self.assertIn("from_publication_date:2026-04-07", query["filter"][0])
        self.assertIn("to_publication_date:2026-04-09", query["filter"][0])
        self.assertIn("type:article|preprint", query["filter"][0])
        self.assertEqual(query["mailto"], ["bot@example.com"])
        self.assertEqual(query["api_key"], ["openalex-secret"])
        self.assertEqual(mock_sleep.call_args_list[0].args, (1.0,))
