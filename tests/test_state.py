from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.arxiv_client import Paper
from paper_digest.config import StateConfig
from paper_digest.state import (
    DigestState,
    clear_action_notifications,
    dedupe_papers,
    list_action_notifications,
    load_state,
    save_state,
)


def build_paper(
    paper_id: str,
    *,
    title: str = "Title",
    doi: str | None = None,
    arxiv_id: str | None = None,
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
        doi=doi,
        arxiv_id=arxiv_id,
    )


class StateTests(unittest.TestCase):
    def test_dedupe_papers_filters_seen_and_duplicates_in_run(self) -> None:
        state = DigestState(
            seen_papers={"LLM": {"title:paper one": "2026-04-07T00:00:00+00:00"}}
        )

        papers = dedupe_papers(
            state,
            feed_name="LLM",
            papers=[
                build_paper("paper-1", title="Paper One"),
                build_paper("paper-2", title="Paper Two"),
                build_paper("paper-2", title="Paper Two"),
            ],
            now=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            retention_days=90,
        )

        self.assertEqual([paper.paper_id for paper in papers], ["paper-2"])

    def test_dedupe_papers_uses_canonical_identity(self) -> None:
        state = DigestState(seen_papers={})

        papers = dedupe_papers(
            state,
            feed_name="LLM",
            papers=[
                build_paper(
                    "https://doi.org/10.5555/example",
                    doi="10.5555/example",
                    title="Shared paper",
                ),
                build_paper(
                    "https://openalex.org/W123",
                    doi="10.5555/example",
                    title="Shared paper",
                ),
                build_paper(
                    "http://arxiv.org/abs/2604.00001v1",
                    arxiv_id="2604.00001",
                    title="Arxiv paper",
                ),
                build_paper(
                    "https://arxiv.org/abs/2604.00001",
                    arxiv_id="2604.00001",
                    title="Arxiv paper",
                ),
            ],
            now=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            retention_days=90,
        )

        self.assertEqual(
            [paper.paper_id for paper in papers],
            [
                "https://doi.org/10.5555/example",
                "http://arxiv.org/abs/2604.00001v1",
            ],
        )
        self.assertEqual(
            state.seen_papers["LLM"],
            {
                "doi:10.5555/example": "2026-04-08T09:00:00+00:00",
                "arxiv:2604.00001": "2026-04-08T09:00:00+00:00",
            },
        )

    def test_save_and_load_state_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = StateConfig(
                enabled=True,
                path=Path(temp_dir) / "state.json",
                retention_days=90,
            )
            state = DigestState(
                seen_papers={"LLM": {"paper-1": "2026-04-08T09:00:00+00:00"}},
                action_notifications={
                    "arxiv:2604.06170": {
                        "due_soon": "2026-04-09T09:30:00+00:00",
                    }
                },
            )

            save_state(config, state)
            loaded = load_state(config)

        self.assertEqual(loaded.seen_papers, state.seen_papers)
        self.assertEqual(
            loaded.action_notifications,
            state.action_notifications,
        )

    def test_load_state_supports_legacy_payload_without_action_notifications(
        self,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            config = StateConfig(
                enabled=True,
                path=Path(temp_dir) / "state.json",
                retention_days=90,
            )
            config.path.write_text(
                '{\n'
                '  "version": 1,\n'
                '  "feeds": {\n'
                '    "LLM": {\n'
                '      "paper-1": "2026-04-08T09:00:00+00:00"\n'
                "    }\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            loaded = load_state(config)

        self.assertEqual(
            loaded.seen_papers,
            {"LLM": {"paper-1": "2026-04-08T09:00:00+00:00"}},
        )
        self.assertEqual(loaded.action_notifications, {})

    def test_list_action_notifications_sorts_latest_first(self) -> None:
        state = DigestState(
            seen_papers={},
            action_notifications={
                "arxiv:2604.06170": {
                    "due_soon": "2026-04-09T09:00:00+00:00",
                    "overdue_3d": "2026-04-12T09:00:00+00:00",
                },
                "pubmed:41951858": {
                    "overdue_1d": "2026-04-11T09:00:00+00:00",
                },
            },
        )

        records = list_action_notifications(state)

        self.assertEqual(
            [(record.canonical_id, record.reason) for record in records],
            [
                ("arxiv:2604.06170", "overdue_3d"),
                ("pubmed:41951858", "overdue_1d"),
                ("arxiv:2604.06170", "due_soon"),
            ],
        )

    def test_clear_action_notifications_can_reset_by_reason(self) -> None:
        state = DigestState(
            seen_papers={},
            action_notifications={
                "arxiv:2604.06170": {
                    "due_soon": "2026-04-09T09:00:00+00:00",
                    "overdue_3d": "2026-04-12T09:00:00+00:00",
                },
                "pubmed:41951858": {
                    "overdue_3d": "2026-04-11T09:00:00+00:00",
                },
            },
        )

        cleared = clear_action_notifications(state, reason="overdue_3d")

        self.assertEqual(cleared, 2)
        self.assertEqual(
            state.action_notifications,
            {
                "arxiv:2604.06170": {
                    "due_soon": "2026-04-09T09:00:00+00:00",
                }
            },
        )
