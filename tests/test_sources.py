from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from paper_digest.arxiv_client import Paper
from paper_digest.config import FeedConfig
from paper_digest.sources import fetch_feed_papers


class SourceDispatchTests(unittest.TestCase):
    @patch("paper_digest.sources.fetch_latest_papers")
    def test_fetch_feed_papers_dispatches_to_arxiv(
        self,
        mock_fetch_latest_papers,
    ) -> None:
        paper = Paper(
            title="Agent systems",
            summary="Agent summary",
            authors=["Alice"],
            categories=["cs.AI"],
            paper_id="http://arxiv.org/abs/2604.00001v1",
            abstract_url="https://arxiv.org/abs/2604.00001v1",
            pdf_url="https://arxiv.org/pdf/2604.00001v1",
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_latest_papers.return_value = [paper]
        feed = FeedConfig(
            name="LLM",
            source="arxiv",
            categories=["cs.AI"],
        )

        papers = fetch_feed_papers(
            feed,
            now=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            lookback_hours=24,
            request_delay_seconds=0.0,
            request_timeout_seconds=45,
            retry_attempts=3,
            retry_backoff_seconds=5.0,
            contact_email=None,
            openalex_api_key=None,
        )

        self.assertEqual(papers, [paper])
        mock_fetch_latest_papers.assert_called_once_with(
            feed,
            request_delay_seconds=0.0,
            request_timeout_seconds=45,
            retry_attempts=3,
            retry_backoff_seconds=5.0,
        )

    @patch("paper_digest.sources.fetch_latest_crossref_papers")
    def test_fetch_feed_papers_dispatches_to_crossref(
        self,
        mock_fetch_latest_crossref_papers,
    ) -> None:
        paper = Paper(
            title="Agent systems",
            summary="Agent summary",
            authors=["Alice"],
            categories=["AI"],
            paper_id="https://doi.org/10.5555/example",
            abstract_url="https://doi.org/10.5555/example",
            pdf_url=None,
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            source="crossref",
            date_label="Indexed",
        )
        mock_fetch_latest_crossref_papers.return_value = [paper]
        feed = FeedConfig(
            name="Biomedical",
            source="crossref",
            queries=["multi agent systems"],
            types=["journal-article"],
        )
        now = datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC"))

        papers = fetch_feed_papers(
            feed,
            now=now,
            lookback_hours=24,
            request_delay_seconds=0.5,
            request_timeout_seconds=60,
            retry_attempts=4,
            retry_backoff_seconds=6.0,
            contact_email="bot@example.com",
            openalex_api_key=None,
        )

        self.assertEqual(papers, [paper])
        mock_fetch_latest_crossref_papers.assert_called_once_with(
            feed,
            now=now,
            lookback_hours=24,
            request_delay_seconds=0.5,
            request_timeout_seconds=60,
            retry_attempts=4,
            retry_backoff_seconds=6.0,
            contact_email="bot@example.com",
        )

    @patch("paper_digest.sources.fetch_latest_pubmed_papers")
    def test_fetch_feed_papers_dispatches_to_pubmed(
        self,
        mock_fetch_latest_pubmed_papers,
    ) -> None:
        paper = Paper(
            title="PubMed agents",
            summary="PubMed summary",
            authors=["Alice"],
            categories=["Journal Article"],
            paper_id="pubmed:12345",
            abstract_url="https://pubmed.ncbi.nlm.nih.gov/12345/",
            pdf_url=None,
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            source="pubmed",
            date_label="Entered",
        )
        mock_fetch_latest_pubmed_papers.return_value = [paper]
        feed = FeedConfig(
            name="PubMed AI",
            source="pubmed",
            queries=["agent systems"],
            types=["Journal Article"],
        )
        now = datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC"))

        papers = fetch_feed_papers(
            feed,
            now=now,
            lookback_hours=24,
            request_delay_seconds=0.25,
            request_timeout_seconds=30,
            retry_attempts=2,
            retry_backoff_seconds=3.0,
            contact_email="bot@example.com",
            openalex_api_key=None,
        )

        self.assertEqual(papers, [paper])
        mock_fetch_latest_pubmed_papers.assert_called_once_with(
            feed,
            now=now,
            lookback_hours=24,
            request_delay_seconds=0.25,
            request_timeout_seconds=30,
            retry_attempts=2,
            retry_backoff_seconds=3.0,
            contact_email="bot@example.com",
        )

    @patch("paper_digest.sources.fetch_latest_semantic_scholar_papers")
    def test_fetch_feed_papers_dispatches_to_semantic_scholar(
        self,
        mock_fetch_latest_semantic_scholar_papers,
    ) -> None:
        paper = Paper(
            title="Semantic Scholar agents",
            summary="Semantic Scholar summary",
            authors=["Alice"],
            categories=["Computer Science"],
            paper_id="semantic_scholar:abc123",
            abstract_url="https://arxiv.org/abs/2604.06666",
            pdf_url="https://arxiv.org/pdf/2604.06666.pdf",
            published_at=datetime(2026, 4, 8, 0, 0, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 0, tzinfo=ZoneInfo("UTC")),
            source="semantic_scholar",
            date_label="Published",
        )
        mock_fetch_latest_semantic_scholar_papers.return_value = [paper]
        feed = FeedConfig(
            name="Semantic Scholar AI",
            source="semantic_scholar",
            queries=["large language model", "agent"],
            types=["Review"],
        )
        now = datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC"))

        papers = fetch_feed_papers(
            feed,
            now=now,
            lookback_hours=24,
            request_delay_seconds=0.25,
            request_timeout_seconds=30,
            retry_attempts=2,
            retry_backoff_seconds=3.0,
            contact_email="bot@example.com",
            openalex_api_key=None,
        )

        self.assertEqual(papers, [paper])
        mock_fetch_latest_semantic_scholar_papers.assert_called_once_with(
            feed,
            now=now,
            lookback_hours=24,
            request_delay_seconds=0.25,
            request_timeout_seconds=30,
            retry_attempts=2,
            retry_backoff_seconds=3.0,
            contact_email="bot@example.com",
        )

    @patch("paper_digest.sources.fetch_latest_openalex_papers")
    def test_fetch_feed_papers_dispatches_to_openalex(
        self,
        mock_fetch_latest_openalex_papers,
    ) -> None:
        paper = Paper(
            title="OpenAlex agents",
            summary="OpenAlex summary",
            authors=["Alice"],
            categories=["Article", "Computer Science"],
            paper_id="openalex:W123",
            abstract_url="https://doi.org/10.5555/openalex",
            pdf_url="https://example.com/openalex.pdf",
            published_at=datetime(2026, 4, 8, 0, 0, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 0, tzinfo=ZoneInfo("UTC")),
            source="openalex",
            date_label="Published",
        )
        mock_fetch_latest_openalex_papers.return_value = [paper]
        feed = FeedConfig(
            name="OpenAlex AI",
            source="openalex",
            queries=["large language model", "agent systems"],
            types=["article"],
        )
        now = datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC"))

        papers = fetch_feed_papers(
            feed,
            now=now,
            lookback_hours=24,
            request_delay_seconds=0.25,
            request_timeout_seconds=30,
            retry_attempts=2,
            retry_backoff_seconds=3.0,
            contact_email="bot@example.com",
            openalex_api_key="openalex-secret",
        )

        self.assertEqual(papers, [paper])
        mock_fetch_latest_openalex_papers.assert_called_once_with(
            feed,
            now=now,
            lookback_hours=24,
            request_delay_seconds=0.25,
            request_timeout_seconds=30,
            retry_attempts=2,
            retry_backoff_seconds=3.0,
            contact_email="bot@example.com",
            api_key="openalex-secret",
        )
