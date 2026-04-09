from __future__ import annotations

import json
import textwrap
import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from paper_digest.config import FeedConfig
from paper_digest.pubmed_client import (
    PubMedClientError,
    fetch_latest_pubmed_papers,
    parse_pubmed_response,
    parse_pubmed_search_response,
)


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def build_search_payload() -> bytes:
    return json.dumps(
        {
            "esearchresult": {
                "count": "2",
                "retmax": "2",
                "retstart": "0",
                "idlist": ["12345", "23456"],
            }
        }
    ).encode("utf-8")


def build_fetch_payload() -> bytes:
    return textwrap.dedent(
        """
        <?xml version="1.0"?>
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation>
              <PMID Version="1">12345</PMID>
                <Article>
                <ArticleTitle>PubMed Test Paper</ArticleTitle>
                <Abstract>
                  <AbstractText Label="BACKGROUND">
                    Agent systems in biomedicine.
                  </AbstractText>
                  <AbstractText Label="RESULTS">Strong benchmark gains.</AbstractText>
                </Abstract>
                <AuthorList>
                  <Author>
                    <LastName>Smith</LastName>
                    <ForeName>Alice</ForeName>
                  </Author>
                  <Author>
                    <CollectiveName>Genome Consortium</CollectiveName>
                  </Author>
                </AuthorList>
                <PublicationTypeList>
                  <PublicationType>Journal Article</PublicationType>
                  <PublicationType>Review</PublicationType>
                </PublicationTypeList>
              </Article>
            </MedlineCitation>
            <PubmedData>
              <History>
                <PubMedPubDate PubStatus="entrez">
                  <Year>2026</Year>
                  <Month>4</Month>
                  <Day>8</Day>
                  <Hour>9</Hour>
                  <Minute>15</Minute>
                </PubMedPubDate>
              </History>
            </PubmedData>
          </PubmedArticle>
        </PubmedArticleSet>
        """
    ).strip().encode("utf-8")


class PubMedClientTests(unittest.TestCase):
    def test_parse_pubmed_response_extracts_papers(self) -> None:
        papers = parse_pubmed_response(build_fetch_payload())

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "PubMed Test Paper")
        self.assertEqual(
            papers[0].summary,
            "BACKGROUND: Agent systems in biomedicine. "
            "RESULTS: Strong benchmark gains.",
        )
        self.assertEqual(papers[0].authors, ["Alice Smith", "Genome Consortium"])
        self.assertEqual(papers[0].categories, ["Journal Article", "Review"])
        self.assertEqual(papers[0].paper_id, "pubmed:12345")
        self.assertEqual(
            papers[0].abstract_url,
            "https://pubmed.ncbi.nlm.nih.gov/12345/",
        )
        self.assertEqual(
            papers[0].published_at,
            datetime(2026, 4, 8, 9, 15, tzinfo=UTC),
        )
        self.assertEqual(papers[0].date_label, "Entered")
        self.assertEqual(papers[0].source, "pubmed")

    def test_parse_pubmed_search_response_rejects_invalid_json(self) -> None:
        with self.assertRaises(PubMedClientError):
            parse_pubmed_search_response(b"not json")

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_latest_pubmed_papers_queries_api(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.side_effect = [
            DummyHTTPResponse(build_search_payload()),
            DummyHTTPResponse(build_fetch_payload()),
        ]
        feed = FeedConfig(
            name="PubMed AI",
            source="pubmed",
            queries=["agent systems", "clinical benchmark"],
            types=["Journal Article", "Review"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_pubmed_papers(
            feed,
            now=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            lookback_hours=48,
            request_delay_seconds=1.0,
            contact_email="bot@example.com",
        )

        self.assertEqual(len(papers), 1)
        search_request = mock_urlopen.call_args_list[0].args[0]
        search_query = parse_qs(urlsplit(search_request.full_url).query)
        self.assertEqual(search_query["db"], ["pubmed"])
        self.assertEqual(search_query["retmax"], ["10"])
        self.assertEqual(search_query["retmode"], ["json"])
        self.assertEqual(search_query["datetype"], ["edat"])
        self.assertEqual(search_query["mindate"], ["2026/04/07"])
        self.assertEqual(search_query["maxdate"], ["2026/04/09"])
        self.assertEqual(search_query["email"], ["bot@example.com"])
        self.assertIn(
            "(agent systems) OR (clinical benchmark)",
            search_query["term"][0],
        )
        self.assertIn('"Journal Article"[Publication Type]', search_query["term"][0])

        fetch_request = mock_urlopen.call_args_list[1].args[0]
        fetch_query = parse_qs(urlsplit(fetch_request.full_url).query)
        self.assertEqual(fetch_query["db"], ["pubmed"])
        self.assertEqual(fetch_query["id"], ["12345,23456"])
        self.assertEqual(fetch_query["retmode"], ["xml"])
        self.assertEqual(fetch_query["email"], ["bot@example.com"])
        self.assertEqual(mock_sleep.call_args_list[0].args, (1.0,))
        self.assertEqual(mock_sleep.call_args_list[1].args, (1.0,))
