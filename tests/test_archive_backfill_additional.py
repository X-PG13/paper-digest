from __future__ import annotations

import io
import json
import runpy
import unittest
import warnings
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from paper_digest.archive_backfill import (
    ArchiveBackfillError,
    BackfillWindow,
    _collect_snapshots,
    _load_snapshot,
    _parse_filter_date,
    _refresh_latest_files,
    _tracked_keywords,
    backfill_archive_history,
    main,
)
from paper_digest.config import AppConfig, FeedConfig, StateConfig


class ArchiveBackfillAdditionalTests(unittest.TestCase):
    def test_backfill_skips_existing_snapshot_with_equal_rank(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            artifacts_dir = root / "artifacts"

            self._write_digest(
                output_dir,
                "2026-04-08",
                generated_at="2026-04-08T08:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [{"title": "Current", "abstract_url": "https://x/1"}],
                    }
                ],
            )
            self._write_digest(
                artifacts_dir / "run-1",
                "2026-04-08",
                generated_at="2026-04-08T08:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [
                            {"title": "Same rank", "abstract_url": "https://x/2"}
                        ],
                    }
                ],
            )

            config = AppConfig(
                timezone="Asia/Shanghai",
                lookback_hours=24,
                output_dir=output_dir,
                request_delay_seconds=0.0,
                feeds=[
                    FeedConfig(
                        name="LLM",
                        categories=["cs.AI"],
                        keywords=[" agent ", "Agent"],
                    ),
                    FeedConfig(
                        name="Vision",
                        categories=["cs.CV"],
                        keywords=["benchmark", " benchmark ", ""],
                    ),
                ],
                state=StateConfig(
                    enabled=True,
                    path=root / "state.json",
                    retention_days=90,
                ),
            )

            result = backfill_archive_history(config, artifacts_dir, dry_run=True)

        self.assertEqual(result.imported_dates, [])
        self.assertEqual(result.replaced_dates, [])
        self.assertEqual(result.skipped_dates, [])
        self.assertEqual(_tracked_keywords(config), ["agent", "benchmark"])

    def test_main_reports_preview_with_imported_replaced_and_skipped_dates(
        self,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            artifacts_dir = root / "artifacts"

            self._write_config(root / "config.toml")
            self._write_digest(
                output_dir,
                "2026-04-09",
                generated_at="2026-04-09T08:00:00+08:00",
                feeds=[{"name": "LLM", "papers": []}],
            )
            self._write_digest(
                artifacts_dir / "run-1",
                "2026-04-09",
                generated_at="2026-04-09T09:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [
                            {"title": "Replacement", "abstract_url": "https://x/1"}
                        ],
                    }
                ],
            )
            self._write_digest(
                artifacts_dir / "run-2",
                "2026-04-08",
                generated_at="2026-04-08T09:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [{"title": "Imported", "abstract_url": "https://x/2"}],
                    }
                ],
            )
            self._write_digest(
                artifacts_dir / "run-3",
                "2026-04-09",
                generated_at="2026-04-09T10:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM Delivery Check",
                        "papers": [{"title": "Skip", "abstract_url": "https://x/3"}],
                    }
                ],
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "--config",
                        str(root / "config.toml"),
                        "--artifacts-dir",
                        str(artifacts_dir),
                        "--dry-run",
                    ]
                )

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn(
            "Backfill preview: imported=1, replaced=1, skipped=1, scanned=3",
            output,
        )
        self.assertIn("Imported dates: 2026-04-08", output)
        self.assertIn("Replaced dates: 2026-04-09", output)
        self.assertIn("Skipped dates: 2026-04-09", output)

    def test_main_omits_date_lists_when_no_changes_exist(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            artifacts_dir = root / "artifacts"

            self._write_config(root / "config.toml")
            self._write_digest(
                output_dir,
                "2026-04-09",
                generated_at="2026-04-09T08:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [{"title": "Current", "abstract_url": "https://x/1"}],
                    }
                ],
            )
            self._write_digest(
                artifacts_dir / "run-1",
                "2026-04-09",
                generated_at="2026-04-09T08:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [{"title": "Same", "abstract_url": "https://x/2"}],
                    }
                ],
            )

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = main(
                    [
                        "--config",
                        str(root / "config.toml"),
                        "--artifacts-dir",
                        str(artifacts_dir),
                        "--dry-run",
                    ]
                )

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn(
            "Backfill preview: imported=0, replaced=0, skipped=0, scanned=1",
            output,
        )
        self.assertNotIn("Imported dates:", output)
        self.assertNotIn("Replaced dates:", output)
        self.assertNotIn("Skipped dates:", output)

    def test_load_snapshot_rejects_invalid_payloads(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            day_dir = root / "2026-04-08"
            day_dir.mkdir(parents=True, exist_ok=True)
            digest_json_path = day_dir / "digest.json"
            markdown_path = day_dir / "digest.md"

            cases = [
                (
                    "missing markdown",
                    {"generated_at": "2026-04-08T08:00:00+08:00"},
                    False,
                ),
                ("non-dict payload", [], True),
                ("invalid generated_at type", {"generated_at": 1, "feeds": []}, True),
                (
                    "invalid generated_at format",
                    {"generated_at": "not-a-date", "feeds": []},
                    True,
                ),
                (
                    "naive generated_at",
                    {"generated_at": "2026-04-08T08:00:00", "feeds": []},
                    True,
                ),
                (
                    "invalid feeds",
                    {"generated_at": "2026-04-08T08:00:00+08:00", "feeds": {}},
                    True,
                ),
            ]

            for label, payload, write_markdown in cases:
                with self.subTest(label=label):
                    if markdown_path.exists():
                        markdown_path.unlink()
                    if write_markdown:
                        markdown_path.write_text("# Digest\n", encoding="utf-8")
                    digest_json_path.write_text(
                        json.dumps(payload),
                        encoding="utf-8",
                    )
                    with self.assertRaises(ArchiveBackfillError):
                        _load_snapshot(digest_json_path)

            markdown_path.write_text("# Digest\n", encoding="utf-8")
            digest_json_path.write_text("{invalid", encoding="utf-8")
            with self.assertRaises(ArchiveBackfillError):
                _load_snapshot(digest_json_path)

    def test_load_snapshot_ignores_non_dict_feeds_and_non_list_papers(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            day_dir = root / "2026-04-08"
            day_dir.mkdir(parents=True, exist_ok=True)
            digest_json_path = day_dir / "digest.json"
            (day_dir / "digest.md").write_text("# Digest\n", encoding="utf-8")
            digest_json_path.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-04-08T08:00:00+08:00",
                        "feeds": [
                            1,
                            {"name": " ", "papers": []},
                            {"name": "LLM", "papers": "bad"},
                            {"name": "Vision", "papers": [{}, {}]},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            snapshot = _load_snapshot(digest_json_path)

        self.assertEqual(snapshot.feed_names, ("LLM", "Vision"))
        self.assertEqual(snapshot.total_papers, 2)

    def test_parse_filter_date_and_window_helpers(self) -> None:
        self.assertEqual(
            _parse_filter_date("2026-04-08", "--date-from"),
            date(2026, 4, 8),
        )
        self.assertIsNone(_parse_filter_date(" ", "--date-from"))
        with self.assertRaises(ArchiveBackfillError):
            _parse_filter_date("not-a-date", "--date-from")

        window = BackfillWindow(
            date_from=date(2026, 4, 8),
            date_to=date(2026, 4, 9),
        )
        self.assertFalse(window.includes(date(2026, 4, 7)))
        self.assertTrue(window.includes(date(2026, 4, 8)))
        self.assertTrue(window.includes(date(2026, 4, 9)))
        self.assertFalse(window.includes(date(2026, 4, 10)))

    def test_refresh_latest_files_handles_empty_and_non_empty_archives(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            _refresh_latest_files(root)
            self.assertFalse((root / "latest.json").exists())
            self.assertFalse((root / "latest.md").exists())

            self._write_digest(
                root,
                "2026-04-08",
                generated_at="2026-04-08T08:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [{"title": "Earlier", "abstract_url": "https://x/1"}],
                    }
                ],
            )
            self._write_digest(
                root,
                "2026-04-09",
                generated_at="2026-04-09T09:30:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [{"title": "Latest", "abstract_url": "https://x/2"}],
                    }
                ],
            )

            _refresh_latest_files(root)

            latest = json.loads((root / "latest.json").read_text(encoding="utf-8"))
            latest_markdown_exists = (root / "latest.md").exists()

        self.assertEqual(latest["generated_at"], "2026-04-09T09:30:00+08:00")
        self.assertTrue(latest_markdown_exists)

    def test_collect_snapshots_keeps_highest_rank_for_same_date(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_digest(
                root / "run-1",
                "2026-04-08",
                generated_at="2026-04-08T08:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [{"title": "One", "abstract_url": "https://x/1"}],
                    }
                ],
            )
            self._write_digest(
                root / "run-2",
                "2026-04-08",
                generated_at="2026-04-08T09:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [{"title": "One", "abstract_url": "https://x/1"}],
                    },
                    {
                        "name": "Vision",
                        "papers": [{"title": "Two", "abstract_url": "https://x/2"}],
                    },
                ],
            )

            snapshots = _collect_snapshots(root)

        self.assertEqual(snapshots["2026-04-08"].total_papers, 2)
        self.assertEqual(
            snapshots["2026-04-08"].feed_names,
            ("LLM", "Vision"),
        )

    def test_module_main_guard_raises_system_exit(self) -> None:
        with (
            patch("sys.argv", ["archive-backfill", "--help"]),
            patch("sys.stdout", io.StringIO()),
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("ignore", RuntimeWarning)
            with self.assertRaises(SystemExit) as raised:
                runpy.run_module("paper_digest.archive_backfill", run_name="__main__")

        self.assertEqual(raised.exception.code, 0)

    def _write_config(self, path: Path) -> None:
        path.write_text(
            "\n".join(
                [
                    "[app]",
                    'timezone = "Asia/Shanghai"',
                    'lookback_hours = 24',
                    'output_dir = "output"',
                    "",
                    "[state]",
                    "enabled = true",
                    'path = "state.json"',
                    "retention_days = 90",
                    "",
                    "[[feeds]]",
                    'name = "LLM"',
                    'categories = ["cs.AI"]',
                    'keywords = ["agent"]',
                ]
            ),
            encoding="utf-8",
        )

    def _write_digest(
        self,
        root: Path,
        date_str: str,
        *,
        generated_at: str,
        feeds: list[dict[str, object]],
    ) -> None:
        day_dir = root / date_str
        day_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": generated_at,
            "timezone": "Asia/Shanghai",
            "lookback_hours": 24,
            "feeds": [
                {
                    "name": feed["name"],
                    "papers": [
                        {
                            "title": paper["title"],
                            "summary": "",
                            "authors": [],
                            "categories": [],
                            "paper_id": paper["abstract_url"],
                            "abstract_url": paper["abstract_url"],
                            "pdf_url": None,
                            "published_at": generated_at,
                            "updated_at": generated_at,
                            "source": "arxiv",
                            "date_label": "Published",
                            "analysis": None,
                            "tags": [],
                            "topics": [],
                        }
                        for paper in feed["papers"]
                    ],
                }
                for feed in feeds
            ],
        }
        (day_dir / "digest.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )
        (day_dir / "digest.md").write_text("# Digest\n", encoding="utf-8")
