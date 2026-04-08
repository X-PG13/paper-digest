from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from paper_digest.cli import main
from paper_digest.config import AppConfig, FeedConfig
from paper_digest.digest import DigestRun


class CliTests(unittest.TestCase):
    @patch("paper_digest.cli.write_outputs")
    @patch("paper_digest.cli.generate_digest")
    @patch("paper_digest.cli.load_config")
    def test_main_returns_zero_on_success(
        self,
        mock_load_config,
        mock_generate_digest,
        mock_write_outputs,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=output_dir,
                request_delay_seconds=0.0,
                feeds=[
                    FeedConfig(
                        name="LLM",
                        categories=["cs.AI"],
                        keywords=["agent"],
                        exclude_keywords=[],
                        max_results=10,
                        max_items=5,
                    )
                ],
            )
            digest = DigestRun(
                generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
                timezone="UTC",
                lookback_hours=24,
                feeds=[],
            )
            mock_load_config.return_value = config
            mock_generate_digest.return_value = digest
            mock_write_outputs.return_value = (
                output_dir / "digest.json",
                output_dir / "digest.md",
            )

            exit_code = main(["--config", "config.toml", "--quiet"])

        self.assertEqual(exit_code, 0)

    def test_main_returns_nonzero_on_missing_config(self) -> None:
        exit_code = main(["--config", "does-not-exist.toml", "--quiet"])
        self.assertEqual(exit_code, 1)
