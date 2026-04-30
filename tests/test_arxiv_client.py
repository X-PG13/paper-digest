from __future__ import annotations

import unittest
from datetime import UTC
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from paper_digest.arxiv_client import (
    ArxivClientError,
    build_search_query,
    fetch_latest_papers,
    fetch_latest_papers_from_rss,
    parse_feed,
    parse_rss_feed,
)
from paper_digest.config import FeedConfig

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "arxiv_sample.xml"
RSS_PAYLOAD = b"""<?xml version='1.0' encoding='UTF-8'?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
  <channel>
    <item>
      <title>Shared Lexical Task Representations Explain LLM Variability</title>
      <link>https://arxiv.org/abs/2604.22027</link>
      <description>arXiv:2604.22027v1 Announce Type: new
Abstract: We study prompt sensitivity in large language models.</description>
      <guid isPermaLink="false">oai:arXiv.org:2604.22027v1</guid>
      <category>cs.CL</category>
      <pubDate>Tue, 28 Apr 2026 00:00:00 -0400</pubDate>
      <dc:creator>Alice Example, Bob Example</dc:creator>
    </item>
  </channel>
</rss>
"""
RSS_FALLBACK_PAYLOAD = b"""<?xml version='1.0' encoding='UTF-8'?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
  <channel>
    <item>
      <title>Language Model Distillation</title>
      <link>https://arxiv.org/abs/2604.30001v1</link>
      <description>Plain RSS summary without an abstract marker.</description>
      <guid isPermaLink="false">oai:arXiv.org:2604.30001v1</guid>
      <pubDate>Tue, 28 Apr 2026 00:00:00</pubDate>
      <dc:creator>Alice Example</dc:creator>
    </item>
    <item>
      <title>Language Model Distillation</title>
      <link>https://arxiv.org/abs/2604.30001v1</link>
      <description>Plain RSS summary without an abstract marker.</description>
      <guid isPermaLink="false">oai:arXiv.org:2604.30001v1</guid>
      <pubDate>Tue, 28 Apr 2026 00:00:00</pubDate>
      <dc:creator>Bob Example</dc:creator>
    </item>
  </channel>
</rss>
"""


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

    def test_parse_rss_feed_extracts_papers(self) -> None:
        papers = parse_rss_feed(RSS_PAYLOAD, category="cs.CL")

        self.assertEqual(len(papers), 1)
        self.assertEqual(
            papers[0].title,
            "Shared Lexical Task Representations Explain LLM Variability",
        )
        self.assertEqual(
            papers[0].summary,
            "We study prompt sensitivity in large language models.",
        )
        self.assertEqual(papers[0].authors, ["Alice Example", "Bob Example"])
        self.assertEqual(papers[0].categories, ["cs.CL"])
        self.assertEqual(papers[0].arxiv_id, "2604.22027")
        self.assertEqual(papers[0].pdf_url, "https://arxiv.org/pdf/2604.22027")

    def test_parse_rss_feed_rejects_invalid_payloads(self) -> None:
        with self.assertRaisesRegex(ArxivClientError, "malformed RSS"):
            parse_rss_feed(b"not xml", category="cs.CL")

        payload = RSS_PAYLOAD.replace(
            b"Tue, 28 Apr 2026 00:00:00 -0400",
            b"not-a-date",
        )
        with self.assertRaisesRegex(ArxivClientError, "invalid RSS datetime"):
            parse_rss_feed(payload, category="cs.CL")

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_papers_from_rss_skips_blank_categories_and_dedupes(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(RSS_FALLBACK_PAYLOAD)
        feed = FeedConfig(
            name="LM",
            categories=[" ", "cs.CL"],
            keywords=[],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_papers_from_rss(
            feed,
            request_delay_seconds=0,
            retry_attempts=1,
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(mock_urlopen.call_count, 1)
        self.assertEqual(papers[0].categories, ["cs.CL"])
        self.assertEqual(
            papers[0].summary,
            "Plain RSS summary without an abstract marker.",
        )
        self.assertEqual(papers[0].authors, ["Alice Example", "Bob Example"])
        self.assertEqual(papers[0].published_at.tzinfo, UTC)
        mock_sleep.assert_not_called()

    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_papers_from_rss_reports_direct_fetch_errors(
        self,
        mock_urlopen,
    ) -> None:
        mock_urlopen.side_effect = HTTPError(
            url="https://rss.arxiv.org/rss/cs.CL",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=None,
        )
        feed = FeedConfig(
            name="LM",
            categories=["cs.CL"],
            keywords=[],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        with self.assertRaisesRegex(ArxivClientError, "HTTP Error 503"):
            fetch_latest_papers_from_rss(
                feed,
                request_delay_seconds=0,
                retry_attempts=1,
            )

    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_papers_from_rss_reports_fallback_errors(
        self,
        mock_urlopen,
    ) -> None:
        mock_urlopen.side_effect = HTTPError(
            url="https://rss.arxiv.org/rss/cs.CL",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=None,
        )
        feed = FeedConfig(
            name="LM",
            categories=["cs.CL"],
            keywords=[],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        with self.assertRaisesRegex(
            ArxivClientError,
            "RSS fallback also failed",
        ):
            fetch_latest_papers_from_rss(
                feed,
                request_delay_seconds=0,
                retry_attempts=1,
                api_error=ArxivClientError("api failed"),
            )

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
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

    @patch("paper_digest.network.urlopen", side_effect=OSError("network down"))
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
            fetch_latest_papers(
                feed,
                request_delay_seconds=0,
                retry_attempts=1,
            )

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_papers_retries_retryable_http_errors(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        retryable = HTTPError(
            url="https://export.arxiv.org/api/query",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "7"},
            fp=None,
        )
        mock_urlopen.side_effect = [
            retryable,
            DummyHTTPResponse(FIXTURE_PATH.read_bytes()),
        ]
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=[],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_papers(feed, request_delay_seconds=3)

        self.assertEqual(len(papers), 2)
        self.assertEqual(mock_urlopen.call_count, 2)
        self.assertEqual(mock_sleep.call_args_list[0].args, (10.0,))
        self.assertEqual(mock_sleep.call_args_list[1].args, (3,))

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_papers_retries_timeout_errors(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.side_effect = [
            TimeoutError("The read operation timed out"),
            DummyHTTPResponse(FIXTURE_PATH.read_bytes()),
        ]
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=[],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_papers(
            feed,
            request_delay_seconds=2,
            request_timeout_seconds=45,
            retry_attempts=3,
            retry_backoff_seconds=6,
        )

        self.assertEqual(len(papers), 2)
        self.assertEqual(mock_urlopen.call_count, 2)
        self.assertEqual(mock_sleep.call_args_list[0].args, (6.0,))
        self.assertEqual(mock_sleep.call_args_list[1].args, (2,))

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_papers_falls_back_to_rss_after_api_429(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.side_effect = [
            HTTPError(
                url="https://export.arxiv.org/api/query",
                code=429,
                msg="Too Many Requests",
                hdrs={},
                fp=None,
            ),
            DummyHTTPResponse(RSS_PAYLOAD),
        ]
        feed = FeedConfig(
            name="LM",
            categories=["cs.CL"],
            keywords=["LLM"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_papers(
            feed,
            request_delay_seconds=0,
            retry_attempts=1,
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].source, "arxiv")
        self.assertEqual(papers[0].arxiv_id, "2604.22027")
        self.assertIn(
            "export.arxiv.org/api/query",
            mock_urlopen.call_args_list[0].args[0].full_url,
        )
        self.assertEqual(
            mock_urlopen.call_args_list[1].args[0].full_url,
            "https://rss.arxiv.org/rss/cs.CL",
        )
        mock_sleep.assert_not_called()
