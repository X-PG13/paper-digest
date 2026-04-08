from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from paper_digest.arxiv_client import (
    ArxivClientError,
    build_search_query,
    fetch_latest_papers,
    parse_feed,
)
from paper_digest.config import FeedConfig

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "arxiv_sample.xml"


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class ParseFeedTests(unittest.TestCase):
    def test_build_search_query_joins_categories(self) -> None:
        query = build_search_query(["cs.AI", "cs.CL"])

        self.assertEqual(query, "(cat:cs.AI OR cat:cs.CL)")

    def test_parse_feed_extracts_papers(self) -> None:
        papers = parse_feed(FIXTURE_PATH.read_bytes())

        self.assertEqual(len(papers), 2)
        self.assertEqual(papers[0].title, "Agentic Evaluation for Vision Models")
        self.assertEqual(papers[0].authors, ["Alice Example", "Bob Example"])
        self.assertEqual(papers[0].categories, ["cs.AI", "cs.CV"])
        self.assertEqual(papers[0].abstract_url, "https://arxiv.org/abs/2604.00001v1")
        self.assertEqual(papers[0].pdf_url, "https://arxiv.org/pdf/2604.00001v1")

    def test_parse_feed_rejects_invalid_xml(self) -> None:
        with self.assertRaises(ArxivClientError):
            parse_feed(b"not xml")

    def test_parse_feed_rejects_invalid_datetime(self) -> None:
        payload = b"""
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2604.00003v1</id>
            <updated>not-a-date</updated>
            <published>2026-04-08T00:30:00Z</published>
            <title>Bad date</title>
            <summary>Broken payload</summary>
          </entry>
        </feed>
        """

        with self.assertRaises(ArxivClientError):
            parse_feed(payload)

    def test_parse_feed_uses_id_when_alternate_link_missing(self) -> None:
        payload = b"""
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2604.00004v1</id>
            <updated>2026-04-08T00:30:00Z</updated>
            <published>2026-04-08T00:30:00Z</published>
            <title>Fallback links</title>
            <summary>No alternate link</summary>
          </entry>
        </feed>
        """

        papers = parse_feed(payload)

        self.assertEqual(papers[0].abstract_url, "http://arxiv.org/abs/2604.00004v1")
        self.assertIsNone(papers[0].pdf_url)

    @patch("paper_digest.arxiv_client.sleep")
    @patch("paper_digest.arxiv_client.urlopen")
    def test_fetch_latest_papers_queries_api_and_sleeps(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(FIXTURE_PATH.read_bytes())
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI", "cs.CL"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=25,
            max_items=10,
        )

        papers = fetch_latest_papers(feed, request_delay_seconds=1.5)

        self.assertEqual(len(papers), 2)
        request = mock_urlopen.call_args.args[0]
        query = parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(query["search_query"], ["(cat:cs.AI OR cat:cs.CL)"])
        self.assertEqual(query["max_results"], ["25"])
        self.assertEqual(query["sortBy"], ["submittedDate"])
        self.assertEqual(query["sortOrder"], ["descending"])
        mock_sleep.assert_called_once_with(1.5)

    @patch("paper_digest.arxiv_client.urlopen", side_effect=OSError("network down"))
    def test_fetch_latest_papers_wraps_oserror(self, _mock_urlopen) -> None:
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=[],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        with self.assertRaises(ArxivClientError):
            fetch_latest_papers(feed, request_delay_seconds=0)
