from __future__ import annotations

import unittest
from pathlib import Path

from paper_digest.arxiv_client import ArxivClientError, parse_feed

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "arxiv_sample.xml"


class ParseFeedTests(unittest.TestCase):
    def test_parse_feed_extracts_papers(self) -> None:
        papers = parse_feed(FIXTURE_PATH.read_bytes())

        self.assertEqual(len(papers), 2)
        self.assertEqual(papers[0].title, "Agentic Evaluation for Vision Models")
        self.assertEqual(papers[0].authors, ["Alice Example", "Bob Example"])
        self.assertEqual(papers[0].categories, ["cs.AI", "cs.CV"])
        self.assertEqual(papers[0].abstract_url, "https://arxiv.org/abs/2604.00001v1")
        self.assertEqual(papers[0].pdf_url, "https://arxiv.org/pdf/2604.00001v1")

    def test_parse_feed_rejects_invalid_xml(self) -> None:
        with self.assertRaises(ArxivClientError):
            parse_feed(b"not xml")
