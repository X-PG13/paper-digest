from __future__ import annotations

import json
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from paper_digest.arxiv_client import Paper
from paper_digest.config import AppConfig, FeedConfig, StateConfig
from paper_digest.digest import ActionItem, DigestRun
from paper_digest.feedback import FeedbackAutomation, FeedbackEntry, FeedbackState
from paper_digest.service import (
    _action_priority,
    _action_reason_codes,
    _build_action_items,
    _CurrentFocusCandidate,
    _effective_due_date_from_entry,
    _entry_is_snoozed,
    _feedback_status,
    _focus_priority,
    _HistorySnapshot,
    _load_history_snapshots,
    _merge_snapshot_with_candidate,
    _optional_date,
    _optional_int,
    _optional_positive_int,
    _optional_string,
    _paper_from_payload,
    _parse_optional_datetime,
    _record_focus_candidates,
    _select_action_notification_items,
    _string_dict,
    _string_list,
    _topic_candidates_from_feeds,
    generate_digest,
)
from paper_digest.state import DigestState


def _paper(
    *,
    title: str = "Agent systems",
    paper_id: str = "http://arxiv.org/abs/2604.00001v1",
    abstract_url: str = "https://arxiv.org/abs/2604.00001v1",
    published_at: datetime | None = None,
    updated_at: datetime | None = None,
    feedback_status: str | None = None,
) -> Paper:
    published = published_at or datetime(2026, 4, 8, 1, 0, tzinfo=UTC)
    updated = updated_at or published
    return Paper(
        title=title,
        summary="Agent summary",
        authors=["Alice"],
        categories=["cs.AI"],
        paper_id=paper_id,
        abstract_url=abstract_url,
        pdf_url=None,
        published_at=published,
        updated_at=updated,
        feedback_status=feedback_status,
    )


class GenerateDigestAdditionalTests(unittest.TestCase):
    def test_generate_digest_uses_current_time_when_now_is_not_provided(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="Asia/Shanghai",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )

            digest = generate_digest(
                config,
                state=DigestState(seen_papers={}),
                feedback_state=FeedbackState(papers={}),
            )

        self.assertEqual(digest.timezone, "Asia/Shanghai")
        self.assertEqual(
            getattr(digest.generated_at.tzinfo, "key", None),
            "Asia/Shanghai",
        )

    def test_generate_digest_rejects_naive_now(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )

            with self.assertRaisesRegex(ValueError, "timezone-aware"):
                generate_digest(
                    config,
                    now=datetime(2026, 4, 8, 9, 30),
                    state=DigestState(seen_papers={}),
                    feedback_state=FeedbackState(papers={}),
                )

    @patch("paper_digest.service.fetch_feed_papers")
    def test_generate_digest_merges_duplicate_starred_focus_candidates_across_feeds(
        self,
        mock_fetch_feed_papers,
    ) -> None:
        now = datetime(2026, 4, 8, 9, 30, tzinfo=UTC)
        llm_feed = FeedConfig(
            name="LLM",
            categories=["cs.AI"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        vision_feed = FeedConfig(
            name="Vision",
            categories=["cs.CV"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )
        primary = _paper()
        duplicate = _paper()
        duplicate.summary = "Longer and more complete summary for the same paper."
        duplicate.authors = ["Alice", "Bob"]
        mock_fetch_feed_papers.side_effect = [[primary], [duplicate]]

        with TemporaryDirectory() as temp_dir:
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=Path(temp_dir) / "output",
                request_delay_seconds=0.0,
                feeds=[llm_feed, vision_feed],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )
            feedback_state = FeedbackState(
                papers={
                    primary.canonical_id(): FeedbackEntry(
                        status="star",
                        updated_at=now,
                    )
                }
            )

            digest = generate_digest(
                config,
                now=now,
                state=DigestState(seen_papers={}),
                feedback_state=feedback_state,
            )

        self.assertEqual(len(digest.focus_items), 1)
        self.assertEqual(
            digest.focus_items[0].feed_names,
            ["LLM", "Vision"],
        )
        self.assertEqual(
            digest.focus_items[0].summary,
            "Longer and more complete summary for the same paper.",
        )


class ServiceHelperTests(unittest.TestCase):
    def test_load_history_snapshots_aggregates_valid_entries_and_skips_invalid_data(
        self,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            (output_dir / "2026-04-08").mkdir()
            (output_dir / "2026-04-08" / "digest.json").write_text(
                "{not valid json",
                encoding="utf-8",
            )
            (output_dir / "2026-04-08-site").mkdir()
            (output_dir / "2026-04-09").mkdir()
            (output_dir / "2026-04-09" / "digest.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-04-09T09:30:00",
                        "feeds": [],
                    }
                ),
                encoding="utf-8",
            )
            (output_dir / "2026-04-10").mkdir()
            (output_dir / "2026-04-10" / "digest.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-04-10T09:30:00+00:00",
                        "feeds": [
                            "invalid-feed",
                            {
                                "name": "",
                                "papers": [
                                    "invalid-paper",
                                    {
                                        "title": "Missing dates",
                                        "abstract_url": "https://example.com",
                                    },
                                    _paper().to_dict(),
                                    _paper(
                                        title="Other paper",
                                        paper_id="http://arxiv.org/abs/2604.00002v1",
                                        abstract_url="https://arxiv.org/abs/2604.00002v1",
                                    ).to_dict(),
                                ],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (output_dir / "2026-04-11").mkdir()
            (output_dir / "2026-04-11" / "digest.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-04-11T09:30:00+00:00",
                        "feeds": [
                            {
                                "name": "LLM",
                                "papers": [_paper().to_dict()],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            snapshots = _load_history_snapshots(output_dir, {"arxiv:2604.00001"})

        snapshot = snapshots["arxiv:2604.00001"]
        self.assertEqual(snapshot.appearance_count, 2)
        self.assertEqual(snapshot.feed_names, {"LLM"})
        self.assertEqual(snapshot.active_days, {"2026-04-10", "2026-04-11"})
        self.assertEqual(snapshot.first_seen, datetime(2026, 4, 10, 9, 30, tzinfo=UTC))
        self.assertEqual(snapshot.last_seen, datetime(2026, 4, 11, 9, 30, tzinfo=UTC))

    def test_load_history_snapshots_updates_first_seen_and_skips_blank_duplicate_feeds(
        self,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            late_dir = output_dir / "2026-04-09"
            late_dir.mkdir()
            (late_dir / "digest.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-04-11T09:30:00+00:00",
                        "feeds": [
                            {
                                "name": "LLM",
                                "papers": [_paper().to_dict()],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            early_dir = output_dir / "2026-04-10"
            early_dir.mkdir()
            (early_dir / "digest.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-04-10T09:30:00+00:00",
                        "feeds": [
                            {
                                "name": "",
                                "papers": [_paper().to_dict()],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            snapshots = _load_history_snapshots(output_dir, {"arxiv:2604.00001"})

        snapshot = snapshots["arxiv:2604.00001"]
        self.assertEqual(snapshot.feed_names, {"LLM"})
        self.assertEqual(snapshot.appearance_count, 2)
        self.assertEqual(snapshot.active_days, {"2026-04-09", "2026-04-10"})
        self.assertEqual(snapshot.first_seen, datetime(2026, 4, 10, 9, 30, tzinfo=UTC))
        self.assertEqual(snapshot.last_seen, datetime(2026, 4, 11, 9, 30, tzinfo=UTC))

    def test_paper_from_payload_validates_required_fields_and_normalizes_optionals(
        self,
    ) -> None:
        self.assertIsNone(_paper_from_payload({"title": "Missing timestamps"}))
        self.assertIsNone(
            _paper_from_payload(
                {
                    "published_at": "2026-04-08T01:00:00+00:00",
                    "updated_at": "2026-04-08T01:00:00+00:00",
                    "title": " ",
                    "abstract_url": "https://example.com",
                }
            )
        )

        paper = _paper_from_payload(
            {
                "published_at": "2026-04-08T01:00:00+00:00",
                "updated_at": "2026-04-08T01:00:00+00:00",
                "title": "Agent systems",
                "abstract_url": "https://arxiv.org/abs/2604.00001v1",
                "source": " ",
                "date_label": " ",
                "pdf_url": " ",
                "source_urls": {"": "skip", "doi": "https://doi.org/10.1000/example"},
                "relevance_score": True,
                "feedback_status": "maybe",
                "feedback_due_date": "bad-date",
                "feedback_review_interval_days": 0,
            }
        )

        assert paper is not None
        self.assertEqual(paper.source, "arxiv")
        self.assertEqual(paper.date_label, "Published")
        self.assertIsNone(paper.pdf_url)
        self.assertEqual(
            paper.source_urls,
            {
                "arxiv": "https://arxiv.org/abs/2604.00001v1",
                "doi": "https://doi.org/10.1000/example",
            },
        )
        self.assertEqual(paper.relevance_score, 0)
        self.assertIsNone(paper.feedback_status)
        self.assertIsNone(paper.feedback_due_date)
        self.assertIsNone(paper.feedback_review_interval_days)

    def test_merge_snapshot_with_candidate_handles_current_only_and_existing_snapshot(
        self,
    ) -> None:
        current_paper = _paper()
        merged_from_current = _merge_snapshot_with_candidate(
            None,
            None,
            current_paper=current_paper,
            current_feed_names=set(),
            current_date="2026-04-08",
            current_seen_at=datetime(2026, 4, 8, 9, 30, tzinfo=UTC),
        )
        self.assertEqual(merged_from_current.appearance_count, 1)
        self.assertEqual(merged_from_current.active_days, {"2026-04-08"})

        snapshot = _HistorySnapshot(
            paper=_paper(updated_at=datetime(2026, 4, 7, 1, 0, tzinfo=UTC)),
            feed_names={"LLM"},
            first_seen=datetime(2026, 4, 10, 9, 30, tzinfo=UTC),
            last_seen=datetime(2026, 4, 10, 9, 30, tzinfo=UTC),
            active_days={"2026-04-10"},
            appearance_count=1,
        )
        candidate = _CurrentFocusCandidate(
            paper=_paper(
                title="Agent systems expanded",
                updated_at=datetime(2026, 4, 11, 1, 0, tzinfo=UTC),
            ),
            feed_names={"LLM", "PubMed AI"},
        )

        earlier = _merge_snapshot_with_candidate(
            snapshot,
            candidate,
            current_paper=None,
            current_feed_names=set(),
            current_date="2026-04-09",
            current_seen_at=datetime(2026, 4, 9, 9, 30, tzinfo=UTC),
        )
        self.assertEqual(earlier.first_seen, datetime(2026, 4, 9, 9, 30, tzinfo=UTC))
        self.assertEqual(earlier.last_seen, datetime(2026, 4, 10, 9, 30, tzinfo=UTC))

        later = _merge_snapshot_with_candidate(
            snapshot,
            None,
            current_paper=_paper(updated_at=datetime(2026, 4, 12, 1, 0, tzinfo=UTC)),
            current_feed_names={"LLM", "Crossref"},
            current_date="2026-04-12",
            current_seen_at=datetime(2026, 4, 12, 9, 30, tzinfo=UTC),
        )
        self.assertEqual(later.last_seen, datetime(2026, 4, 12, 9, 30, tzinfo=UTC))
        self.assertEqual(later.appearance_count, 3)

        cloned = _merge_snapshot_with_candidate(
            snapshot,
            None,
            current_paper=None,
            current_feed_names=set(),
            current_date="2026-04-10",
            current_seen_at=datetime(2026, 4, 10, 9, 30, tzinfo=UTC),
        )
        self.assertEqual(cloned.feed_names, {"LLM"})

        with self.assertRaisesRegex(ValueError, "must be provided"):
            _merge_snapshot_with_candidate(
                None,
                None,
                current_paper=None,
                current_feed_names=set(),
                current_date="2026-04-10",
                current_seen_at=datetime(2026, 4, 10, 9, 30, tzinfo=UTC),
            )

    def test_select_action_notification_items_respects_triggers_and_limits(
        self,
    ) -> None:
        state = DigestState(
            seen_papers={},
            action_notifications={
                "arxiv:stale": {"due_soon": "2026-04-08T09:30:00+00:00"},
                "arxiv:repeat": {"due_soon": "2026-04-08T09:30:00+00:00"},
            },
        )
        action_items = [
            ActionItem(
                canonical_id="arxiv:no-trigger",
                title="No trigger",
                abstract_url="https://example.com/no-trigger",
                summary="No transition reason",
                source_label="arxiv",
                feedback_status="reading",
                reasons=["next_action_pending"],
            ),
            ActionItem(
                canonical_id="arxiv:repeat",
                title="Repeat",
                abstract_url="https://example.com/repeat",
                summary="Already notified",
                source_label="arxiv",
                feedback_status="reading",
                reasons=["due_soon"],
            ),
            ActionItem(
                canonical_id="arxiv:new",
                title="New",
                abstract_url="https://example.com/new",
                summary="New transition",
                source_label="arxiv",
                feedback_status="reading",
                reasons=["overdue", "overdue_1d"],
            ),
            ActionItem(
                canonical_id="arxiv:capped",
                title="Capped",
                abstract_url="https://example.com/capped",
                summary="Would be selected without the cap",
                source_label="arxiv",
                feedback_status="reading",
                reasons=["overdue", "overdue_3d"],
            ),
        ]

        selected = _select_action_notification_items(
            action_items,
            state=state,
            now=datetime(2026, 4, 9, 9, 30, tzinfo=UTC),
            max_items=1,
        )

        self.assertEqual([item.canonical_id for item in selected], ["arxiv:new"])
        self.assertEqual(
            state.action_notifications,
            {
                "arxiv:repeat": {"due_soon": "2026-04-08T09:30:00+00:00"},
                "arxiv:new": {
                    "overdue": "2026-04-09T09:30:00+00:00",
                    "overdue_1d": "2026-04-09T09:30:00+00:00",
                },
            },
        )

    def test_misc_service_helpers_cover_normalization_and_reason_logic(self) -> None:
        aware = _parse_optional_datetime("2026-04-08T01:00:00+00:00")
        self.assertEqual(aware, datetime(2026, 4, 8, 1, 0, tzinfo=UTC))
        self.assertIsNone(_parse_optional_datetime("2026-04-08T01:00:00"))
        self.assertIsNone(_parse_optional_datetime("bad-value"))
        self.assertIsNone(_parse_optional_datetime(123))

        self.assertEqual(_string_list("bad"), [])
        self.assertEqual(_string_list([" Alice ", "", 7]), ["Alice", "7"])
        self.assertEqual(_string_dict("bad"), {})
        self.assertEqual(
            _string_dict({"": "skip", "doi": " 10.1000/example "}),
            {"doi": "10.1000/example"},
        )
        self.assertEqual(_optional_string(" value "), "value")
        self.assertIsNone(_optional_string(1))
        self.assertEqual(_optional_int(7), 7)
        self.assertIsNone(_optional_int(True))
        self.assertEqual(_optional_positive_int(3), 3)
        self.assertIsNone(_optional_positive_int(0))
        self.assertEqual(_optional_date("2026-04-18"), date(2026, 4, 18))
        self.assertIsNone(_optional_date("bad-date"))
        self.assertEqual(_feedback_status(" Reading "), "reading")
        self.assertIsNone(_feedback_status("invalid"))

        topics = _topic_candidates_from_feeds(
            [
                FeedConfig(
                    name="A",
                    keywords=["agent", " Agent ", ""],
                    exclude_keywords=[],
                ),
                FeedConfig(name="B", keywords=["benchmark"], exclude_keywords=[]),
            ]
        )
        self.assertEqual(topics, ["agent", "benchmark"])

        candidates: dict[str, _CurrentFocusCandidate] = {}
        canonical_id = _paper(feedback_status="star").canonical_id()
        _record_focus_candidates(
            candidates,
            papers=[_paper(feedback_status="star"), _paper(feedback_status="reading")],
            feed_name="LLM",
            seen_before_today=set(),
        )
        _record_focus_candidates(
            candidates,
            papers=[_paper(feedback_status="star")],
            feed_name="PubMed AI",
            seen_before_today={canonical_id},
        )
        self.assertEqual(candidates[canonical_id].feed_names, {"LLM", "PubMed AI"})
        self.assertTrue(candidates[canonical_id].seen_before_today)

        entry = FeedbackEntry(
            status="star",
            updated_at=datetime(2026, 4, 8, 9, 30, tzinfo=UTC),
            next_action="follow up",
            review_interval_days=7,
        )
        self.assertEqual(
            _action_reason_codes(
                entry,
                effective_due_date=date(2026, 4, 10),
                days_until_due=2,
                resumed_from_snooze=True,
                recurring_due=True,
            ),
            [
                "snooze_resumed",
                "due_soon",
                "recurring_review",
                "recurring_due",
                "next_action_pending",
            ],
        )

    def test_priority_and_due_helpers_cover_default_and_recurring_paths(self) -> None:
        self.assertEqual(_focus_priority(["other"]), 2)
        self.assertEqual(_action_priority(["overdue"]), 3)
        self.assertEqual(_action_priority(["recurring_review"]), 5)
        self.assertEqual(_action_priority(["other"]), 6)

        entry = FeedbackEntry(
            status="reading",
            updated_at=datetime(2026, 4, 8, 9, 30, tzinfo=UTC),
            review_interval_days=7,
        )
        self.assertEqual(_effective_due_date_from_entry(entry), date(2026, 4, 15))
        self.assertTrue(
            _entry_is_snoozed(
                FeedbackEntry(
                    status="star",
                    updated_at=datetime(2026, 4, 8, 9, 30, tzinfo=UTC),
                    snoozed_until=date(2026, 4, 16),
                ),
                today=date(2026, 4, 15),
            )
        )

    def test_build_action_items_skips_non_actionable_and_reasonless_entries(
        self,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            config = AppConfig(
                timezone="UTC",
                lookback_hours=24,
                output_dir=output_dir,
                request_delay_seconds=0.0,
                feeds=[],
                state=StateConfig(
                    enabled=True,
                    path=Path(temp_dir) / "state.json",
                    retention_days=90,
                ),
            )
            now = datetime(2026, 4, 15, 9, 30, tzinfo=UTC)
            current_paper = _paper()
            current_papers = {
                current_paper.canonical_id(): current_paper,
                "arxiv:future": _paper(
                    title="Future follow-up",
                    paper_id="http://arxiv.org/abs/2604.00002v1",
                    abstract_url="https://arxiv.org/abs/2604.00002v1",
                ),
            }
            feedback_state = FeedbackState(
                papers={
                    "arxiv:ignored": FeedbackEntry(
                        status="done",
                        updated_at=now,
                        next_action="skip",
                    ),
                    current_paper.canonical_id(): FeedbackEntry(
                        status="star",
                        updated_at=None,
                        review_interval_days=7,
                    ),
                    "arxiv:future": FeedbackEntry(
                        status="follow_up",
                        updated_at=now,
                        due_date=date(2026, 4, 25),
                    ),
                }
            )

            action_items = _build_action_items(
                DigestRun(
                    generated_at=now,
                    timezone="UTC",
                    lookback_hours=24,
                    feeds=[],
                ),
                config=config,
                feedback_state=feedback_state,
                feedback_automation=FeedbackAutomation(
                    resumed_from_snooze=frozenset(),
                    recurring_due=frozenset(),
                ),
                current_papers=current_papers,
                current_feed_names={
                    current_paper.canonical_id(): {"LLM"},
                    "arxiv:future": {"LLM"},
                },
                now=now,
            )

        self.assertEqual(action_items, [])
