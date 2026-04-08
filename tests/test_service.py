from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from paper_digest.arxiv_client import Paper
from paper_digest.config import AppConfig, FeedConfig
from paper_digest.service import generate_digest


class GenerateDigestTests(unittest.TestCase):
    @patch("paper_digest.service.fetch_latest_papers")
    def test_generate_digest_uses_configured_timezone_and_filters(
        self,
        mock_fetch_latest_papers,
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
        mock_fetch_latest_papers.return_value = [recent_paper, non_matching_paper]
        config = AppConfig(
            timezone="Asia/Shanghai",
            lookback_hours=24,
            output_dir=Path("/tmp/paper-digest-tests"),
            request_delay_seconds=0.0,
            feeds=[feed],
        )

        digest = generate_digest(config, now=now)

        self.assertEqual(digest.generated_at, now)
        self.assertEqual(len(digest.feeds), 1)
        self.assertEqual(
            [paper.title for paper in digest.feeds[0].papers],
            ["Agent systems"],
        )
        mock_fetch_latest_papers.assert_called_once_with(
            feed,
            request_delay_seconds=0.0,
        )
