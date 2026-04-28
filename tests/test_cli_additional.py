from __future__ import annotations

import io
import json
import runpy
import textwrap
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from paper_digest.cli import (
    _main_state,
    _parse_iso_date,
    _print_action_state_sync_preview,
    _print_feedback_sync_preview,
    build_parser,
    main,
)
from paper_digest.config import AppConfig, ConfigError, FeedConfig, StateConfig
from paper_digest.delivery import DeliveryError
from paper_digest.feedback import (
    FeedbackEntry,
    FeedbackState,
    diff_feedback_states,
)
from paper_digest.github_action_state import (
    GitHubActionStateResult,
    GitHubActionStateSyncError,
)
from paper_digest.github_feedback import (
    GitHubFeedbackPullResult,
    GitHubFeedbackSyncError,
)
from paper_digest.state import DigestState, diff_action_notifications


class CliAdditionalTests(unittest.TestCase):
    def _state_config(self, root: Path) -> StateConfig:
        return StateConfig(
            enabled=True,
            path=root / "state.json",
            retention_days=90,
        )

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

    def _run_main(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            exit_code = main(args)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def _feedback_pull_result(self) -> GitHubFeedbackPullResult:
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

    def test_build_parser_and_parse_iso_date_helpers(self) -> None:
        self.assertEqual(build_parser().parse_args([]).config, "config.toml")
        self.assertEqual(_parse_iso_date("2026-04-18").isoformat(), "2026-04-18")
        with self.assertRaisesRegex(ValueError, "invalid ISO date: 2026/04/18"):
            _parse_iso_date("2026/04/18")

    @patch("paper_digest.cli.save_state")
    @patch("paper_digest.cli.save_feedback")
    @patch("paper_digest.cli.send_configured_deliveries", return_value=["email sent"])
    @patch("paper_digest.cli.build_archive_site")
    @patch("paper_digest.cli.write_outputs")
    @patch("paper_digest.cli.generate_digest")
    @patch("paper_digest.cli.load_feedback")
    @patch("paper_digest.cli.load_state")
    @patch("paper_digest.cli.load_config")
    def test_main_digest_prints_success_summary_when_not_quiet(
        self,
        mock_load_config,
        mock_load_state,
        mock_load_feedback,
        mock_generate_digest,
        mock_write_outputs,
        mock_build_archive_site,
        _mock_send_configured_deliveries,
        _mock_save_feedback,
        _mock_save_state,
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
                    )
                ],
                state=self._state_config(output_dir),
            )
            state = DigestState(seen_papers={})
            feedback_state = FeedbackState(papers={})
            digest = mock_generate_digest.return_value
            digest.feeds = []
            json_path = output_dir / "digest.json"
            markdown_path = output_dir / "digest.md"
            site_path = output_dir / "site"
            mock_load_config.return_value = config
            mock_load_state.return_value = state
            mock_load_feedback.return_value = feedback_state
            mock_write_outputs.return_value = (json_path, markdown_path)
            mock_build_archive_site.return_value = site_path

            exit_code, stdout, stderr = self._run_main(["--config", "config.toml"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn(f"JSON written to {json_path.resolve()}", stdout)
        self.assertIn(f"Markdown written to {markdown_path.resolve()}", stdout)
        self.assertIn(f"Archive site written to {site_path.resolve()}", stdout)
        self.assertIn("Matched papers:", stdout)
        self.assertIn("email sent", stdout)

    @patch("paper_digest.cli.build_archive_site")
    @patch("paper_digest.cli.write_outputs", side_effect=DeliveryError("bad write"))
    @patch("paper_digest.cli.generate_digest")
    @patch("paper_digest.cli.load_feedback")
    @patch("paper_digest.cli.load_state")
    @patch("paper_digest.cli.load_config")
    def test_main_digest_error_before_artifacts_does_not_report_paths(
        self,
        mock_load_config,
        mock_load_state,
        mock_load_feedback,
        mock_generate_digest,
        _mock_write_outputs,
        _mock_build_archive_site,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            mock_load_config.return_value = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=output_dir,
                request_delay_seconds=0.0,
                feeds=[],
                state=self._state_config(output_dir),
            )
            mock_load_state.return_value = DigestState(seen_papers={})
            mock_load_feedback.return_value = FeedbackState(papers={})
            mock_generate_digest.return_value.feeds = []

            exit_code, _stdout, stderr = self._run_main(["--config", "config.toml"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Error: bad write", stderr)
        self.assertNotIn("Artifacts preserved at", stderr)

    def test_feedback_commands_cover_missing_entry_and_validation_paths(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            exit_code, stdout, stderr = self._run_main(
                [
                    "feedback",
                    "clear",
                    "doi:10.5555/example",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("No entry for doi:10.5555/example", stdout)
            self.assertEqual(stderr, "")

            exit_code, _stdout, stderr = self._run_main(
                [
                    "feedback",
                    "note",
                    "doi:10.5555/example",
                    "note",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("No entry for doi:10.5555/example", stderr)

            exit_code, stdout, _stderr = self._run_main(
                [
                    "feedback",
                    "clear-note",
                    "doi:10.5555/example",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("No note for doi:10.5555/example", stdout)

            exit_code, _stdout, stderr = self._run_main(
                [
                    "feedback",
                    "action",
                    "set",
                    "doi:10.5555/example",
                    "follow up",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("No entry for doi:10.5555/example", stderr)

            exit_code, stdout, _stderr = self._run_main(
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
            self.assertIn("No next action for doi:10.5555/example", stdout)

            exit_code, _stdout, stderr = self._run_main(
                [
                    "feedback",
                    "due",
                    "set",
                    "doi:10.5555/example",
                    "2026/04/18",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("due_date must use YYYY-MM-DD format", stderr)

            exit_code, _stdout, stderr = self._run_main(
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
            self.assertEqual(exit_code, 1)
            self.assertIn("No entry for doi:10.5555/example", stderr)

            exit_code, stdout, _stderr = self._run_main(
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
            self.assertIn("No due date for doi:10.5555/example", stdout)

            exit_code, _stdout, stderr = self._run_main(
                [
                    "feedback",
                    "snooze",
                    "set",
                    "doi:10.5555/example",
                    "2026/04/20",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("snoozed_until must use YYYY-MM-DD format", stderr)

            exit_code, _stdout, stderr = self._run_main(
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
            self.assertEqual(exit_code, 1)
            self.assertIn("No entry for doi:10.5555/example", stderr)

            exit_code, stdout, _stderr = self._run_main(
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
            self.assertIn("No snoozed-until for doi:10.5555/example", stdout)

            exit_code, _stdout, stderr = self._run_main(
                [
                    "feedback",
                    "interval",
                    "set",
                    "doi:10.5555/example",
                    "abc",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("review_interval_days must be a positive integer", stderr)

            exit_code, _stdout, stderr = self._run_main(
                [
                    "feedback",
                    "interval",
                    "set",
                    "doi:10.5555/example",
                    "0",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("review_interval_days must be a positive integer", stderr)

            exit_code, _stdout, stderr = self._run_main(
                [
                    "feedback",
                    "interval",
                    "set",
                    "doi:10.5555/example",
                    "7",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("No entry for doi:10.5555/example", stderr)

            exit_code, stdout, _stderr = self._run_main(
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
            self.assertIn("No review interval for doi:10.5555/example", stdout)

            exit_code, stdout, _stderr = self._run_main(
                ["feedback", "list", "--config", str(config_path)]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("No feedback entries found", stdout)

    @patch("paper_digest.cli.sync_feedback_to_github_secret")
    @patch("paper_digest.cli.pull_feedback_from_github_secret")
    def test_feedback_sync_push_preview_failure_branches(
        self,
        mock_pull_feedback_from_github_secret,
        mock_sync_feedback_to_github_secret,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            mock_pull_feedback_from_github_secret.side_effect = GitHubFeedbackSyncError(
                "preview failed"
            )
            exit_code, _stdout, stderr = self._run_main(
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
            self.assertEqual(exit_code, 1)
            self.assertIn("preview failed", stderr)
            mock_sync_feedback_to_github_secret.assert_not_called()

            mock_pull_feedback_from_github_secret.side_effect = None
            mock_pull_feedback_from_github_secret.return_value = None
            exit_code, _stdout, _stderr = self._run_main(
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
            self.assertEqual(exit_code, 1)

            mock_pull_feedback_from_github_secret.side_effect = GitHubFeedbackSyncError(
                "preview failed"
            )
            mock_sync_feedback_to_github_secret.return_value = "X-PG13/paper-digest"
            exit_code, stdout, stderr = self._run_main(
                [
                    "feedback",
                    "sync",
                    "--direction",
                    "push",
                    "--show-diff",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("Warning: could not fetch remote feedback preview", stderr)
            self.assertIn("Synced", stdout)

    def test_feedback_preview_helpers_can_skip_verbose_diffs(self) -> None:
        diff = diff_feedback_states(FeedbackState(papers={}), FeedbackState(papers={}))
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            _print_feedback_sync_preview(
                direction="pull",
                feedback_path=Path("/tmp/feedback.json"),
                secret_name="PAPER_DIGEST_FEEDBACK_JSON",
                repository="X-PG13/paper-digest",
                diff=diff,
                show_diff=False,
                merge_strategy="newer",
                run_id=None,
                dry_run=False,
            )
        self.assertIn("Preview: would pull", stdout.getvalue())
        self.assertIn("Diff summary: no changes", stdout.getvalue())

        action_diff = diff_action_notifications({}, {})
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            _print_action_state_sync_preview(
                direction="push",
                state_path=Path("/tmp/state.json"),
                repository="X-PG13/paper-digest",
                diff=action_diff,
                show_diff=False,
                run_id=None,
                dry_run=False,
            )
        self.assertIn("Preview: would sync action notifications", stdout.getvalue())
        self.assertIn("Diff summary: added=0, updated=0, removed=0", stdout.getvalue())

    @patch("paper_digest.cli.sync_action_notifications_to_github_actions")
    @patch("paper_digest.cli.pull_action_notifications_from_github_actions")
    def test_state_command_covers_empty_and_sync_preview_failure_paths(
        self,
        mock_pull_action_notifications_from_github_actions,
        mock_sync_action_notifications_to_github_actions,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)
            state_path = root / ".paper-digest-state" / "state.json"

            exit_code, stdout, _stderr = self._run_main(
                ["state", "action", "list", "--config", str(config_path)]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("No action notification entries found", stdout)

            exit_code, _stdout, stderr = self._run_main(
                ["state", "action", "reset", "--config", str(config_path)]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("provide a canonical_id", stderr)

            exit_code, stdout, _stderr = self._run_main(
                [
                    "state",
                    "action",
                    "reset",
                    "--reason",
                    "due_soon",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("No matching action notification entries", stdout)

            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "feeds": {},
                        "action_notifications": {
                            "arxiv:2604.06170": {
                                "due_soon": "2026-04-13T09:30:00+00:00",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            exit_code, stdout, _stderr = self._run_main(
                [
                    "state",
                    "action",
                    "reset",
                    "arxiv:2604.06170",
                    "--dry-run",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("Would clear 1 action notification entry", stdout)

            mock_pull_action_notifications_from_github_actions.side_effect = (
                GitHubActionStateSyncError("preview failed")
            )
            exit_code, _stdout, stderr = self._run_main(
                [
                    "state",
                    "action",
                    "sync",
                    "--direction",
                    "push",
                    "--dry-run",
                    "--show-diff",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 1)
            self.assertIn("preview failed", stderr)
            mock_sync_action_notifications_to_github_actions.assert_not_called()

            mock_pull_action_notifications_from_github_actions.side_effect = None
            mock_pull_action_notifications_from_github_actions.return_value = None
            exit_code, _stdout, _stderr = self._run_main(
                [
                    "state",
                    "action",
                    "sync",
                    "--direction",
                    "push",
                    "--dry-run",
                    "--show-diff",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 1)

            mock_pull_action_notifications_from_github_actions.side_effect = (
                GitHubActionStateSyncError("preview failed")
            )
            mock_sync_action_notifications_to_github_actions.return_value = (
                GitHubActionStateResult(
                    repository="X-PG13/paper-digest",
                    run_id="123456789",
                    run_url=(
                        "https://github.com/X-PG13/paper-digest/actions/runs/"
                        "123456789"
                    ),
                    action_notifications={},
                )
            )
            exit_code, stdout, stderr = self._run_main(
                [
                    "state",
                    "action",
                    "sync",
                    "--direction",
                    "push",
                    "--show-diff",
                    "--config",
                    str(config_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn(
                "Warning: could not fetch remote action state preview",
                stderr,
            )
            self.assertIn("Synced action notifications", stdout)

    @patch("paper_digest.cli.load_config", side_effect=ConfigError("bad config"))
    def test_feedback_and_state_commands_report_config_errors(
        self,
        _mock_load_config,
    ) -> None:
        feedback_exit_code, _stdout, feedback_stderr = self._run_main(
            ["feedback", "list"]
        )
        state_exit_code, _stdout, state_stderr = self._run_main(
            ["state", "action", "list"]
        )

        self.assertEqual(feedback_exit_code, 1)
        self.assertIn("Error: bad config", feedback_stderr)
        self.assertEqual(state_exit_code, 1)
        self.assertIn("Error: bad config", state_stderr)

    @patch(
        "paper_digest.cli.sync_feedback_to_github_secret",
        return_value="X-PG13/paper-digest",
    )
    @patch("paper_digest.cli.pull_feedback_from_github_secret")
    def test_feedback_sync_push_with_preview_continues_when_not_dry_run(
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

            exit_code, stdout, stderr = self._run_main(
                [
                    "feedback",
                    "sync",
                    "--direction",
                    "push",
                    "--show-diff",
                    "--config",
                    str(config_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Synced", stdout)
        mock_sync_feedback_to_github_secret.assert_called_once()

    @patch("paper_digest.cli.pull_feedback_from_github_secret")
    def test_feedback_sync_pull_with_preview_persists_when_not_dry_run(
        self,
        mock_pull_feedback_from_github_secret,
    ) -> None:
        mock_pull_feedback_from_github_secret.return_value = (
            self._feedback_pull_result()
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            exit_code, stdout, stderr = self._run_main(
                [
                    "feedback",
                    "sync",
                    "--direction",
                    "pull",
                    "--merge-strategy",
                    "remote",
                    "--show-diff",
                    "--config",
                    str(config_path),
                ]
            )
            feedback_path = root / ".paper-digest-state" / "feedback.json"
            payload = json.loads(feedback_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Pulled GitHub Actions secret", stdout)
        self.assertEqual(
            payload["papers"]["doi:10.5555/example"]["status"],
            "reading",
        )

    @patch("paper_digest.cli.sync_action_notifications_to_github_actions")
    def test_state_action_sync_push_without_preview_syncs_directly(
        self,
        mock_sync_action_notifications_to_github_actions,
    ) -> None:
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
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            mock_sync_action_notifications_to_github_actions.return_value = (
                GitHubActionStateResult(
                    repository="X-PG13/paper-digest",
                    run_id="123456789",
                    run_url=(
                        "https://github.com/X-PG13/paper-digest/actions/runs/"
                        "123456789"
                    ),
                    action_notifications={},
                )
            )

            exit_code, stdout, stderr = self._run_main(
                [
                    "state",
                    "action",
                    "sync",
                    "--direction",
                    "push",
                    "--config",
                    str(config_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Synced action notifications", stdout)
        mock_sync_action_notifications_to_github_actions.assert_called_once()

    @patch("paper_digest.cli.sync_action_notifications_to_github_actions")
    @patch("paper_digest.cli.pull_action_notifications_from_github_actions")
    def test_state_action_sync_push_with_preview_continues_when_not_dry_run(
        self,
        mock_pull_action_notifications_from_github_actions,
        mock_sync_action_notifications_to_github_actions,
    ) -> None:
        mock_pull_action_notifications_from_github_actions.return_value = (
            GitHubActionStateResult(
                repository="X-PG13/paper-digest",
                run_id="123456789",
                run_url=(
                    "https://github.com/X-PG13/paper-digest/actions/runs/"
                    "123456789"
                ),
                action_notifications={},
            )
        )
        mock_sync_action_notifications_to_github_actions.return_value = (
            GitHubActionStateResult(
                repository="X-PG13/paper-digest",
                run_id="123456789",
                run_url=(
                    "https://github.com/X-PG13/paper-digest/actions/runs/"
                    "123456789"
                ),
                action_notifications={},
            )
        )
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
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            exit_code, stdout, stderr = self._run_main(
                [
                    "state",
                    "action",
                    "sync",
                    "--direction",
                    "push",
                    "--show-diff",
                    "--config",
                    str(config_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Synced action notifications", stdout)
        mock_sync_action_notifications_to_github_actions.assert_called_once()

    @patch("paper_digest.cli.pull_action_notifications_from_github_actions")
    def test_state_action_sync_pull_persists_state_when_not_dry_run(
        self,
        mock_pull_action_notifications_from_github_actions,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)
            state_path = root / ".paper-digest-state" / "state.json"
            mock_pull_action_notifications_from_github_actions.return_value = (
                GitHubActionStateResult(
                    repository="X-PG13/paper-digest",
                    run_id="123456789",
                    run_url=(
                        "https://github.com/X-PG13/paper-digest/actions/runs/"
                        "123456789"
                    ),
                    action_notifications={
                        "arxiv:2604.06170": {
                            "due_soon": "2026-04-13T09:30:00+00:00",
                        }
                    },
                )
            )

            exit_code, stdout, stderr = self._run_main(
                [
                    "state",
                    "action",
                    "sync",
                    "--direction",
                    "pull",
                    "--config",
                    str(config_path),
                ]
            )
            state_payload = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Pulled action notifications from X-PG13/paper-digest", stdout)
        self.assertIn("run 123456789", stdout)
        self.assertEqual(
            state_payload["action_notifications"]["arxiv:2604.06170"]["due_soon"],
            "2026-04-13T09:30:00+00:00",
        )

    @patch("paper_digest.cli.pull_action_notifications_from_github_actions")
    def test_state_action_sync_pull_with_preview_persists_when_not_dry_run(
        self,
        mock_pull_action_notifications_from_github_actions,
    ) -> None:
        mock_pull_action_notifications_from_github_actions.return_value = (
            GitHubActionStateResult(
                repository="X-PG13/paper-digest",
                run_id="123456789",
                run_url=(
                    "https://github.com/X-PG13/paper-digest/actions/runs/"
                    "123456789"
                ),
                action_notifications={
                    "arxiv:2604.06170": {
                        "due_soon": "2026-04-13T09:30:00+00:00",
                    }
                },
            )
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            exit_code, stdout, stderr = self._run_main(
                [
                    "state",
                    "action",
                    "sync",
                    "--direction",
                    "pull",
                    "--show-diff",
                    "--config",
                    str(config_path),
                ]
            )
            state_path = root / ".paper-digest-state" / "state.json"
            state_payload = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Pulled action notifications", stdout)
        self.assertEqual(
            state_payload["action_notifications"]["arxiv:2604.06170"]["due_soon"],
            "2026-04-13T09:30:00+00:00",
        )

    def test_state_action_reset_prints_reason_and_before_filters_on_success(
        self,
    ) -> None:
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
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            exit_code, stdout, stderr = self._run_main(
                [
                    "state",
                    "action",
                    "reset",
                    "arxiv:2604.06170",
                    "--reason",
                    "due_soon",
                    "--before",
                    "2026-04-14",
                    "--config",
                    str(config_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Cleared 1 action notification entry", stdout)
        self.assertIn("(reason due_soon, before 2026-04-14)", stdout)

    def test_state_action_reset_can_succeed_without_optional_filters(self) -> None:
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
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            exit_code, stdout, stderr = self._run_main(
                [
                    "state",
                    "action",
                    "reset",
                    "arxiv:2604.06170",
                    "--config",
                    str(config_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn(
            "Cleared 1 action notification entry for arxiv:2604.06170",
            stdout,
        )
        self.assertNotIn("(", stdout)

    @patch("paper_digest.cli.clear_action_notifications", return_value=0)
    def test_state_action_reset_handles_zero_clears_without_success_message(
        self,
        mock_clear_action_notifications,
    ) -> None:
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
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            exit_code, stdout, stderr = self._run_main(
                [
                    "state",
                    "action",
                    "reset",
                    "arxiv:2604.06170",
                    "--config",
                    str(config_path),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        mock_clear_action_notifications.assert_called_once()

    @patch("paper_digest.cli.load_state", return_value=DigestState(seen_papers={}))
    @patch("paper_digest.cli.load_config")
    @patch("paper_digest.cli.build_state_parser")
    def test_main_state_rejects_unexpected_parser_command(
        self,
        mock_build_state_parser,
        mock_load_config,
        _mock_load_state,
    ) -> None:
        mock_build_state_parser.return_value.parse_args.return_value = SimpleNamespace(
            config="config.toml",
            state_command="unexpected",
        )
        mock_load_config.return_value = AppConfig(
            timezone="UTC",
            lookback_hours=24,
            output_dir=Path("output"),
            request_delay_seconds=0.0,
            feeds=[],
            state=self._state_config(Path(".")),
        )

        with self.assertRaisesRegex(AssertionError, "unsupported state command"):
            _main_state([])

    def test_cli_module_main_guard_exits_with_return_code(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = self._write_feedback_config(root)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch(
                    "sys.argv",
                    ["paper-digest", "feedback", "list", "--config", str(config_path)],
                ),
                patch("sys.stdout", stdout),
                patch("sys.stderr", stderr),
            ):
                with self.assertRaises(SystemExit) as raised:
                    runpy.run_module("paper_digest.cli", run_name="__main__")

        self.assertEqual(raised.exception.code, 0)
