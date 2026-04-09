from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.archive_backfill import BackfillWindow, backfill_archive_history, main
from paper_digest.config import AppConfig, FeedConfig, StateConfig


class ArchiveBackfillTests(unittest.TestCase):
    def test_backfill_imports_missing_dates_and_replaces_weaker_snapshot(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            artifacts_dir = root / "artifacts"

            self._write_digest(
                output_dir,
                "2026-04-09",
                generated_at="2026-04-09T11:00:00+08:00",
                feeds=[
                    {"name": "LLM", "papers": []},
                    {"name": "Vision", "papers": []},
                ],
            )
            self._write_digest(
                artifacts_dir / "run-1",
                "2026-04-09",
                generated_at="2026-04-09T09:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM Delivery Check",
                        "papers": [
                            {"title": "Should not import", "abstract_url": "https://x/1"}
                        ],
                    }
                ],
            )
            self._write_digest(
                artifacts_dir / "run-2",
                "2026-04-09",
                generated_at="2026-04-09T08:30:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [
                            {"title": "Agent systems", "abstract_url": "https://x/2"}
                        ],
                    },
                    {
                        "name": "Vision",
                        "papers": [
                            {"title": "Vision benchmark", "abstract_url": "https://x/3"}
                        ],
                    },
                ],
            )
            self._write_digest(
                artifacts_dir / "run-3",
                "2026-04-08",
                generated_at="2026-04-08T21:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [
                            {"title": "Paper Circle", "abstract_url": "https://x/4"}
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
                    FeedConfig(name="LLM", categories=["cs.AI"], keywords=["agent"]),
                    FeedConfig(
                        name="Vision",
                        categories=["cs.CV"],
                        keywords=["benchmark"],
                    ),
                ],
                state=StateConfig(
                    enabled=True,
                    path=root / "state.json",
                    retention_days=90,
                ),
            )

            result = backfill_archive_history(config, artifacts_dir)

            self.assertEqual(result.imported_dates, ["2026-04-08"])
            self.assertEqual(result.replaced_dates, ["2026-04-09"])
            self.assertEqual(result.skipped_dates, ["2026-04-09"])

            backfilled = json.loads(
                (output_dir / "2026-04-09/digest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [feed["name"] for feed in backfilled["feeds"]],
                ["LLM", "Vision"],
            )
            self.assertEqual(
                sum(len(feed["papers"]) for feed in backfilled["feeds"]),
                2,
            )

            latest = json.loads(
                (output_dir / "latest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(latest["generated_at"], "2026-04-09T08:30:00+08:00")
            self.assertTrue((output_dir / "site/index.html").exists())

    def test_backfill_respects_date_window(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            artifacts_dir = root / "artifacts"

            self._write_digest(
                artifacts_dir / "run-1",
                "2026-04-07",
                generated_at="2026-04-07T08:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [{"title": "Too old", "abstract_url": "https://x/7"}],
                    }
                ],
            )
            self._write_digest(
                artifacts_dir / "run-2",
                "2026-04-08",
                generated_at="2026-04-08T08:00:00+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "papers": [{"title": "Keep me", "abstract_url": "https://x/8"}],
                    }
                ],
            )
            self._write_digest(
                artifacts_dir / "run-3",
                "2026-04-09",
                generated_at="2026-04-09T08:00:00+08:00",
                feeds=[
                    {
                        "name": "Vision",
                        "papers": [
                            {"title": "Also keep me", "abstract_url": "https://x/9"}
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
                    FeedConfig(name="LLM", categories=["cs.AI"], keywords=["agent"]),
                    FeedConfig(
                        name="Vision",
                        categories=["cs.CV"],
                        keywords=["benchmark"],
                    ),
                ],
                state=StateConfig(
                    enabled=True,
                    path=root / "state.json",
                    retention_days=90,
                ),
            )

            result = backfill_archive_history(
                config,
                artifacts_dir,
                window=BackfillWindow(
                    date_from=date(2026, 4, 8),
                    date_to=date(2026, 4, 9),
                ),
            )

            self.assertEqual(result.imported_dates, ["2026-04-08", "2026-04-09"])
            self.assertEqual(result.replaced_dates, [])
            self.assertFalse((output_dir / "2026-04-07").exists())
            self.assertTrue((output_dir / "2026-04-08/digest.json").exists())
            self.assertTrue((output_dir / "2026-04-09/digest.json").exists())

    def test_main_rejects_invalid_date_window(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.toml"
            config_path.write_text(
                '\n'.join(
                    [
                        '[app]',
                        'timezone = "Asia/Shanghai"',
                        'lookback_hours = 24',
                        'output_dir = "output"',
                        '',
                        '[[feeds]]',
                        'name = "LLM"',
                        'categories = ["cs.AI"]',
                        'keywords = ["agent"]',
                    ]
                ),
                encoding="utf-8",
            )
            artifacts_dir = root / "artifacts"
            artifacts_dir.mkdir()

            exit_code = main(
                [
                    "--config",
                    str(config_path),
                    "--artifacts-dir",
                    str(artifacts_dir),
                    "--date-from",
                    "2026-04-10",
                    "--date-to",
                    "2026-04-09",
                ]
            )

            self.assertEqual(exit_code, 1)

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
            "highlights": [],
            "topic_sections": [],
            "template": "zh_daily_brief",
            "feeds": [
                {
                    "name": feed["name"],
                    "key_points": [],
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
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (day_dir / "digest.md").write_text("# Digest\n", encoding="utf-8")
