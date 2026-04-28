from __future__ import annotations

import json
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest import feedback as feedback_module
from paper_digest.config import FeedbackConfig
from paper_digest.feedback import (
    FeedbackEntry,
    FeedbackState,
    advance_feedback_state,
    diff_feedback_states,
    load_feedback,
    load_feedback_file,
    normalize_feedback_canonical_id,
    render_feedback_diff,
    set_feedback_review_interval_days,
)


class FeedbackAdditionalTests(unittest.TestCase):
    def test_load_feedback_returns_empty_when_disabled_or_payload_invalid(self) -> None:
        disabled = load_feedback(
            FeedbackConfig(
                enabled=False,
                path=Path("feedback.json"),
            )
        )
        self.assertEqual(disabled.papers, {})

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "feedback.json"
            path.write_text(
                json.dumps(
                    {
                        "papers": {
                            "  ": "star",
                            "doi:10.5555/example": "reading",
                        }
                    }
                ),
                encoding="utf-8",
            )
            state = load_feedback_file(path)
            self.assertEqual(list(state.papers), ["doi:10.5555/example"])

            path.write_text(json.dumps({"papers": []}), encoding="utf-8")
            invalid = load_feedback_file(path)
            self.assertEqual(invalid.papers, {})

    def test_feedback_interval_validation_and_id_normalization_edges(self) -> None:
        state = FeedbackState(
            papers={
                "doi:10.5555/example": FeedbackEntry(status="reading"),
            }
        )

        with self.assertRaisesRegex(ValueError, "must be positive"):
            set_feedback_review_interval_days(
                state,
                canonical_id="doi:10.5555/example",
                review_interval_days=0,
            )

        with self.assertRaisesRegex(ValueError, "must not be empty"):
            normalize_feedback_canonical_id("   ")

        self.assertEqual(
            normalize_feedback_canonical_id("StandaloneId"),
            "StandaloneId",
        )

    def test_diff_and_render_cover_removed_and_no_change_cases(self) -> None:
        removed_diff = diff_feedback_states(
            FeedbackState(
                papers={
                    "doi:10.5555/example": FeedbackEntry(status="star"),
                }
            ),
            FeedbackState(papers={}),
        )

        self.assertEqual(removed_diff.removed_count, 1)
        self.assertIn("- doi:10.5555/example", render_feedback_diff(removed_diff))
        self.assertIn(
            "  status: star -> (none)",
            render_feedback_diff(removed_diff),
        )

        empty_diff = diff_feedback_states(
            FeedbackState(papers={}),
            FeedbackState(papers={}),
        )
        self.assertEqual(render_feedback_diff(empty_diff), ["No feedback changes."])

    def test_advance_feedback_state_clears_past_snoozes_without_resume_event(
        self,
    ) -> None:
        state = FeedbackState(
            papers={
                "doi:10.5555/example": FeedbackEntry(
                    status="reading",
                    updated_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
                    snoozed_until=date(2026, 4, 10),
                    review_interval_days=7,
                )
            }
        )

        automation = advance_feedback_state(state, today=date(2026, 4, 13))

        self.assertTrue(automation.changed)
        self.assertEqual(automation.resumed_from_snooze, frozenset())
        self.assertEqual(automation.recurring_due, frozenset({"doi:10.5555/example"}))
        self.assertIsNone(state.papers["doi:10.5555/example"].snoozed_until)

    def test_feedback_private_helpers_cover_invalid_inputs_and_fallbacks(self) -> None:
        self.assertIsNone(feedback_module._parse_feedback_entry("unknown"))
        self.assertIsNone(feedback_module._parse_feedback_entry(123))
        self.assertIsNone(feedback_module._feedback_status(1))
        self.assertIsNone(feedback_module._parse_optional_datetime("not-a-date"))
        self.assertIsNone(
            feedback_module._parse_optional_datetime("2026-04-08T12:00:00")
        )
        self.assertIsNone(feedback_module._parse_optional_date("bad-date"))
        self.assertIsNone(feedback_module._parse_optional_positive_int(0))
        self.assertEqual(
            feedback_module._serialize_feedback_entry(FeedbackEntry(status="star")),
            "star",
        )
        self.assertEqual(
            feedback_module._serialize_feedback_entry(
                FeedbackEntry(
                    status="reading",
                    note="keep reading",
                    due_date=date(2026, 4, 18),
                )
            ),
            {
                "status": "reading",
                "note": "keep reading",
                "due_date": "2026-04-18",
            },
        )
        self.assertEqual(
            feedback_module._coerce_feedback_path("feedback.json"),
            Path("feedback.json"),
        )
        self.assertIsNone(feedback_module._normalize_note(1))

    def test_preferred_entry_and_latest_datetime_helpers_cover_all_none_paths(
        self,
    ) -> None:
        local = FeedbackEntry(status="star")
        remote = FeedbackEntry(status="done")
        self.assertEqual(
            feedback_module._preferred_feedback_entries(
                local,
                remote,
                strategy="newer",
            ),
            (local, remote),
        )

        local_with_time = FeedbackEntry(
            status="star",
            updated_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        )
        self.assertEqual(
            feedback_module._preferred_feedback_entries(
                local_with_time,
                remote,
                strategy="newer",
            ),
            (local_with_time, remote),
        )

        remote_with_time = FeedbackEntry(
            status="done",
            updated_at=datetime(2026, 4, 9, 9, 0, tzinfo=UTC),
        )
        self.assertEqual(
            feedback_module._preferred_feedback_entries(
                local,
                remote_with_time,
                strategy="newer",
            ),
            (remote_with_time, local),
        )
        self.assertEqual(
            feedback_module._preferred_feedback_entries(
                local_with_time,
                FeedbackEntry(
                    status="reading",
                    updated_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
                ),
                strategy="newer",
            )[0],
            local_with_time,
        )
        self.assertEqual(
            feedback_module._latest_datetime(None, remote_with_time.updated_at),
            remote_with_time.updated_at,
        )
        self.assertEqual(
            feedback_module._latest_datetime(local_with_time.updated_at, None),
            local_with_time.updated_at,
        )
