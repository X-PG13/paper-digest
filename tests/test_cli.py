from __future__ import annotations

import io
import json
import textwrap
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from paper_digest.cli import main
from paper_digest.config import AppConfig, FeedConfig, StateConfig
from paper_digest.delivery import DeliveryError
from paper_digest.digest import DigestRun, FeedDigest
from paper_digest.feedback import FeedbackState
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
    @patch("paper_digest.cli.load_feedback")
    @patch("paper_digest.cli.load_state")
    @patch("paper_digest.cli.load_config")
    def test_main_returns_zero_on_success(
        self,
        mock_load_config,
        mock_load_state,
        mock_load_feedback,
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
            feedback_state = FeedbackState(papers={})
            digest = DigestRun(
                generated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
                timezone="UTC",
                lookback_hours=24,
                feeds=[],
            )
            mock_load_config.return_value = config
            mock_load_state.return_value = state
            mock_load_feedback.return_value = feedback_state
            mock_generate_digest.return_value = digest
            mock_write_outputs.return_value = (
                output_dir / "digest.json",
                output_dir / "digest.md",
            )
            mock_build_archive_site.return_value = output_dir / "site"
            mock_send_configured_deliveries.return_value = []

            exit_code = main(["--config", "config.toml", "--quiet"])

        self.assertEqual(exit_code, 0)
        mock_generate_digest.assert_called_once_with(
            config,
            state=state,
            feedback_state=feedback_state,
        )
        mock_build_archive_site.assert_called_once_with(
            config.output_dir,
            tracked_keywords=["agent", "reasoning"],
            feedback_state=feedback_state,
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
    @patch("paper_digest.cli.load_feedback")
    @patch("paper_digest.cli.load_state")
    @patch("paper_digest.cli.load_config")
    def test_main_returns_nonzero_on_delivery_failure_and_preserves_artifacts(
        self,
        mock_load_config,
        mock_load_state,
        mock_load_feedback,
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
            feedback_state = FeedbackState(papers={})
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
            mock_load_feedback.return_value = feedback_state
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

    def _write_feedback_config(self, root: Path) -> Path:
        config_path = root / "config.toml"
        config_path.write_text(
            textwrap.dedent(
                """
                [app]
                timezone = "UTC"
                output_dir = "output"

                [state]
                enabled = true
                path = ".paper-digest-state/state.json"
                retention_days = 90

                [feedback]
                enabled = true
                path = ".paper-digest-state/feedback.json"

                [[feeds]]
                name = "LLM"
                categories = ["cs.AI"]
                keywords = ["agent"]
                """
            ).strip(),
            encoding="utf-8",
        )
        return config_path

    def test_feedback_set_and_list_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "set",
                        "doi:10.5555/example",
                        "star",
                        "--note",
                        "first pass note",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            feedback_path = root / ".paper-digest-state" / "feedback.json"
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["papers"]["doi:10.5555/example"]["status"],
                "star",
            )
            self.assertEqual(
                payload["papers"]["doi:10.5555/example"]["note"],
                "first pass note",
            )
            self.assertIn("Set doi:10.5555/example -> star", stdout.getvalue())

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "list",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn(
                "star\tdoi:10.5555/example\t",
                stdout.getvalue(),
            )
            self.assertIn("first pass note", stdout.getvalue())

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "set",
                        "doi:10.5555/example",
                        "reading",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["papers"]["doi:10.5555/example"]["status"],
                "reading",
            )
            self.assertIn("Set doi:10.5555/example -> reading", stdout.getvalue())

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "note",
                        "doi:10.5555/example",
                        "deep dive on evaluation setup",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["papers"]["doi:10.5555/example"]["note"],
                "deep dive on evaluation setup",
            )
            self.assertIn(
                "Updated note for doi:10.5555/example",
                stdout.getvalue(),
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "clear-note",
                        "doi:10.5555/example",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))
            self.assertNotIn("note", payload["papers"]["doi:10.5555/example"])
            self.assertIn(
                "Cleared note for doi:10.5555/example",
                stdout.getvalue(),
            )

    def test_feedback_clear_removes_entry(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)
            feedback_path = root / ".paper-digest-state" / "feedback.json"
            feedback_path.parent.mkdir(parents=True, exist_ok=True)
            feedback_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "papers": {
                            "doi:10.5555/example": {
                                "status": "follow_up",
                                "updated_at": "2026-04-10T09:15:00+08:00",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "clear",
                        "doi:10.5555/example",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["papers"], {})
            self.assertIn("Cleared doi:10.5555/example", stdout.getvalue())

    def test_feedback_action_and_due_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)
            feedback_path = root / ".paper-digest-state" / "feedback.json"

            exit_code = main(
                [
                    "feedback",
                    "set",
                    "doi:10.5555/example",
                    "star",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 0)

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "action",
                        "set",
                        "doi:10.5555/example",
                        "compare baseline table",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["papers"]["doi:10.5555/example"]["next_action"],
                "compare baseline table",
            )
            self.assertIn(
                "Updated next action for doi:10.5555/example",
                stdout.getvalue(),
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "due",
                        "set",
                        "doi:10.5555/example",
                        "2026-04-18",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["papers"]["doi:10.5555/example"]["due_date"],
                "2026-04-18",
            )
            self.assertIn(
                "Updated due date for doi:10.5555/example -> 2026-04-18",
                stdout.getvalue(),
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(["feedback", "list", "--config", str(config_path)])

            self.assertEqual(exit_code, 0)
            self.assertIn("2026-04-18", stdout.getvalue())
            self.assertIn("compare baseline table", stdout.getvalue())

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "action",
                        "clear",
                        "doi:10.5555/example",
                        "--config",
                        str(config_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertIn(
                "Cleared next action for doi:10.5555/example",
                stdout.getvalue(),
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "due",
                        "clear",
                        "doi:10.5555/example",
                        "--config",
                        str(config_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertIn(
                "Cleared due date for doi:10.5555/example",
                stdout.getvalue(),
            )
