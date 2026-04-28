from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from paper_digest import openalex_client
from paper_digest.config import FeedConfig
from paper_digest.openalex_client import (
    OpenAlexClientError,
    build_openalex_search_query,
    fetch_latest_openalex_papers,
    parse_openalex_response,
    parse_openalex_work,
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


class OpenAlexClientAdditionalTests(unittest.TestCase):
    def test_parse_openalex_response_validates_payload_shape(self) -> None:
        cases = [
            (json.dumps([]).encode("utf-8"), "OpenAlex response payload is invalid"),
            (
                json.dumps({"results": {}}).encode("utf-8"),
                "OpenAlex response did not include a valid results list",
            ),
        ]

        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(OpenAlexClientError, message):
                    parse_openalex_response(payload)

    def test_parse_openalex_response_skips_non_mapping_items(self) -> None:
        papers = parse_openalex_response(
            json.dumps(
                {
                    "results": [
                        1,
                        {
                            "id": "https://openalex.org/W12345",
                            "publication_date": "2026-04-08",
                        },
                    ]
                }
            ).encode("utf-8")
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].paper_id, "openalex:W12345")

    def test_parse_openalex_work_uses_fallbacks_and_deduplicates_metadata(self) -> None:
        paper = parse_openalex_work(
            {
                "id": "https://openalex.org/W12345/",
                "publication_date": "2026-04-08",
                "type": "journal-article",
                "doi": "https://doi.org/10.5555/example",
                "primary_location": {
                    "landing_page_url": " ",
                    "pdf_url": "https://example.com/paper.pdf",
                },
                "topics": [
                    {"display_name": "Agents"},
                    {"display_name": "agents"},
                    {"display_name": "Ignored Third Topic"},
                ],
                "primary_topic": {
                    "field": {"display_name": "Computer Science"},
                    "subfield": {"display_name": "computer science"},
                },
                "abstract_inverted_index": {
                    " Agent ": [0, 2],
                    "systems": [1],
                    "first": [0],
                    "ignored": [-1],
                    "bad": ["x"],
                    "": [3],
                },
            }
        )

        assert paper is not None
        self.assertEqual(paper.title, "W12345")
        self.assertEqual(paper.summary, "Agent systems Agent")
        self.assertEqual(
            paper.categories,
            ["Journal Article", "Computer Science", "Agents"],
        )
        self.assertEqual(paper.abstract_url, "https://doi.org/10.5555/example")
        self.assertEqual(paper.pdf_url, "https://example.com/paper.pdf")
        self.assertEqual(paper.paper_id, "openalex:W12345")

    def test_parse_openalex_work_rejects_invalid_dates(self) -> None:
        with self.assertRaisesRegex(
            OpenAlexClientError,
            "invalid OpenAlex publication",
        ):
            parse_openalex_work(
                {
                    "id": "https://openalex.org/W12345",
                    "publication_date": "2026-99-99",
                }
            )

    def test_openalex_helpers_cover_invalid_and_fallback_inputs(self) -> None:
        self.assertEqual(openalex_client._reconstruct_abstract("bad"), "")
        self.assertEqual(
            openalex_client._reconstruct_abstract(
                {
                    1: [0],
                    "token": "bad",
                    " ": [1],
                    "ignored": [-1],
                }
            ),
            "",
        )
        self.assertEqual(openalex_client._extract_authors("bad"), [])
        self.assertEqual(
            openalex_client._extract_authors(
                [
                    "invalid",
                    {"author": "invalid"},
                    {"author": {"display_name": "   "}},
                    {"author": {"display_name": "Alice"}},
                ]
            ),
            ["Alice"],
        )
        self.assertEqual(openalex_client._extract_categories({}), [])
        self.assertIsNone(openalex_client._display_work_type(None))
        self.assertEqual(openalex_client._topic_names("bad"), [])
        self.assertEqual(
            openalex_client._topic_names(
                [
                    "invalid",
                    {"display_name": "   "},
                    {"display_name": "ignored third item"},
                ]
            ),
            [],
        )
        self.assertEqual(
            openalex_client._resolve_abstract_url({}),
            "https://openalex.org",
        )
        self.assertEqual(
            openalex_client._openalex_short_id("https://openalex.org"),
            "https://openalex.org",
        )

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_openalex_without_optional_contact_or_api_key(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(
            json.dumps({"results": []}).encode("utf-8")
        )
        feed = FeedConfig(
            name="OpenAlex AI",
            source="openalex",
            queries=["agent systems"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_openalex_papers(
            feed,
            now=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            lookback_hours=24,
            request_delay_seconds=0.5,
        )

        self.assertEqual(papers, [])
        request = mock_urlopen.call_args.args[0]
        self.assertNotIn("mailto=", request.full_url)
        self.assertNotIn("api_key=", request.full_url)
        self.assertNotIn("type:", request.full_url)
        self.assertEqual(
            dict(request.header_items())["User-agent"],
            "paper-digest/0.1 (https://github.com/X-PG13/paper-digest)",
        )
        self.assertEqual(build_openalex_search_query(feed), "agent systems")
        self.assertEqual(mock_sleep.call_args_list[0].args, (0.5,))
