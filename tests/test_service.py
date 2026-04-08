from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zoneinfo import ZoneInfo

from paper_digest.arxiv_client import Paper
from paper_digest.config import AppConfig, FeedConfig, StateConfig
from paper_digest.service import generate_digest


class GenerateDigestTests(unittest.TestCase):
    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_uses_configured_timezone_and_filters(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        recent_paper = Paper(
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
        non_matching_paper = Paper(
            title="Compiler optimizations",
            summary="Nothing about the topic",
            authors=["Bob"],
            categories=["cs.PL"],
            paper_id="http://arxiv.org/abs/2604.00002v1",
            abstract_url="https://arxiv.org/abs/2604.00002v1",
            pdf_url=None,
            published_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
            updated_at=datetime(2026, 4, 8, 0, 30, tzinfo=ZoneInfo("UTC")),
        )
        mock_fetch_feed_papers.return_value = [recent_paper, non_matching_paper]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="Asia/Shanghai",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )

            digest = generate_digest(config, now=now)

        self.assertEqual(digest.generated_at, now)
        self.assertEqual(len(digest.feeds), 1)
        self.assertEqual(
            [paper.title for paper in digest.feeds[0].papers],
            ["Agent systems"],
        )
        mock_fetch_feed_papers.assert_called_once_with(
            feed,
            now=now.astimezone(ZoneInfo("UTC")),
            lookback_hours=24,
            request_delay_seconds=0.0,
            contact_email=None,
        )

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_dedupes_against_state(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=ZoneInfo("UTC"))
        feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=[],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
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
        mock_fetch_feed_papers.return_value = [paper]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )

            first_digest = generate_digest(config, now=now)
            second_digest = generate_digest(config, now=now)

        self.assertEqual(len(first_digest.feeds[0].papers), 1)
        self.assertEqual(len(second_digest.feeds[0].papers), 0)
