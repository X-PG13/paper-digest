from __future__ import annotations

import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.archive_site import build_archive_site
from paper_digest.feedback import FeedbackEntry, FeedbackState


class ArchiveSiteTests(unittest.TestCase):
    def test_build_archive_site_renders_history_and_copies_digest_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            self._write_digest(
                output_dir,
                "2026-04-08",
                generated_at="2026-04-08T23:59:44+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "key_points": ["《Paper Circle》：适合做研究发现入口。"],
                        "papers": [
                            {
                                "title": "Paper Circle",
                                "abstract_url": "https://arxiv.org/abs/2604.06170v1",
                                "canonical_id": "doi:10.5555/paper-circle",
                                "summary": (
                                    "A canonical paper with merged source links."
                                ),
                                "authors": ["Alice", "Bob"],
                                "tags": ["方法"],
                                "topics": ["Agent"],
                                "source_variants": [
                                    "arxiv",
                                    "openalex",
                                    "semantic_scholar",
                                ],
                                "source_urls": {
                                    "arxiv": "https://arxiv.org/abs/2604.06170v1",
                                    "doi": "https://doi.org/10.5555/paper-circle",
                                    "openalex": "https://openalex.org/W123",
                                    "semantic_scholar": (
                                        "https://www.semanticscholar.org/paper/abc"
                                    ),
                                },
                                "doi": "10.5555/paper-circle",
                                "arxiv_id": "2604.06170",
                                "pdf_url": "https://arxiv.org/pdf/2604.06170v1",
                                "relevance_score": 91,
                                "match_reasons": [
                                    'title matched "agent"',
                                    "seen in 3 sources",
                                ],
                            }
                            ,
                            {
                                "title": "Fresh Agent Note",
                                "abstract_url": "https://arxiv.org/abs/2604.09999v1",
                                "canonical_id": "arxiv:2604.09999",
                                "summary": (
                                    "A recent unreviewed paper for the action queue."
                                ),
                                "authors": ["Cara"],
                                "tags": ["方法"],
                                "topics": ["Agent"],
                                "relevance_score": 88,
                                "match_reasons": ['title matched "agent"'],
                            },
                            {
                                "title": "Action Planner",
                                "abstract_url": "https://arxiv.org/abs/2604.08888v1",
                                "canonical_id": "arxiv:2604.08888",
                                "summary": (
                                    "A starred paper with a queued next action."
                                ),
                                "authors": ["Drew"],
                                "tags": ["方法"],
                                "topics": ["Agent"],
                                "relevance_score": 77,
                                "match_reasons": ['title matched "agent"'],
                            },
                            {
                                "title": "Deferred Agent",
                                "abstract_url": "https://arxiv.org/abs/2604.07777v1",
                                "canonical_id": "arxiv:2604.07777",
                                "summary": (
                                    "A snoozed paper that should stay out of "
                                    "the active queue."
                                ),
                                "authors": ["Evan"],
                                "tags": ["方法"],
                                "topics": ["Agent"],
                                "relevance_score": 70,
                                "match_reasons": ['title matched "agent"'],
                            },
                        ],
                    },
                    {
                        "name": "Vision",
                        "key_points": [],
                        "papers": [],
                    },
                ],
                template="zh_daily_brief",
            )
            self._write_digest(
                output_dir,
                "2026-04-07",
                generated_at="2026-04-07T23:58:10+08:00",
                feeds=[
                    {
                        "name": "LLM",
                        "key_points": [],
                        "papers": [
                            {
                                "title": "Agent Systems",
                                "abstract_url": "https://arxiv.org/abs/2604.00001v1",
                                "canonical_id": "arxiv:2604.00001",
                                "summary": "Another agent paper for the related list.",
                                "topics": ["Agent"],
                                "tags": ["评测"],
                            },
                            {
                                "title": "Benchmark Design",
                                "abstract_url": "https://arxiv.org/abs/2604.00002v1",
                                "canonical_id": "arxiv:2604.00002",
                                "summary": "A benchmark-oriented paper.",
                                "topics": ["Benchmark"],
                                "tags": ["评测"],
                            },
                        ],
                    },
                    {
                        "name": "Vision",
                        "key_points": [],
                        "papers": [
                            {
                                "title": "Paper Circle",
                                "abstract_url": "https://openalex.org/W123",
                                "canonical_id": "doi:10.5555/paper-circle",
                                "summary": (
                                    "A prior appearance used for momentum tracking."
                                ),
                                "topics": ["Agent"],
                                "tags": ["方法"],
                                "source_variants": ["openalex"],
                                "source_urls": {
                                    "openalex": "https://openalex.org/W123",
                                    "doi": "https://doi.org/10.5555/paper-circle",
                                },
                                "doi": "10.5555/paper-circle",
                            }
                        ],
                    }
                ],
                template="default",
            )
            (output_dir / "latest.md").write_text("# latest\n", encoding="utf-8")
            (output_dir / "latest.json").write_text("{}", encoding="utf-8")

            site_path = build_archive_site(
                output_dir,
                tracked_keywords=["agent", "benchmark", "diffusion"],
                feedback_state=FeedbackState(
                    papers={
                        "doi:10.5555/paper-circle": FeedbackEntry(
                            status="star",
                            updated_at=datetime.fromisoformat(
                                "2026-04-09T08:30:00+08:00"
                            ),
                            note="anchor paper for the review queue",
                            next_action="compare planner design",
                            due_date=datetime(2026, 4, 11).date(),
                            review_interval_days=14,
                        ),
                        "arxiv:2604.00001": FeedbackEntry(
                            status="reading",
                            updated_at=datetime.fromisoformat(
                                "2026-04-09T09:15:00+08:00"
                            ),
                            note="read sections 3 and 4 carefully",
                            due_date=datetime(2026, 4, 8).date(),
                        ),
                        "arxiv:2604.00002": FeedbackEntry(
                            status="done",
                            updated_at=datetime.fromisoformat(
                                "2026-04-09T10:00:00+08:00"
                            ),
                            note="already summarized in weekly notes",
                        ),
                        "arxiv:2604.08888": FeedbackEntry(
                            status="star",
                            updated_at=datetime.fromisoformat(
                                "2026-04-09T08:45:00+08:00"
                            ),
                            note="keep this in the action queue",
                            next_action="compare baseline table",
                        ),
                        "arxiv:2604.07777": FeedbackEntry(
                            status="follow_up",
                            updated_at=datetime.fromisoformat(
                                "2026-04-09T09:30:00+08:00"
                            ),
                            note="snooze until the workshop notes arrive",
                            snoozed_until=datetime(2026, 4, 12).date(),
                        ),
                    }
                ),
            )

            index_html = (site_path / "index.html").read_text(encoding="utf-8")
            trends_html = (site_path / "trends.html").read_text(encoding="utf-8")
            momentum_html = (site_path / "momentum.html").read_text(encoding="utf-8")
            weekly_review_html = (site_path / "weekly-review.html").read_text(
                encoding="utf-8"
            )
            reading_list_html = (site_path / "reading-list.html").read_text(
                encoding="utf-8"
            )
            review_queue_html = (site_path / "review-queue.html").read_text(
                encoding="utf-8"
            )
            llm_html = (site_path / "feeds/llm.html").read_text(encoding="utf-8")
            llm_xml = (site_path / "feeds/llm.xml").read_text(encoding="utf-8")
            agent_html = (site_path / "topics/agent.html").read_text(encoding="utf-8")
            agent_xml = (site_path / "topics/agent.xml").read_text(encoding="utf-8")
            paper_detail = next(
                path
                for path in (site_path / "papers").glob("*.html")
                if "<h1>Paper Circle</h1>" in path.read_text(encoding="utf-8")
            ).read_text(encoding="utf-8")
            self.assertIn("研究日报归档页", index_html)
            self.assertIn("订阅入口", index_html)
            self.assertIn("最近 7 天", index_html)
            self.assertIn("Paper Circle", index_html)
            self.assertIn("papers/", index_html)
            self.assertIn("momentum.html", index_html)
            self.assertIn("weekly-review.html", index_html)
            self.assertIn("reading-list.html", index_html)
            self.assertIn("review-queue.html", index_html)
            self.assertIn("digests/2026-04-08/digest.md", index_html)
            self.assertIn("2026-04-08 23:59:44 (Asia/Shanghai)", index_html)
            self.assertIn('data-feed-names="|llm|vision|"', index_html)
            self.assertIn("feeds/llm.html", index_html)
            self.assertIn("topics/agent.html", index_html)
            self.assertIn("趋势与订阅总览", trends_html)
            self.assertIn("持续升温论文", trends_html)
            self.assertIn("momentum.html", trends_html)
            self.assertIn("持续升温论文", momentum_html)
            self.assertIn("首次出现", momentum_html)
            self.assertIn("最近出现", momentum_html)
            self.assertIn("Paper Circle", momentum_html)
            self.assertIn("周度回顾", weekly_review_html)
            self.assertIn("还没处理完的", weekly_review_html)
            self.assertIn("已连续逾期的", weekly_review_html)
            self.assertIn("已完成", weekly_review_html)
            self.assertIn("Paper Circle", weekly_review_html)
            self.assertIn("Agent Systems", weekly_review_html)
            self.assertIn("Benchmark Design", weekly_review_html)
            self.assertIn("Action Planner", weekly_review_html)
            self.assertIn("已搁置", weekly_review_html)
            self.assertIn("Deferred Agent", weekly_review_html)
            self.assertIn("read sections 3 and 4 carefully", weekly_review_html)
            self.assertIn("Reading List", reading_list_html)
            self.assertIn("阅读清单", reading_list_html)
            self.assertIn("Paper Circle", reading_list_html)
            self.assertIn("Agent Systems", reading_list_html)
            self.assertIn("Action Planner", reading_list_html)
            self.assertIn("Deferred Agent", reading_list_html)
            self.assertIn("anchor paper for the review queue", reading_list_html)
            self.assertIn("compare planner design", reading_list_html)
            self.assertIn("复查周期：每 14 天", reading_list_html)
            self.assertIn("compare baseline table", reading_list_html)
            self.assertIn("papers/", reading_list_html)
            self.assertNotIn("Benchmark Design", reading_list_html)
            self.assertIn("Review Queue", review_queue_html)
            self.assertIn("行动队列", review_queue_html)
            self.assertIn("已过期", review_queue_html)
            self.assertIn("3 天内到期", review_queue_html)
            self.assertIn("已设下一步动作", review_queue_html)
            self.assertIn("新出现且未标记", review_queue_html)
            self.assertIn("Fresh Agent Note", review_queue_html)
            self.assertIn("Paper Circle", review_queue_html)
            self.assertIn("Action Planner", review_queue_html)
            self.assertNotIn("Deferred Agent", review_queue_html)
            self.assertIn("anchor paper for the review queue", review_queue_html)
            self.assertIn("compare planner design", review_queue_html)
            self.assertIn("复查周期：每 14 天", review_queue_html)
            self.assertIn("compare baseline table", review_queue_html)
            self.assertIn("2026-04-11", review_queue_html)
            self.assertIn("LLM 固定订阅页", llm_html)
            self.assertIn('type="application/rss+xml"', llm_html)
            self.assertIn("订阅 RSS", llm_html)
            self.assertIn("../trends.html", llm_html)
            self.assertIn("../papers/", llm_html)
            self.assertIn("Score 91", llm_html)
            self.assertIn('title matched &quot;agent&quot;', llm_html)
            self.assertIn("关键词追踪：agent", agent_html)
            self.assertIn('type="application/rss+xml"', agent_html)
            self.assertIn("../papers/", agent_html)
            self.assertIn("Agent Systems", agent_html)
            self.assertIn("<rss version=\"2.0\">", llm_xml)
            self.assertIn("<title>LLM Feed Archive</title>", llm_xml)
            self.assertIn("<link>../papers/", llm_xml)
            self.assertIn("<rss version=\"2.0\">", agent_xml)
            self.assertIn("<title>agent Topic Archive</title>", agent_xml)
            self.assertIn("<link>../papers/", agent_xml)
            self.assertIn("Canonical Paper", paper_detail)
            self.assertIn("合并来源", paper_detail)
            self.assertIn("OpenAlex", paper_detail)
            self.assertIn("历史命中", paper_detail)
            self.assertIn("相关推荐", paper_detail)
            self.assertIn("Agent Systems", paper_detail)
            self.assertIn("反馈状态", paper_detail)
            self.assertIn("标星", paper_detail)
            self.assertIn("下一步", paper_detail)
            self.assertIn("最晚处理", paper_detail)
            self.assertIn("compare planner design", paper_detail)
            self.assertIn("2026-04-11", paper_detail)
            self.assertIn("搁置到", paper_detail)
            self.assertIn("复查周期", paper_detail)
            self.assertIn("每 14 天", paper_detail)
            self.assertIn("复制 canonical_id", paper_detail)
            self.assertIn("复制标星命令", paper_detail)
            self.assertIn("复制阅读中命令", paper_detail)
            self.assertIn("复制已完成命令", paper_detail)
            self.assertIn("复制备注命令", paper_detail)
            self.assertIn("复制下一步命令", paper_detail)
            self.assertIn("复制到期命令", paper_detail)
            self.assertIn("复制搁置命令", paper_detail)
            self.assertIn("复制复查周期命令", paper_detail)
            self.assertIn("python -m paper_digest feedback set", paper_detail)
            self.assertIn("python -m paper_digest feedback note", paper_detail)
            self.assertIn("anchor paper for the review queue", paper_detail)
            self.assertIn("首次出现", paper_detail)
            self.assertIn("最近出现", paper_detail)
            self.assertIn("覆盖跨度", paper_detail)
            self.assertIn("2 个活跃日期 / 2 个 feed / 2 次归档出现", paper_detail)
            self.assertIn("持续升温", paper_detail)
            self.assertTrue((site_path / "weekly-review.html").exists())
            self.assertTrue((site_path / "reading-list.html").exists())
            self.assertTrue((site_path / "review-queue.html").exists())
            self.assertTrue((site_path / "latest.md").exists())
            self.assertTrue((site_path / "latest.json").exists())
            self.assertTrue((site_path / "digests/2026-04-08/digest.json").exists())
            self.assertTrue((site_path / "digests/2026-04-08/digest.md").exists())
            self.assertTrue((site_path / "trends.html").exists())
            self.assertTrue((site_path / "momentum.html").exists())
            self.assertTrue((site_path / "feeds/llm.html").exists())
            self.assertTrue((site_path / "feeds/llm.xml").exists())
            self.assertTrue(any((site_path / "papers").glob("*.html")))
            self.assertTrue((site_path / "topics/agent.html").exists())
            self.assertTrue((site_path / "topics/agent.xml").exists())

    def test_build_archive_site_uses_title_based_summary_without_key_points(
        self,
    ) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            self._write_digest(
                output_dir,
                "2026-04-08",
                generated_at="2026-04-08T10:00:00+00:00",
                feeds=[
                    {
                        "name": "LLM",
                        "key_points": [],
                        "papers": [
                            {
                                "title": "Agent Systems",
                                "abstract_url": "https://arxiv.org/abs/1",
                            },
                            {
                                "title": "Benchmark Design",
                                "abstract_url": "https://arxiv.org/abs/2",
                            },
                        ],
                    }
                ],
                template="default",
            )

            site_path = build_archive_site(output_dir, tracked_keywords=["agent"])

            index_html = (site_path / "index.html").read_text(encoding="utf-8")
            self.assertIn(
                "收录 2 篇，重点包括《Agent Systems》、《Benchmark Design》。",
                index_html,
            )

    def _write_digest(
        self,
        output_dir: Path,
        date_str: str,
        *,
        generated_at: str,
        feeds: list[dict[str, object]],
        template: str,
    ) -> None:
        day_dir = output_dir / date_str
        day_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": generated_at,
            "timezone": "Asia/Shanghai",
            "lookback_hours": 24,
            "highlights": [],
            "template": template,
            "feeds": [
                {
                    "name": feed["name"],
                    "key_points": feed["key_points"],
                    "papers": [
                        {
                            "title": paper["title"],
                            "summary": paper.get("summary", ""),
                            "authors": paper.get("authors", []),
                            "categories": paper.get("categories", []),
                            "paper_id": paper["abstract_url"],
                            "abstract_url": paper["abstract_url"],
                            "pdf_url": paper.get("pdf_url"),
                            "published_at": generated_at,
                            "updated_at": generated_at,
                            "source": "arxiv",
                            "source_variants": paper.get("source_variants", ["arxiv"]),
                            "source_urls": paper.get(
                                "source_urls",
                                {"arxiv": paper["abstract_url"]},
                            ),
                            "doi": paper.get("doi"),
                            "arxiv_id": paper.get("arxiv_id"),
                            "date_label": "Published",
                            "analysis": None,
                            "canonical_id": paper.get("canonical_id"),
                            "tags": paper.get("tags", []),
                            "topics": paper.get("topics", []),
                            "relevance_score": paper.get("relevance_score", 0),
                            "match_reasons": paper.get("match_reasons", []),
                            "feedback_status": paper.get("feedback_status"),
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
        (day_dir / "digest.md").write_text(
            f"# Digest {date_str}\n",
            encoding="utf-8",
        )
