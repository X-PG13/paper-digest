from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.arxiv_client import Paper
from paper_digest.config import FeedbackConfig
from paper_digest.feedback import (
    FeedbackEntry,
    FeedbackState,
    apply_feedback_to_papers,
    load_feedback,
)


def build_paper(*, paper_id: str, title: str) -> Paper:
    published_at = datetime(2026, 4, 10, 8, 0, tzinfo=UTC)
    return Paper(
        title=title,
        summary="Agent systems summary.",
        authors=["Alice"],
        categories=["cs.AI"],
        paper_id=paper_id,
        abstract_url=paper_id.replace("http://", "https://"),
        pdf_url="https://arxiv.org/pdf/2604.00001v1",
        published_at=published_at,
        updated_at=published_at,
        base_relevance_score=40,
        relevance_score=40,
        match_reasons=['title matched "agent"'],
    )


class FeedbackTests(unittest.TestCase):
    def test_load_feedback_parses_string_and_object_entries(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "feedback.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "papers": {
                            "arxiv:2604.00001": "star",
                            "doi:10.5555/example": {
                                "status": "follow_up",
                                "updated_at": "2026-04-10T09:15:00+08:00",
                            },
                            "title:ignored-entry": {
                                "status": "unsupported",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            state = load_feedback(
                FeedbackConfig(
                    enabled=True,
                    path=path,
                )
            )

        self.assertEqual(state.papers["arxiv:2604.00001"].status, "star")
        self.assertEqual(state.papers["doi:10.5555/example"].status, "follow_up")
        self.assertEqual(
            state.papers["doi:10.5555/example"].updated_at,
            datetime.fromisoformat("2026-04-10T09:15:00+08:00"),
        )
        self.assertNotIn("title:ignored-entry", state.papers)

    def test_apply_feedback_to_papers_boosts_and_hides(self) -> None:
        starred = build_paper(
            paper_id="http://arxiv.org/abs/2604.00001v1",
            title="Agent planning",
        )
        ignored = build_paper(
            paper_id="http://arxiv.org/abs/2604.00002v1",
            title="Ignored agent",
        )
        untouched = build_paper(
            paper_id="http://arxiv.org/abs/2604.00003v1",
            title="Agent baseline",
        )
        feedback_state = FeedbackState(
            papers={
                "arxiv:2604.00001": FeedbackEntry(status="star"),
                "arxiv:2604.00002": FeedbackEntry(status="ignore"),
            }
        )

        adjusted = apply_feedback_to_papers(
            [starred, ignored, untouched],
            feedback_state=feedback_state,
            config=FeedbackConfig(
                enabled=True,
                path=Path("feedback.json"),
            ),
        )

        self.assertEqual(
            [paper.title for paper in adjusted],
            ["Agent planning", "Agent baseline"],
        )
        self.assertEqual(starred.feedback_status, "star")
        self.assertGreater(starred.base_relevance_score, untouched.base_relevance_score)
        self.assertIn("feedback: starred", starred.match_reasons)
        self.assertEqual(ignored.feedback_status, "ignore")

    def test_apply_feedback_can_keep_ignored_papers_visible(self) -> None:
        ignored = build_paper(
            paper_id="http://arxiv.org/abs/2604.00004v1",
            title="Ignored but visible",
        )
        adjusted = apply_feedback_to_papers(
            [ignored],
            feedback_state=FeedbackState(
                papers={
                    "arxiv:2604.00004": FeedbackEntry(status="ignore"),
                }
            ),
            config=FeedbackConfig(
                enabled=True,
                path=Path("feedback.json"),
                hide_ignored=False,
                ignore_penalty=25,
            ),
        )

        self.assertEqual(len(adjusted), 1)
        self.assertEqual(adjusted[0].feedback_status, "ignore")
        self.assertEqual(adjusted[0].base_relevance_score, 15)
        self.assertIn("feedback: ignored", adjusted[0].match_reasons)
