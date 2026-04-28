from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from paper_digest.arxiv_client import Paper
from paper_digest.config import StateConfig
from paper_digest.state import (
    ActionNotificationRecord,
    DigestState,
    clear_action_notifications,
    dedupe_papers,
    diff_action_notifications,
    load_state,
    normalize_action_notifications,
    parse_action_notifications_payload,
    save_state,
)


def build_paper(
    paper_id: str,
    *,
    title: str = "Title",
) -> Paper:
    return Paper(
        title=title,
        summary="Summary",
        authors=["Alice"],
        categories=["cs.AI"],
        paper_id=paper_id,
        abstract_url=paper_id,
        pdf_url=None,
        published_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
    )


class StateAdditionalTests(unittest.TestCase):
    def test_load_state_and_save_state_cover_disabled_and_invalid_payloads(
        self,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            disabled_path = Path(temp_dir) / "disabled.json"
            save_state(
                StateConfig(
                    enabled=False,
                    path=disabled_path,
                    retention_days=90,
                ),
                DigestState(
                    seen_papers={"LLM": {"paper-1": "2026-04-08T09:00:00+00:00"}}
                ),
            )
            self.assertFalse(disabled_path.exists())

            invalid_path = Path(temp_dir) / "invalid.json"
            invalid_path.write_text(
                json.dumps(
                    {
                        "feeds": ["bad"],
                        "action_notifications": ["bad"],
                    }
                ),
                encoding="utf-8",
            )
            loaded_invalid = load_state(
                StateConfig(enabled=True, path=invalid_path, retention_days=90)
            )
            self.assertEqual(loaded_invalid.seen_papers, {})
            self.assertEqual(loaded_invalid.action_notifications, {})

            partial_path = Path(temp_dir) / "partial.json"
            partial_path.write_text(
                json.dumps(
                    {
                        "feeds": {
                            "LLM": {"paper-1": "2026-04-08T09:00:00+00:00"},
                            "Broken": ["bad"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            loaded_partial = load_state(
                StateConfig(enabled=True, path=partial_path, retention_days=90)
            )
            self.assertEqual(
                loaded_partial.seen_papers,
                {"LLM": {"paper-1": "2026-04-08T09:00:00+00:00"}},
            )

    def test_state_helpers_cover_normalization_pruning_and_validation_edges(
        self,
    ) -> None:
        self.assertEqual(normalize_action_notifications(["bad"]), {})
        self.assertEqual(
            normalize_action_notifications(
                {
                    1: {"due_soon": "2026-04-08T09:00:00+00:00"},
                    "bad-reasons": ["due_soon"],
                    "empty": {"due_soon": 1},
                    "ok": {"due_soon": "2026-04-08T09:00:00+00:00"},
                }
            ),
            {"ok": {"due_soon": "2026-04-08T09:00:00+00:00"}},
        )
        self.assertEqual(
            parse_action_notifications_payload(
                json.dumps({"ok": {"due_soon": "2026-04-08T09:00:00+00:00"}})
            ),
            {"ok": {"due_soon": "2026-04-08T09:00:00+00:00"}},
        )
        self.assertEqual(
            diff_action_notifications(
                {
                    "arxiv:2604.06170": {
                        "due_soon": "2026-04-08T09:00:00+00:00",
                    }
                },
                {
                    "arxiv:2604.06170": {
                        "due_soon": "2026-04-08T09:00:00+00:00",
                    }
                },
            ).updated,
            (),
        )

        state = DigestState(
            seen_papers={"LLM": {"title:stale paper": "2025-01-01T09:00:00+00:00"}}
        )
        papers = dedupe_papers(
            state,
            feed_name="LLM",
            papers=[build_paper("paper-1", title="Stale Paper")],
            now=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            retention_days=90,
        )
        self.assertEqual([paper.paper_id for paper in papers], ["paper-1"])
        self.assertEqual(
            state.seen_papers["LLM"],
            {"title:stale paper": "2026-04-08T09:00:00+00:00"},
        )

        with self.assertRaisesRegex(
            ValueError,
            "canonical_id, reason, or before_date must be provided",
        ):
            clear_action_notifications(DigestState(seen_papers={}))

    @patch(
        "paper_digest.state.list_action_notifications",
        return_value=[
            ActionNotificationRecord(
                canonical_id="missing",
                reason="due_soon",
                notified_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            )
        ],
    )
    def test_clear_action_notifications_tolerates_missing_record_targets(
        self,
        _mock_list_action_notifications,
    ) -> None:
        cleared = clear_action_notifications(
            DigestState(seen_papers={}, action_notifications={}),
            canonical_id="missing",
        )

        self.assertEqual(cleared, 1)
