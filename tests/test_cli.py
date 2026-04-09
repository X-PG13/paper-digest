from __future__ import annotations

import io
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from paper_digest.cli import main
from paper_digest.config import AppConfig, FeedConfig, StateConfig
from paper_digest.delivery import DeliveryError
from paper_digest.digest import DigestRun, FeedDigest
from paper_digest.state import DigestState


class CliTests(unittest.TestCase):
    def _state_config(self, root: Path) -> StateConfig:
        return StateConfig(
            enabled=True,
            path=root / "state.json",
            retention_days=90,
        )

    @patch("paper_digest.cli.save_state")
    @patch("paper_digest.cli.send_configured_deliveries")
    @patch("paper_digest.cli.build_archive_site")
    @patch("paper_digest.cli.write_outputs")
    @patch("paper_digest.cli.generate_digest")
    @patch("paper_digest.cli.load_state")
    @patch("paper_digest.cli.load_config")
    def test_main_returns_zero_on_success(
        self,
        mock_load_config,
        mock_load_state,
        mock_generate_digest,
        mock_write_outputs,
        mock_build_archive_site,
        mock_send_configured_deliveries,
        mock_save_state,
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
                        categories=["cs.CL"],
                        keywords=["agent", "reasoning", "agent"],
                    )
                ],
                state=self._state_config(output_dir),
            )
            state = DigestState(seen_papers={})
            digest = DigestRun(
                generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
                timezone="UTC",
                lookback_hours=24,
                feeds=[],
            )
            mock_load_config.return_value = config
            mock_load_state.return_value = state
            mock_generate_digest.return_value = digest
            mock_write_outputs.return_value = (
                output_dir / "digest.json",
                output_dir / "digest.md",
            )
            mock_build_archive_site.return_value = output_dir / "site"
            mock_send_configured_deliveries.return_value = []

            exit_code = main(["--config", "config.toml", "--quiet"])

        self.assertEqual(exit_code, 0)
        mock_generate_digest.assert_called_once_with(config, state=state)
        mock_build_archive_site.assert_called_once_with(
            config.output_dir,
            tracked_keywords=["agent", "reasoning"],
        )
        mock_send_configured_deliveries.assert_called_once_with(config, digest)
        mock_save_state.assert_called_once_with(config.state, state)

    def test_main_returns_nonzero_on_missing_config(self) -> None:
        exit_code = main(["--config", "does-not-exist.toml", "--quiet"])
        self.assertEqual(exit_code, 1)

    @patch("paper_digest.cli.save_state")
    @patch(
        "paper_digest.cli.send_configured_deliveries",
        side_effect=DeliveryError("delivery failed"),
    )
    @patch("paper_digest.cli.build_archive_site")
    @patch("paper_digest.cli.write_outputs")
    @patch("paper_digest.cli.generate_digest")
    @patch("paper_digest.cli.load_state")
    @patch("paper_digest.cli.load_config")
    def test_main_returns_nonzero_on_delivery_failure_and_preserves_artifacts(
        self,
        mock_load_config,
        mock_load_state,
        mock_generate_digest,
        mock_write_outputs,
        mock_build_archive_site,
        _mock_send_configured_deliveries,
        mock_save_state,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=output_dir,
                request_delay_seconds=0.0,
                feeds=[],
                state=self._state_config(output_dir),
            )
            state = DigestState(seen_papers={})
            digest = DigestRun(
                generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
                timezone="UTC",
                lookback_hours=24,
                feeds=[FeedDigest(name="LLM", papers=[])],
            )
            json_path = output_dir / "digest.json"
            markdown_path = output_dir / "digest.md"
            mock_load_config.return_value = config
            mock_load_state.return_value = state
            mock_generate_digest.return_value = digest
            mock_write_outputs.return_value = (json_path, markdown_path)
            mock_build_archive_site.return_value = output_dir / "site"

            stderr = io.StringIO()
            with patch("sys.stderr", stderr):
                exit_code = main(["--config", "config.toml", "--quiet"])

        self.assertEqual(exit_code, 1)
        self.assertIn("delivery failed", stderr.getvalue())
        self.assertIn("Artifacts preserved at", stderr.getvalue())
        mock_save_state.assert_not_called()
