from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from paper_digest.cli import main
from paper_digest.config import AppConfig, EmailConfig, FeedConfig
from paper_digest.digest import DigestRun
from paper_digest.email_delivery import EmailDeliveryError


class CliTests(unittest.TestCase):
    @patch("paper_digest.cli.write_outputs")
    @patch("paper_digest.cli.send_digest_email")
    @patch("paper_digest.cli.generate_digest")
    @patch("paper_digest.cli.load_config")
    def test_main_returns_zero_on_success(
        self,
        mock_load_config,
        mock_generate_digest,
        _mock_send_digest_email,
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

    @patch("paper_digest.cli.write_outputs")
    @patch("paper_digest.cli.send_digest_email")
    @patch("paper_digest.cli.generate_digest")
    @patch("paper_digest.cli.load_config")
    def test_main_sends_email_when_configured(
        self,
        mock_load_config,
        mock_generate_digest,
        mock_send_digest_email,
        mock_write_outputs,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=output_dir,
                request_delay_seconds=0.0,
                feeds=[],
                email=EmailConfig(
                    smtp_host="smtp.example.com",
                    smtp_port=465,
                    username=None,
                    password_env=None,
                    from_address="bot@example.com",
                    to_addresses=["reader@example.com"],
                    use_tls=True,
                    use_starttls=False,
                    subject_prefix="[Digest]",
                ),
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
        mock_send_digest_email.assert_called_once_with(config.email, digest)

    def test_main_returns_nonzero_on_missing_config(self) -> None:
        exit_code = main(["--config", "does-not-exist.toml", "--quiet"])
        self.assertEqual(exit_code, 1)

    @patch("paper_digest.cli.write_outputs")
    @patch(
        "paper_digest.cli.send_digest_email",
        side_effect=EmailDeliveryError("smtp failed"),
    )
    @patch("paper_digest.cli.generate_digest")
    @patch("paper_digest.cli.load_config")
    def test_main_returns_nonzero_on_email_failure(
        self,
        mock_load_config,
        mock_generate_digest,
        _mock_send_digest_email,
        mock_write_outputs,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=output_dir,
                request_delay_seconds=0.0,
                feeds=[],
                email=EmailConfig(
                    smtp_host="smtp.example.com",
                    smtp_port=465,
                    username=None,
                    password_env=None,
                    from_address="bot@example.com",
                    to_addresses=["reader@example.com"],
                    use_tls=True,
                    use_starttls=False,
                    subject_prefix="[Digest]",
                ),
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

        self.assertEqual(exit_code, 1)
