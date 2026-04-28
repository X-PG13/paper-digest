from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import paper_digest.archive_site as archive_site


class ArchiveSiteAdditionalTests(unittest.TestCase):
    def test_build_archive_site_rebuilds_existing_site_without_archives(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            site_root = output_dir / "site"
            site_root.mkdir(parents=True, exist_ok=True)
            (site_root / "stale.txt").write_text("stale", encoding="utf-8")

            built = archive_site.build_archive_site(output_dir)

            index_html = (built / "index.html").read_text(encoding="utf-8")
            self.assertEqual(built, site_root)
            self.assertFalse((built / "stale.txt").exists())
            self.assertIn("No digest runs yet", index_html)
            self.assertTrue((built / "momentum.html").exists())
            self.assertTrue((built / "weekly-review.html").exists())
            self.assertTrue((built / "review-queue.html").exists())

    def test_load_day_archive_and_parse_feed_validate_invalid_payloads(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            digests_root = root / "site" / "digests"

            cases = [
                ("invalid-json", "{invalid", True, "invalid digest JSON"),
                ("non-dict", json.dumps([]), True, "invalid digest payload"),
                (
                    "bad-timezone",
                    json.dumps(
                        {
                            "generated_at": "2026-04-09T09:00:00+08:00",
                            "timezone": 1,
                            "feeds": [],
                        }
                    ),
                    True,
                    "invalid timezone",
                ),
                (
                    "missing-markdown",
                    json.dumps(
                        {
                            "generated_at": "2026-04-09T09:00:00+08:00",
                            "timezone": "Asia/Shanghai",
                            "feeds": [],
                        }
                    ),
                    False,
                    "missing digest markdown",
                ),
                (
                    "bad-feeds",
                    json.dumps(
                        {
                            "generated_at": "2026-04-09T09:00:00+08:00",
                            "timezone": "Asia/Shanghai",
                            "feeds": {},
                        }
                    ),
                    True,
                    "invalid feed list",
                ),
            ]

            for label, payload, write_markdown, expected in cases:
                with self.subTest(label=label):
                    day_dir = root / label / "2026-04-09"
                    day_dir.mkdir(parents=True, exist_ok=True)
                    if write_markdown:
                        (day_dir / "digest.md").write_text(
                            "# Digest\n", encoding="utf-8"
                        )
                    (day_dir / "digest.json").write_text(payload, encoding="utf-8")
                    with self.assertRaisesRegex(
                        archive_site.ArchiveSiteError, expected
                    ):
                        archive_site._load_day_archive(
                            day_dir / "digest.json", digests_root
                        )

        generated_at = datetime.fromisoformat("2026-04-09T09:00:00+08:00")
        digest_json_path = Path("2026-04-09/digest.json")
        for raw_feed, expected in [
            ([], "invalid feed payload"),
            ({}, "invalid feed name"),
            ({"name": "LLM", "papers": {}}, "invalid papers"),
        ]:
            with self.subTest(raw_feed=raw_feed):
                with self.assertRaisesRegex(archive_site.ArchiveSiteError, expected):
                    archive_site._parse_feed(raw_feed, digest_json_path, generated_at)

    def test_parse_papers_and_feed_summary_cover_skip_and_fallback_paths(self) -> None:
        generated_at = datetime.fromisoformat("2026-04-09T09:00:00+08:00")
        papers = archive_site._parse_papers(
            [
                1,
                {"title": 1, "abstract_url": "https://example.com/skip"},
                {"title": "Skip", "abstract_url": 2},
                {
                    "title": "  Useful Paper  ",
                    "abstract_url": "https://arxiv.org/abs/2604.12345v2",
                    "summary": "  Summary with spacing.  ",
                    "match_reasons": "not-a-list",
                    "authors": [" Alice ", "Alice", ""],
                    "categories": ["cs.AI", " cs.AI "],
                    "tags": ["Agents", "agents"],
                    "topics": ["LLM", " llm "],
                    "feedback_status": "Reading",
                    "feedback_note": "  note  ",
                    "feedback_next_action": "  next step  ",
                    "feedback_due_date": "2026-04-11",
                    "feedback_snoozed_until": "2026-04-12",
                    "feedback_review_interval_days": 3,
                },
            ],
            Path("digest.json"),
            generated_at,
        )

        self.assertEqual(len(papers), 1)
        paper = papers[0]
        self.assertEqual(paper.title, "Useful Paper")
        self.assertEqual(paper.reason_summary, "")
        self.assertEqual(paper.source, "unknown")
        self.assertEqual(paper.canonical_id, "arxiv:2604.12345")
        self.assertEqual(paper.authors, ["Alice"])
        self.assertEqual(paper.categories, ["cs.AI"])
        self.assertEqual(paper.tags, ["Agents"])
        self.assertEqual(paper.topics, ["LLM"])
        self.assertEqual(paper.feedback_status, "reading")
        self.assertEqual(paper.feedback_note, "note")
        self.assertEqual(paper.feedback_next_action, "next step")
        self.assertEqual(paper.feedback_due_date, date(2026, 4, 11))
        self.assertEqual(paper.feedback_snoozed_until, date(2026, 4, 12))
        self.assertEqual(paper.feedback_review_interval_days, 3)
        self.assertEqual(
            archive_site._build_feed_summary("LLM", 1, [], []),
            "收录 1 篇新论文。",
        )

    def test_review_helpers_cover_empty_and_secondary_sections(self) -> None:
        anchor = datetime.fromisoformat("2026-04-09T09:00:00+08:00")
        recurring = self._detail(
            canonical_id="paper:recurring",
            title="Recurring Reading",
            feedback_status="reading",
            feedback_updated_at=anchor - timedelta(days=7),
            feedback_review_interval_days=7,
            last_seen=anchor,
            active_days=3,
            active_feeds=2,
        )
        anchor_driver = self._detail(
            canonical_id="paper:done",
            title="Anchor Driver",
            feedback_status="done",
            feedback_updated_at=anchor,
            last_seen=anchor,
        )
        follow_up = self._detail(
            canonical_id="paper:follow-up",
            title="Follow Up Again",
            feedback_status="follow_up",
            feedback_updated_at=anchor,
            last_seen=anchor - timedelta(days=1),
            active_days=2,
        )
        starred = self._detail(
            canonical_id="paper:starred",
            title="Starred Backlog",
            feedback_status="star",
            feedback_updated_at=anchor,
            last_seen=anchor - timedelta(days=2),
        )
        unreviewed = self._detail(
            canonical_id="paper:new",
            title="Fresh Candidate",
            feedback_status=None,
            last_seen=anchor - timedelta(days=3),
            relevance_score=99,
        )

        self.assertIsNone(archive_site._review_anchor([]))
        self.assertEqual(archive_site._feedback_stage_priority("reading"), 2)
        self.assertTrue(
            archive_site._is_same_iso_week(anchor - timedelta(days=1), anchor)
        )
        self.assertFalse(
            archive_site._is_same_iso_week(anchor - timedelta(days=14), anchor)
        )
        self.assertEqual(archive_site._build_weekly_review_sections([]), [])
        self.assertEqual(archive_site._build_review_queue_sections([]), [])

        weekly_labels = [
            section.label
            for section in archive_site._build_weekly_review_sections(
                [recurring, anchor_driver]
            )
        ]
        queue_labels = [
            section.label
            for section in archive_site._build_review_queue_sections(
                [follow_up, starred, unreviewed]
            )
        ]
        queue_without_unreviewed = [
            section.label
            for section in archive_site._build_review_queue_sections(
                [follow_up, starred]
            )
        ]

        self.assertIn("周期复查又回来的", weekly_labels)
        self.assertIn("待跟进再次出现", queue_labels)
        self.assertIn("标星待处理", queue_labels)
        self.assertIn("新出现且未标记", queue_labels)
        self.assertNotIn("新出现且未标记", queue_without_unreviewed)

    def test_render_helpers_cover_optional_content_and_empty_states(self) -> None:
        anchor = datetime.fromisoformat("2026-04-09T09:00:00+08:00")
        detail = self._detail(
            canonical_id="paper:card",
            title="Render Card",
            feedback_status="star",
            feedback_updated_at=anchor,
            feedback_note="remember this",
            feedback_next_action="compare baselines",
            feedback_due_date=date(2026, 4, 11),
            feedback_snoozed_until=date(2026, 4, 12),
            feedback_review_interval_days=14,
        )
        html = archive_site._render_rising_paper_card(detail, link_prefix="../")
        self.assertIn("备注：remember this", html)
        self.assertIn("下一步：compare baselines", html)
        self.assertIn("最晚处理：2026-04-11", html)
        self.assertIn("搁置到：2026-04-12", html)
        self.assertIn("复查周期：每 14 天", html)

        entry_without_detail = archive_site.NotificationHistoryEntry(
            canonical_id="paper:missing",
            title="Missing Detail",
            detail_href=None,
            reason="due_soon",
            notified_at=anchor,
            feedback_status="follow_up",
            feedback_note="needs action",
            feedback_next_action="write notes",
            feedback_due_date=date(2026, 4, 10),
            feedback_snoozed_until=date(2026, 4, 12),
            feedback_review_interval_days=7,
            last_seen=None,
        )
        entry_with_detail = archive_site.NotificationHistoryEntry(
            canonical_id="paper:linked",
            title="Linked Detail",
            detail_href="papers/linked.html",
            reason="overdue_3d",
            notified_at=anchor,
            feedback_status=None,
            feedback_note=None,
            feedback_next_action=None,
            feedback_due_date=None,
            feedback_snoozed_until=None,
            feedback_review_interval_days=None,
            last_seen=anchor,
        )

        missing_detail_html = archive_site._render_notification_history_card(
            entry_without_detail,
            link_prefix="../",
        )
        linked_detail_html = archive_site._render_notification_history_card(
            entry_with_detail,
            link_prefix="../",
        )

        self.assertIn("当前归档里还没有对应的论文详情页。", missing_detail_html)
        self.assertIn("备注：needs action", missing_detail_html)
        self.assertIn("下一步：write notes", missing_detail_html)
        self.assertIn("最晚处理：2026-04-10", missing_detail_html)
        self.assertIn("搁置到：2026-04-12", missing_detail_html)
        self.assertIn("复查周期：每 7 天", missing_detail_html)
        self.assertIn("../papers/linked.html", linked_detail_html)
        self.assertIn("已逾期至少 3 天", linked_detail_html)

        self.assertIn(
            "暂无趋势",
            archive_site._render_trend_list([], empty_label="暂无趋势"),
        )
        self.assertIn(
            "2026-04-09",
            archive_site._render_keyword_match_group("2026-04-09", []),
        )
        self.assertIn(
            "这篇论文还没有历史命中记录。",
            archive_site._render_paper_appearances([]),
        )
        paper_without_links = archive_site.PaperArchive(
            canonical_id="paper:no-links",
            slug="paper-no-links",
            title="No Links",
            href="",
            detail_href="papers/paper-no-links.html",
            summary="",
            relevance_score=0,
            reason_summary="",
            source="unknown",
            source_variants=[],
            source_urls={},
            paper_id="",
            pdf_url=None,
            doi=None,
            arxiv_id=None,
            authors=[],
            categories=[],
            tags=[],
            topics=[],
            published_at=anchor,
            updated_at=anchor,
            feedback_status=None,
            feedback_note=None,
            feedback_next_action=None,
            feedback_due_date=None,
            feedback_snoozed_until=None,
            feedback_review_interval_days=None,
            search_text="",
        )
        self.assertIn(
            "当前没有可展示的来源链接。",
            archive_site._render_source_link_grid(paper_without_links),
        )

    def test_normalizers_and_identifier_helpers_cover_fallbacks(self) -> None:
        fallback = datetime.fromisoformat("2026-04-09T09:00:00+08:00")
        day = archive_site.DayArchive(
            date="2026-04-09",
            generated_at=fallback,
            timezone="Asia/Shanghai",
            total_papers=0,
            feeds=[],
            markdown_href="digests/2026-04-09/digest.md",
            json_href="digests/2026-04-09/digest.json",
            days_ago=0,
            search_text="",
        )

        self.assertEqual(archive_site._latest_label(None), "No digest runs yet")
        self.assertEqual(
            archive_site._latest_label(day),
            "2026-04-09 09:00:00 (Asia/Shanghai)",
        )
        with self.assertRaisesRegex(
            archive_site.ArchiveSiteError, "invalid generated_at"
        ):
            archive_site._parse_datetime(1, Path("digest.json"))
        with self.assertRaisesRegex(
            archive_site.ArchiveSiteError, "invalid generated_at"
        ):
            archive_site._parse_datetime("bad", Path("digest.json"))
        with self.assertRaisesRegex(
            archive_site.ArchiveSiteError, "naive generated_at"
        ):
            archive_site._parse_datetime(
                "2026-04-09T09:00:00",
                Path("digest.json"),
            )
        self.assertEqual(
            archive_site._parse_optional_datetime(
                1,
                fallback=fallback,
                digest_json_path=Path("digest.json"),
            ),
            fallback,
        )
        self.assertEqual(
            archive_site._parse_optional_datetime(
                "bad",
                fallback=fallback,
                digest_json_path=Path("digest.json"),
            ),
            fallback,
        )
        with self.assertRaisesRegex(
            archive_site.ArchiveSiteError, "naive paper datetime"
        ):
            archive_site._parse_optional_datetime(
                "2026-04-09T09:00:00",
                fallback=fallback,
                digest_json_path=Path("digest.json"),
            )
        self.assertEqual(
            archive_site._parse_optional_datetime(
                "2026-04-09T10:00:00+08:00",
                fallback=fallback,
                digest_json_path=Path("digest.json"),
            ),
            datetime.fromisoformat("2026-04-09T10:00:00+08:00"),
        )
        self.assertEqual(archive_site._optional_date(" 2026-04-11 "), date(2026, 4, 11))
        self.assertIsNone(archive_site._optional_date("bad-date"))
        self.assertEqual(archive_site._optional_feedback_status(" Reading "), "reading")
        self.assertIsNone(archive_site._optional_feedback_status("later"))
        self.assertEqual(
            archive_site._normalize_string_list([" Alice ", "alice", "", 1]),
            ["Alice"],
        )
        self.assertEqual(archive_site._normalize_string_list("bad"), [])

        pubmed_urls = archive_site._normalize_source_url_map(
            {" PubMed ": " https://example.com/custom ", "": "skip", 1: "bad"},
            source="pubmed",
            abstract_url="https://pubmed.example/paper",
            paper_id="pubmed:12345",
            doi="10.1000/test",
            arxiv_id="2604.12345",
        )
        openalex_urls = archive_site._normalize_source_url_map(
            "bad",
            source="openalex",
            abstract_url="",
            paper_id="openalex:W123",
            doi=None,
            arxiv_id=None,
        )

        self.assertEqual(pubmed_urls["pubmed"], "https://example.com/custom")
        self.assertEqual(pubmed_urls["doi"], "https://doi.org/10.1000/test")
        self.assertEqual(pubmed_urls["arxiv"], "https://arxiv.org/abs/2604.12345")
        self.assertEqual(openalex_urls["openalex"], "https://openalex.org/W123")

        derived_due_date = archive_site._effective_feedback_due_date(
            self._detail(
                canonical_id="paper:due",
                feedback_status="reading",
                feedback_updated_at=fallback,
                feedback_review_interval_days=5,
            )
        )
        self.assertEqual(derived_due_date, date(2026, 4, 14))
        self.assertIsNone(archive_site._optional_positive_int(True))
        self.assertIsNone(archive_site._optional_positive_int(0))
        self.assertEqual(archive_site._optional_positive_int(2), 2)

        self.assertEqual(
            archive_site._canonical_id_from_payload(
                " custom:id ",
                None,
                "https://example.com/paper",
                "Title",
            ),
            "custom:id",
        )
        self.assertEqual(
            archive_site._canonical_id_from_payload(
                None,
                "https://doi.org/10.1000/test",
                "https://example.com/paper",
                "Title",
            ),
            "doi:10.1000/test",
        )
        self.assertEqual(
            archive_site._canonical_id_from_payload(
                None,
                "pubmed:12345",
                "https://example.com/paper",
                "Title",
            ),
            "pubmed:12345",
        )
        self.assertEqual(
            archive_site._canonical_id_from_payload(
                None,
                None,
                "https://arxiv.org/abs/2604.12345v3",
                "Title",
            ),
            "arxiv:2604.12345",
        )
        self.assertEqual(
            archive_site._canonical_id_from_payload(
                None,
                None,
                "https://example.com/paper",
                "A Title With Punctuation!",
            ),
            "title:a title with punctuation",
        )
        self.assertEqual(
            archive_site._normalize_keywords([" Agent ", "agent", "", "Vision"]),
            ["Agent", "Vision"],
        )
        self.assertTrue(archive_site._slugify("中文标题").startswith("item-"))
        self.assertEqual(archive_site._truncate(" short text ", 20), "short text")
        self.assertEqual(archive_site._truncate("word word word", 5), "word…")

    def _detail(
        self,
        *,
        canonical_id: str = "paper:default",
        title: str = "Paper",
        feedback_status: str | None = None,
        feedback_updated_at: datetime | None = None,
        feedback_note: str | None = None,
        feedback_next_action: str | None = None,
        feedback_due_date: date | None = None,
        feedback_snoozed_until: date | None = None,
        feedback_review_interval_days: int | None = None,
        last_seen: datetime | None = None,
        active_days: int = 1,
        active_feeds: int = 1,
        appearance_count: int = 1,
        relevance_score: int = 60,
    ) -> archive_site.PaperDetail:
        last_seen = last_seen or datetime.fromisoformat("2026-04-09T09:00:00+08:00")
        paper = self._paper(
            canonical_id=canonical_id,
            title=title,
            relevance_score=relevance_score,
        )
        appearance = archive_site.PaperAppearance(
            date=last_seen.date().isoformat(),
            generated_at=last_seen,
            generated_label=archive_site._format_seen_label(last_seen),
            feed_name="LLM",
            feed_slug="llm",
            summary=paper.summary,
            relevance_score=paper.relevance_score,
            match_reasons=[],
            markdown_href="digests/2026-04-09/digest.md",
            json_href="digests/2026-04-09/digest.json",
        )
        return archive_site.PaperDetail(
            paper=paper,
            appearances=[appearance],
            first_seen=last_seen - timedelta(days=max(active_days - 1, 0)),
            last_seen=last_seen,
            active_days=active_days,
            active_feeds=active_feeds,
            appearance_count=appearance_count,
            feedback_status=feedback_status,
            feedback_updated_at=feedback_updated_at,
            feedback_note=feedback_note,
            feedback_next_action=feedback_next_action,
            feedback_due_date=feedback_due_date,
            feedback_snoozed_until=feedback_snoozed_until,
            feedback_review_interval_days=feedback_review_interval_days,
            action_notifications=[],
            related_papers=[],
        )

    def _paper(
        self,
        *,
        canonical_id: str,
        title: str,
        relevance_score: int,
    ) -> archive_site.PaperArchive:
        published_at = datetime.fromisoformat("2026-04-08T09:00:00+08:00")
        slug = archive_site._paper_slug(canonical_id)
        return archive_site.PaperArchive(
            canonical_id=canonical_id,
            slug=slug,
            title=title,
            href="https://example.com/paper",
            detail_href=f"papers/{slug}.html",
            summary="Useful summary",
            relevance_score=relevance_score,
            reason_summary="",
            source="arxiv",
            source_variants=["arxiv"],
            source_urls={"arxiv": "https://example.com/paper"},
            paper_id="paper-id",
            pdf_url=None,
            doi=None,
            arxiv_id="2604.12345",
            authors=["Alice"],
            categories=["cs.AI"],
            tags=["Agents"],
            topics=["LLM"],
            published_at=published_at,
            updated_at=published_at,
            feedback_status=None,
            feedback_note=None,
            feedback_next_action=None,
            feedback_due_date=None,
            feedback_snoozed_until=None,
            feedback_review_interval_days=None,
            search_text="useful summary llm agents",
        )
