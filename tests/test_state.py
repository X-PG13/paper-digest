from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.arxiv_client import Paper
from paper_digest.config import StateConfig
from paper_digest.state import DigestState, dedupe_papers, load_state, save_state


def build_paper(paper_id: str) -> Paper:
    return Paper(
        title="Title",
        summary="Summary",
        authors=["Alice"],
        categories=["cs.AI"],
        paper_id=paper_id,
        abstract_url=paper_id,
        pdf_url=None,
        published_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
    )


class StateTests(unittest.TestCase):
    def test_dedupe_papers_filters_seen_and_duplicates_in_run(self) -> None:
        state = DigestState(
            seen_papers={"LLM": {"paper-1": "2026-04-07T00:00:00+00:00"}}
        )

        papers = dedupe_papers(
            state,
            feed_name="LLM",
            papers=[
                build_paper("paper-1"),
                build_paper("paper-2"),
                build_paper("paper-2"),
            ],
            now=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            retention_days=90,
        )

        self.assertEqual([paper.paper_id for paper in papers], ["paper-2"])

    def test_save_and_load_state_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config = StateConfig(
                enabled=True,
                path=Path(temp_dir) / "state.json",
                retention_days=90,
            )
            state = DigestState(
                seen_papers={"LLM": {"paper-1": "2026-04-08T09:00:00+00:00"}}
            )

            save_state(config, state)
            loaded = load_state(config)

        self.assertEqual(loaded.seen_papers, state.seen_papers)
