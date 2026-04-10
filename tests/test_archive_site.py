from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.archive_site import build_archive_site


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
            )

            index_html = (site_path / "index.html").read_text(encoding="utf-8")
            trends_html = (site_path / "trends.html").read_text(encoding="utf-8")
            momentum_html = (site_path / "momentum.html").read_text(encoding="utf-8")
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
            self.assertIn("首次出现", paper_detail)
            self.assertIn("最近出现", paper_detail)
            self.assertIn("覆盖跨度", paper_detail)
            self.assertIn("2 个活跃日期 / 2 个 feed / 2 次归档出现", paper_detail)
            self.assertIn("持续升温", paper_detail)
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
