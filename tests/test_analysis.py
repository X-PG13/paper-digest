from __future__ import annotations

import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from paper_digest.analysis import build_digest_highlights, enrich_digest_with_analysis
from paper_digest.arxiv_client import Paper, PaperAnalysis
from paper_digest.config import AnalysisConfig
from paper_digest.digest import DigestRun, FeedDigest


def build_paper(title: str) -> Paper:
    published_at = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)
    return Paper(
        title=title,
        summary=f"{title} summary",
        authors=["Alice"],
        categories=["cs.AI"],
        paper_id=f"https://arxiv.org/abs/{title}",
        abstract_url=f"https://arxiv.org/abs/{title}",
        pdf_url=None,
        published_at=published_at,
        updated_at=published_at,
    )


def build_config() -> AnalysisConfig:
    return AnalysisConfig(
        provider="openai",
        model="gpt-5-mini",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1/responses",
        timeout_seconds=60,
        max_papers=2,
        max_output_tokens=600,
        top_highlights=2,
        language="English",
        reasoning_effort="minimal",
    )


class AnalysisTests(unittest.TestCase):
    @patch("paper_digest.analysis.analyze_paper_with_openai")
    def test_enrich_digest_with_analysis_round_robins_across_feeds(
        self,
        mock_analyze_paper_with_openai,
    ) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[
                FeedDigest(name="LLM", papers=[build_paper("A"), build_paper("B")]),
                FeedDigest(name="Vision", papers=[build_paper("C")]),
            ],
        )
        mock_analyze_paper_with_openai.side_effect = [
            PaperAnalysis(conclusion="Analysis A"),
            PaperAnalysis(conclusion="Analysis C"),
        ]

        enrich_digest_with_analysis(build_config(), digest)

        self.assertEqual(mock_analyze_paper_with_openai.call_count, 2)
        self.assertEqual(digest.feeds[0].papers[0].analysis.conclusion, "Analysis A")
        self.assertEqual(digest.feeds[1].papers[0].analysis.conclusion, "Analysis C")
        self.assertIsNone(digest.feeds[0].papers[1].analysis)
        self.assertEqual(len(digest.highlights), 2)

    def test_build_digest_highlights_falls_back_to_raw_summary(self) -> None:
        paper = build_paper("A")
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[paper])],
        )

        highlights = build_digest_highlights(digest, 1)

        self.assertEqual(highlights, ["LLM: A - A summary"])
