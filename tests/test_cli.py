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
from paper_digest.feedback import FeedbackEntry, FeedbackState
from paper_digest.state import DigestState


class CliTests(unittest.TestCase):
    def _state_config(self, root: Path) -> StateConfig:
        return StateConfig(
            enabled=True,
            path=root / "state.json",
            retention_days=90,
        )

    @patch("paper_digest.cli.save_state")
    @patch("paper_digest.cli.save_feedback")
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
        mock_save_feedback,
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
            digest_state=state,
        )
        mock_send_configured_deliveries.assert_called_once_with(config, digest)
        mock_save_feedback.assert_called_once_with(config.feedback, feedback_state)
        mock_save_state.assert_called_once_with(config.state, state)

    def test_main_returns_nonzero_on_missing_config(self) -> None:
        exit_code = main(["--config", "does-not-exist.toml", "--quiet"])
        self.assertEqual(exit_code, 1)

    @patch("paper_digest.cli.save_state")
    @patch("paper_digest.cli.save_feedback")
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
        mock_save_feedback,
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
        mock_save_feedback.assert_not_called()
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

    def test_state_action_list_reports_notification_entries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)
            state_path = root / ".paper-digest-state" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "feeds": {},
                        "action_notifications": {
                            "arxiv:2604.06170": {
                                "due_soon": "2026-04-13T09:30:00+00:00",
                                "overdue_3d": "2026-04-16T09:30:00+00:00",
                            }
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "state",
                        "action",
                        "list",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn(
                "arxiv:2604.06170\toverdue_3d\t2026-04-16T09:30:00+00:00",
                stdout.getvalue(),
            )
            self.assertIn(
                "arxiv:2604.06170\tdue_soon\t2026-04-13T09:30:00+00:00",
                stdout.getvalue(),
            )

    def test_state_action_reset_can_clear_reason_across_entries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)
            state_path = root / ".paper-digest-state" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "feeds": {},
                        "action_notifications": {
                            "arxiv:2604.06170": {
                                "due_soon": "2026-04-13T09:30:00+00:00",
                                "overdue_3d": "2026-04-16T09:30:00+00:00",
                            },
                            "pubmed:41951858": {
                                "overdue_3d": "2026-04-17T09:30:00+00:00",
                            },
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "state",
                        "action",
                        "reset",
                        "--reason",
                        "overdue_3d",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["action_notifications"],
                {
                    "arxiv:2604.06170": {
                        "due_soon": "2026-04-13T09:30:00+00:00",
                    }
                },
            )
            self.assertIn(
                "Cleared 2 action notification entries",
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

    def test_feedback_snooze_and_interval_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)
            feedback_path = root / ".paper-digest-state" / "feedback.json"

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

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "snooze",
                        "set",
                        "doi:10.5555/example",
                        "2026-04-20",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["papers"]["doi:10.5555/example"]["snoozed_until"],
                "2026-04-20",
            )
            self.assertIn(
                "Updated snoozed-until for doi:10.5555/example -> 2026-04-20",
                stdout.getvalue(),
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "interval",
                        "set",
                        "doi:10.5555/example",
                        "14",
                        "--config",
                        str(config_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["papers"]["doi:10.5555/example"]["review_interval_days"],
                14,
            )
            self.assertIn(
                "Updated review interval for doi:10.5555/example -> 14 days",
                stdout.getvalue(),
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(["feedback", "list", "--config", str(config_path)])

            self.assertEqual(exit_code, 0)
            self.assertIn("2026-04-20", stdout.getvalue())
            self.assertIn("\t14\t", stdout.getvalue())

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "snooze",
                        "clear",
                        "doi:10.5555/example",
                        "--config",
                        str(config_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertIn(
                "Cleared snoozed-until for doi:10.5555/example",
                stdout.getvalue(),
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "interval",
                        "clear",
                        "doi:10.5555/example",
                        "--config",
                        str(config_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertIn(
                "Cleared review interval for doi:10.5555/example",
                stdout.getvalue(),
            )

    @patch("paper_digest.cli.sync_feedback_to_github_secret")
    def test_feedback_sync_direction_push_updates_github_secret(
        self,
        mock_sync_feedback_to_github_secret,
    ) -> None:
        mock_sync_feedback_to_github_secret.return_value = "X-PG13/paper-digest"
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            main(
                [
                    "feedback",
                    "set",
                    "doi:10.5555/example",
                    "star",
                    "--config",
                    str(config_path),
                ]
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "sync",
                        "--direction",
                        "push",
                        "--config",
                        str(config_path),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn(
            "Synced",
            stdout.getvalue(),
        )

    @patch("paper_digest.cli.pull_feedback_from_github_secret")
    def test_feedback_sync_direction_pull_restores_local_feedback_file(
        self,
        mock_pull_feedback_from_github_secret,
    ) -> None:
        mock_pull_feedback_from_github_secret.return_value = (
            self._feedback_pull_result()
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "sync",
                        "--direction",
                        "pull",
                        "--config",
                        str(config_path),
                    ]
                )

            feedback_path = root / ".paper-digest-state" / "feedback.json"
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["papers"]["doi:10.5555/example"]["status"],
            "reading",
        )
        self.assertEqual(
            payload["papers"]["doi:10.5555/example"]["note"],
            "pulled from GitHub",
        )
        self.assertIn(
            "Pulled GitHub Actions secret PAPER_DIGEST_FEEDBACK_JSON for "
            "X-PG13/paper-digest",
            stdout.getvalue(),
        )
        self.assertIn("merge=newer", stdout.getvalue())

    @patch("paper_digest.cli.pull_feedback_from_github_secret")
    def test_feedback_sync_direction_pull_can_prefer_local_entry(
        self,
        mock_pull_feedback_from_github_secret,
    ) -> None:
        mock_pull_feedback_from_github_secret.return_value = (
            self._feedback_pull_result()
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            main(
                [
                    "feedback",
                    "set",
                    "doi:10.5555/example",
                    "star",
                    "--note",
                    "keep local note",
                    "--config",
                    str(config_path),
                ]
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "sync",
                        "--direction",
                        "pull",
                        "--merge-strategy",
                        "local",
                        "--config",
                        str(config_path),
                    ]
                )

            feedback_path = root / ".paper-digest-state" / "feedback.json"
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["papers"]["doi:10.5555/example"]["status"],
            "star",
        )
        self.assertEqual(
            payload["papers"]["doi:10.5555/example"]["note"],
            "keep local note",
        )
        self.assertIn("merge=local", stdout.getvalue())

    @patch("paper_digest.cli.pull_feedback_from_github_secret")
    def test_feedback_sync_direction_pull_dry_run_does_not_write_file(
        self,
        mock_pull_feedback_from_github_secret,
    ) -> None:
        mock_pull_feedback_from_github_secret.return_value = (
            self._feedback_pull_result()
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            main(
                [
                    "feedback",
                    "set",
                    "doi:10.5555/example",
                    "star",
                    "--note",
                    "keep local note",
                    "--config",
                    str(config_path),
                ]
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "sync",
                        "--direction",
                        "pull",
                        "--merge-strategy",
                        "remote",
                        "--dry-run",
                        "--show-diff",
                        "--config",
                        str(config_path),
                    ]
                )

            feedback_path = root / ".paper-digest-state" / "feedback.json"
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["papers"]["doi:10.5555/example"]["status"],
            "star",
        )
        self.assertEqual(
            payload["papers"]["doi:10.5555/example"]["note"],
            "keep local note",
        )
        self.assertIn("Dry run: would pull", stdout.getvalue())
        self.assertIn("Diff summary:", stdout.getvalue())
        self.assertIn("status: star -> reading", stdout.getvalue())

    @patch("paper_digest.cli.sync_feedback_to_github_secret")
    @patch("paper_digest.cli.pull_feedback_from_github_secret")
    def test_feedback_sync_direction_push_dry_run_previews_remote_diff(
        self,
        mock_pull_feedback_from_github_secret,
        mock_sync_feedback_to_github_secret,
    ) -> None:
        mock_pull_feedback_from_github_secret.return_value = (
            self._feedback_pull_result()
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            main(
                [
                    "feedback",
                    "set",
                    "doi:10.5555/example",
                    "star",
                    "--note",
                    "keep local note",
                    "--config",
                    str(config_path),
                ]
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "feedback",
                        "sync",
                        "--direction",
                        "push",
                        "--dry-run",
                        "--show-diff",
                        "--config",
                        str(config_path),
                    ]
                )

        self.assertEqual(exit_code, 0)
        mock_sync_feedback_to_github_secret.assert_not_called()
        self.assertIn("Dry run: would sync", stdout.getvalue())
        self.assertIn("Diff summary:", stdout.getvalue())
        self.assertIn("status: reading -> star", stdout.getvalue())
        self.assertIn("note: pulled from GitHub -> keep local note", stdout.getvalue())

    def _feedback_pull_result(self):
        from paper_digest.github_feedback import GitHubFeedbackPullResult

        return GitHubFeedbackPullResult(
            repository="X-PG13/paper-digest",
            run_id="123456789",
            run_url="https://github.com/X-PG13/paper-digest/actions/runs/123456789",
            feedback_state=FeedbackState(
                papers={
                    "doi:10.5555/example": FeedbackEntry(
                        status="reading",
                        updated_at=datetime(2026, 4, 12, 10, 0, tzinfo=UTC),
                        note="pulled from GitHub",
                    )
                }
            ),
        )
