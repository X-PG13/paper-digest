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
            contact_email=None,
        )

        self.assertEqual(papers, [paper])
        mock_fetch_latest_papers.assert_called_once_with(
            feed,
            request_delay_seconds=0.0,
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
            contact_email="bot@example.com",
        )

        self.assertEqual(papers, [paper])
        mock_fetch_latest_crossref_papers.assert_called_once_with(
            feed,
            now=now,
            lookback_hours=24,
            request_delay_seconds=0.5,
            contact_email="bot@example.com",
        )
