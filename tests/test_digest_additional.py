from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta

from paper_digest.arxiv_client import Paper, PaperAnalysis
from paper_digest.digest import (
    ActionItem,
    DigestRun,
    FeedDigest,
    FocusItem,
    TopicDigest,
    _action_due_label,
    _build_match_reasons,
    _build_sort_summary,
    _keyword_hits,
    _merge_unique_reasons,
    _paper_sort_key,
    _sort_mode_description,
    digest_has_papers,
    render_action_brief_markdown,
    render_feedback_brief_markdown,
    render_focus_brief_markdown,
    render_markdown,
)


def build_paper(
    *,
    title: str = "Agent paper",
    summary: str = "Agent summary",
    hours_ago: int = 1,
    authors: list[str] | None = None,
    paper_id: str = "http://arxiv.org/abs/2604.00001v1",
    abstract_url: str = "https://arxiv.org/abs/2604.00001v1",
    pdf_url: str | None = "https://arxiv.org/pdf/2604.00001v1",
    relevance_score: int = 0,
    source_variants: list[str] | None = None,
) -> Paper:
    now = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)
    published_at = now - timedelta(hours=hours_ago)
    return Paper(
        title=title,
        summary=summary,
        authors=authors or ["Alice"],
        categories=["cs.AI"],
        paper_id=paper_id,
        abstract_url=abstract_url,
        pdf_url=pdf_url,
        published_at=published_at,
        updated_at=published_at,
        relevance_score=relevance_score,
        source_variants=source_variants or [],
    )


class DigestAdditionalTests(unittest.TestCase):
    def test_to_dict_helpers_include_optional_metadata_and_mixed_sort_summary(
        self,
    ) -> None:
        generated_at = datetime(2026, 4, 8, 20, 0, tzinfo=UTC)
        focus_item = FocusItem(
            canonical_id="arxiv:2604.00001",
            title="Focus paper",
            abstract_url="https://example.com/focus",
            summary="Focus summary",
            source_label="arxiv",
            feedback_status="star",
            reasons=["new_starred"],
            first_seen=generated_at,
            last_seen=generated_at,
        )
        action_item = ActionItem(
            canonical_id="arxiv:2604.00002",
            title="Action paper",
            abstract_url="https://example.com/action",
            summary="Action summary",
            source_label="arxiv",
            feedback_status="reading",
            reasons=["due_soon"],
            due_date=date(2026, 4, 9),
            first_seen=generated_at,
            last_seen=generated_at,
        )
        digest = DigestRun(
            generated_at=generated_at,
            timezone="UTC",
            lookback_hours=24,
            feeds=[
                FeedDigest(name="LLM", papers=[], sort_by="relevance"),
                FeedDigest(name="Vision", papers=[], sort_by="published_at"),
            ],
            focus_items=[focus_item],
            action_items=[action_item],
            default_sort_by="hybrid",
        )
        digest.sort_summary = _build_sort_summary(digest)

        payload = digest.to_dict()

        self.assertEqual(
            payload["sorting"]["summary"],
            "mixed (LLM=relevance, Vision=published_at)",
        )
        self.assertEqual(
            payload["focus_items"][0]["first_seen"],
            generated_at.isoformat(),
        )
        self.assertEqual(
            payload["action_items"][0]["due_date"],
            "2026-04-09",
        )

    def test_focus_and_action_briefs_cover_empty_and_combined_paths(self) -> None:
        empty_default = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[],
        )
        self.assertIn(
            "No feedback-triggered papers for this run.",
            render_feedback_brief_markdown(empty_default),
        )
        self.assertIn(
            "No feedback-triggered papers for this run.",
            render_focus_brief_markdown(empty_default),
        )
        self.assertIn(
            "No action reminders for this run.",
            render_action_brief_markdown(empty_default),
        )

        empty_zh = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[],
            template="zh_daily_brief",
        )
        self.assertIn(
            "本次没有触发反馈驱动的关注论文。",
            render_feedback_brief_markdown(empty_zh),
        )
        self.assertIn(
            "本次没有触发反馈驱动的关注论文。",
            render_focus_brief_markdown(empty_zh),
        )
        self.assertIn(
            "本次没有触发行动提醒。",
            render_action_brief_markdown(empty_zh),
        )

        combined_zh = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[],
            template="zh_daily_brief",
            focus_items=[
                FocusItem(
                    canonical_id="arxiv:2604.00001",
                    title="Focus paper",
                    abstract_url="https://example.com/focus",
                    summary="Focus summary",
                    source_label="arxiv",
                    feedback_status="star",
                    reasons=["new_starred"],
                )
            ],
            action_items=[
                ActionItem(
                    canonical_id="arxiv:2604.00002",
                    title="Action paper",
                    abstract_url="https://example.com/action",
                    summary="Action summary",
                    source_label="arxiv",
                    feedback_status="reading",
                    reasons=["due_soon"],
                    due_date=date(2026, 4, 9),
                    days_until_due=1,
                )
            ],
        )
        markdown = render_feedback_brief_markdown(combined_zh)
        self.assertIn("## Focus 区块", markdown)
        self.assertIn("## 本周该处理什么", markdown)

    def test_render_action_brief_includes_english_optional_metadata(self) -> None:
        generated_at = datetime(2026, 4, 8, 20, 0, tzinfo=UTC)
        digest = DigestRun(
            generated_at=generated_at,
            timezone="UTC",
            lookback_hours=24,
            feeds=[],
            action_items=[
                ActionItem(
                    canonical_id="arxiv:2604.00002",
                    title="Action paper",
                    abstract_url="https://example.com/action",
                    summary="Action summary",
                    source_label="arxiv",
                    feedback_status="follow_up",
                    feedback_note="compare with previous baseline",
                    next_action="read section 4",
                    due_date=date(2026, 4, 7),
                    days_until_due=-1,
                    review_interval_days=7,
                    reasons=["overdue", "next_action_pending"],
                    feed_names=["LLM"],
                    relevance_score=88,
                    active_days=2,
                    active_feeds=1,
                    appearance_count=2,
                    first_seen=generated_at - timedelta(days=1),
                    last_seen=generated_at,
                )
            ],
        )

        markdown = render_action_brief_markdown(digest)

        self.assertIn("Due: 2026-04-07 (overdue by 1 day(s))", markdown)
        self.assertIn("Next Action: read section 4", markdown)
        self.assertIn("Review Cadence: every 7 day(s)", markdown)
        self.assertIn("Note: compare with previous baseline", markdown)
        self.assertIn("Feeds: LLM", markdown)
        self.assertIn("Seen Window:", markdown)
        self.assertIn("Relevance: 88", markdown)

    def test_keyword_reason_and_sort_helpers_cover_duplicate_and_fallback_paths(
        self,
    ) -> None:
        self.assertEqual(
            _keyword_hits(
                "Agent benchmark systems",
                [" agent ", "", "AGENT", "benchmark"],
            ),
            ["agent", "benchmark"],
        )

        paper = build_paper(
            summary="x" * 130,
            authors=["Alice"],
            pdf_url=None,
        )
        reasons = _build_match_reasons(
            paper,
            title_hits=["agent"],
            summary_hits=["benchmark"],
        )
        self.assertIn("has rich summary", reasons)
        self.assertIn("has complete metadata", reasons)

        self.assertEqual(
            _merge_unique_reasons([" has DOI ", "has doi", ""]),
            ["has DOI"],
        )
        self.assertEqual(
            _paper_sort_key(build_paper(relevance_score=10), sort_by="relevance"),
            (
                -10,
                -1,
                "agent paper",
            ),
        )
        self.assertEqual(
            _sort_mode_description("relevance"),
            "relevance (score-first ranking; recency only breaks exact ties)",
        )

    def test_action_due_label_and_digest_has_papers_cover_edge_cases(self) -> None:
        item_without_due_date = ActionItem(
            canonical_id="a",
            title="A",
            abstract_url="https://example.com/a",
            summary="A",
            source_label="arxiv",
            feedback_status="reading",
            reasons=["due_soon"],
        )
        self.assertEqual(_action_due_label(item_without_due_date, language="en"), "")

        item_without_days_until_due = ActionItem(
            canonical_id="b",
            title="B",
            abstract_url="https://example.com/b",
            summary="B",
            source_label="arxiv",
            feedback_status="reading",
            reasons=["due_soon"],
            due_date=date(2026, 4, 9),
        )
        self.assertEqual(
            _action_due_label(item_without_days_until_due, language="en"),
            "2026-04-09",
        )

        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[build_paper()])],
        )
        self.assertTrue(digest_has_papers(digest))

    def test_render_markdown_covers_english_optional_sections(self) -> None:
        generated_at = datetime(2026, 4, 8, 20, 0, tzinfo=UTC)
        digest = DigestRun(
            generated_at=generated_at,
            timezone="UTC",
            lookback_hours=24,
            feeds=[
                FeedDigest(
                    name="LLM",
                    papers=[
                        build_paper(
                            authors=[
                                "A1",
                                "A2",
                                "A3",
                                "A4",
                                "A5",
                                "A6",
                                "A7",
                            ],
                            relevance_score=91,
                        )
                    ],
                )
            ],
            focus_items=[
                FocusItem(
                    canonical_id="arxiv:2604.00001",
                    title="Focus paper",
                    abstract_url="https://example.com/focus",
                    summary="Focus summary",
                    source_label="arxiv / openalex",
                    feedback_status="star",
                    feedback_note="keep an eye on this",
                    reasons=["new_starred"],
                    feed_names=["LLM", "Vision"],
                    relevance_score=88,
                    active_days=2,
                    active_feeds=2,
                    appearance_count=3,
                    first_seen=generated_at - timedelta(days=1),
                    last_seen=generated_at,
                )
            ],
            action_items=[
                ActionItem(
                    canonical_id="arxiv:2604.00002",
                    title="Action paper",
                    abstract_url="https://example.com/action",
                    summary="Action summary",
                    source_label="arxiv",
                    feedback_status="follow_up",
                    feedback_note="needs comparison",
                    next_action="read appendix",
                    due_date=date(2026, 4, 7),
                    days_until_due=-1,
                    review_interval_days=14,
                    reasons=["overdue", "next_action_pending"],
                    feed_names=["LLM"],
                    relevance_score=77,
                    active_days=3,
                    active_feeds=1,
                    appearance_count=4,
                    first_seen=generated_at - timedelta(days=2),
                    last_seen=generated_at,
                )
            ],
        )
        digest.feeds[0].papers[0].feedback_status = "reading"
        digest.feeds[0].papers[0].feedback_note = "review later"
        digest.feeds[0].papers[0].match_reasons = ["title matched agent"]
        digest.feeds[0].papers[0].analysis = PaperAnalysis(
            conclusion="Solid baseline.",
            contributions=["Fast training", "Clear benchmark"],
            audience="evaluation researchers",
            limitations=["Small scale", "English only"],
        )

        markdown = render_markdown(digest)
        feedback_markdown = render_feedback_brief_markdown(digest)
        focus_markdown = render_focus_brief_markdown(digest)

        self.assertIn("## Focus", markdown)
        self.assertIn("## What To Review This Week", markdown)
        self.assertIn("## Focus", feedback_markdown)
        self.assertIn("## What To Review This Week", feedback_markdown)
        self.assertIn("## Focus", focus_markdown)
        self.assertIn("Feeds: LLM, Vision", markdown)
        self.assertIn("Seen Window:", markdown)
        self.assertIn("Authors: A1, A2, A3, A4, A5, A6, et al.", markdown)
        self.assertIn("Feedback: reading", markdown)
        self.assertIn("Note: review later", markdown)
        self.assertIn("Relevance: 91", markdown)
        self.assertIn("Match Reasons: title matched agent", markdown)
        self.assertIn("Contributions: Fast training; Clear benchmark", markdown)
        self.assertIn("Best For: evaluation researchers", markdown)
        self.assertIn("Limitations: Small scale; English only", markdown)

    def test_render_markdown_covers_minimal_analysis_and_unassigned_items(self) -> None:
        generated_at = datetime(2026, 4, 8, 20, 0, tzinfo=UTC)
        paper = build_paper(relevance_score=50)
        paper.analysis = PaperAnalysis(
            conclusion="Only conclusion.",
            contributions=[],
            audience="",
            limitations=[],
        )
        digest = DigestRun(
            generated_at=generated_at,
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[paper])],
            focus_items=[
                FocusItem(
                    canonical_id="arxiv:focus-minimal",
                    title="Minimal focus",
                    abstract_url="https://example.com/focus-minimal",
                    summary="focus summary",
                    source_label="arxiv",
                    feedback_status="star",
                    reasons=["new_starred"],
                )
            ],
            action_items=[
                ActionItem(
                    canonical_id="arxiv:action-minimal",
                    title="Minimal action",
                    abstract_url="https://example.com/action-minimal",
                    summary="action summary",
                    source_label="arxiv",
                    feedback_status="reading",
                    reasons=["recurring_review"],
                    review_interval_days=7,
                )
            ],
        )

        markdown = render_markdown(digest)
        action_markdown = render_action_brief_markdown(digest)

        self.assertIn("Conclusion: Only conclusion.", markdown)
        self.assertNotIn("Contributions:", markdown)
        self.assertNotIn("Best For:", markdown)
        self.assertNotIn("Limitations:", markdown)
        self.assertNotIn("Feeds:", markdown)
        self.assertNotIn("Due:", action_markdown)
        self.assertNotIn("Next Action:", action_markdown)

    def test_render_feedback_brief_markdown_zh_supports_action_only(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[],
            template="zh_daily_brief",
            action_items=[
                ActionItem(
                    canonical_id="arxiv:2604.00002",
                    title="Action paper",
                    abstract_url="https://example.com/action",
                    summary="Action summary",
                    source_label="arxiv",
                    feedback_status="reading",
                    reasons=["due_soon"],
                    due_date=date(2026, 4, 9),
                    days_until_due=1,
                )
            ],
        )

        markdown = render_feedback_brief_markdown(digest)

        self.assertIn("## 本周该处理什么", markdown)
        self.assertNotIn("## Focus 区块", markdown)

    def test_render_markdown_covers_zh_topic_and_optional_metadata(self) -> None:
        generated_at = datetime(2026, 4, 8, 20, 0, tzinfo=UTC)
        digest = DigestRun(
            generated_at=generated_at,
            timezone="UTC",
            lookback_hours=24,
            feeds=[
                FeedDigest(
                    name="LLM",
                    papers=[
                        build_paper(
                            authors=[
                                "甲",
                                "乙",
                                "丙",
                                "丁",
                                "戊",
                                "己",
                                "庚",
                            ],
                            relevance_score=95,
                        )
                    ],
                )
            ],
            focus_items=[
                FocusItem(
                    canonical_id="arxiv:2604.00003",
                    title="关注论文",
                    abstract_url="https://example.com/focus-zh",
                    summary="中文摘要",
                    source_label="arxiv",
                    feedback_status="star",
                    feedback_note="值得持续跟踪",
                    reasons=["new_starred"],
                    feed_names=["LLM", "Crossref"],
                    relevance_score=92,
                    active_days=4,
                    active_feeds=2,
                    appearance_count=5,
                    first_seen=generated_at - timedelta(days=3),
                    last_seen=generated_at,
                )
            ],
            action_items=[
                ActionItem(
                    canonical_id="arxiv:2604.00004",
                    title="行动论文",
                    abstract_url="https://example.com/action-zh",
                    summary="行动摘要",
                    source_label="arxiv",
                    feedback_status="reading",
                    feedback_note="安排时间看",
                    next_action="补读实验部分",
                    due_date=date(2026, 4, 9),
                    days_until_due=1,
                    review_interval_days=7,
                    reasons=["due_soon", "recurring_review"],
                    feed_names=["LLM"],
                    relevance_score=80,
                    active_days=2,
                    active_feeds=1,
                    appearance_count=2,
                    first_seen=generated_at - timedelta(days=1),
                    last_seen=generated_at,
                )
            ],
            topic_sections=[
                TopicDigest(
                    name="Agent",
                    paper_count=2,
                    feed_names=["LLM", "Crossref"],
                    paper_titles=["论文 A", "论文 B"],
                    key_points=["第一条", "第二条"],
                ),
                TopicDigest(
                    name="Empty Topic",
                    paper_count=1,
                    feed_names=["LLM"],
                )
            ],
            template="zh_daily_brief",
        )
        digest.feeds[0].papers[0].feedback_status = "star"
        digest.feeds[0].papers[0].feedback_note = "先看方法部分"
        digest.feeds[0].papers[0].match_reasons = ["标题命中 agent"]
        digest.feeds[0].papers[0].analysis = PaperAnalysis(
            conclusion="值得关注。",
            contributions=["提出新框架"],
            audience="做 benchmark 的人",
            limitations=["样本偏少"],
        )

        markdown = render_markdown(digest)
        feedback_markdown = render_feedback_brief_markdown(digest)
        focus_markdown = render_focus_brief_markdown(digest)

        self.assertIn("## Focus 区块", feedback_markdown)
        self.assertIn("## 本周该处理什么", feedback_markdown)
        self.assertIn("## Focus 区块", focus_markdown)
        self.assertIn("## 主题聚焦", markdown)
        self.assertIn("代表论文：《论文 A》", markdown)
        self.assertIn("主题速读：", markdown)
        self.assertIn("### Empty Topic", markdown)
        self.assertIn("作者：甲，乙，丙，丁，戊，己 等", markdown)
        self.assertIn("备注：先看方法部分", markdown)
        self.assertIn("相关性分数：95", markdown)
        self.assertIn("命中原因：标题命中 agent", markdown)
        self.assertIn("适合谁看：做 benchmark 的人", markdown)
        self.assertIn("潜在局限：样本偏少", markdown)
        self.assertIn("覆盖分组：LLM、Crossref", markdown)
        self.assertIn("历史窗口：", markdown)

    def test_render_markdown_covers_zh_analysis_without_audience(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[build_paper(relevance_score=10)])],
            template="zh_daily_brief",
        )
        digest.feeds[0].papers[0].analysis = PaperAnalysis(
            conclusion="中文结论。",
            contributions=["贡献一"],
            audience="",
            limitations=[],
        )

        markdown = render_markdown(digest)

        self.assertIn("一句话结论：中文结论。", markdown)
        self.assertIn("主要贡献：贡献一", markdown)
        self.assertNotIn("适合谁看：", markdown)
        self.assertNotIn("潜在局限：", markdown)
