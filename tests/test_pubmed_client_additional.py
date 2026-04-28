from __future__ import annotations

import json
import textwrap
import unittest
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from unittest.mock import patch

from paper_digest import pubmed_client
from paper_digest.config import FeedConfig
from paper_digest.pubmed_client import (
    PubMedClientError,
    _parse_pubmed_date,
    build_pubmed_search_term,
    fetch_latest_pubmed_papers,
    parse_pubmed_article,
    parse_pubmed_response,
    parse_pubmed_search_response,
)


class PubMedClientAdditionalTests(unittest.TestCase):
    def test_parse_pubmed_response_rejects_invalid_xml(self) -> None:
        with self.assertRaisesRegex(PubMedClientError, "malformed XML"):
            parse_pubmed_response(b"not xml")

    def test_parse_pubmed_search_response_validates_required_fields(self) -> None:
        cases = [
            ({}, "PubMed search response did not include esearchresult"),
            (
                {"esearchresult": {"idlist": {}}},
                "PubMed search response did not include a valid idlist",
            ),
        ]

        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(PubMedClientError, message):
                    parse_pubmed_search_response(json.dumps(payload).encode("utf-8"))

    @patch("paper_digest.pubmed_client._search_pubmed_ids", return_value=[])
    def test_fetch_latest_pubmed_papers_returns_empty_when_search_is_empty(
        self,
        mock_search_pubmed_ids,
    ) -> None:
        feed = FeedConfig(
            name="PubMed AI",
            source="pubmed",
            queries=["agent systems"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_pubmed_papers(
            feed,
            now=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            lookback_hours=24,
            request_delay_seconds=0.0,
        )

        self.assertEqual(papers, [])
        mock_search_pubmed_ids.assert_called_once()
        self.assertEqual(build_pubmed_search_term(feed), "(agent systems)")

    @patch(
        "paper_digest.pubmed_client.fetch_bytes_with_retry",
        return_value=json.dumps(
            {"esearchresult": {"idlist": ["12345"]}}
        ).encode("utf-8"),
    )
    def test_search_pubmed_ids_omits_optional_email_when_absent(
        self,
        mock_fetch_bytes_with_retry,
    ) -> None:
        feed = FeedConfig(
            name="PubMed AI",
            source="pubmed",
            queries=["agent systems"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        ids = pubmed_client._search_pubmed_ids(
            feed,
            now=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            lookback_hours=24,
            request_delay_seconds=0.0,
            request_timeout_seconds=60,
            retry_attempts=1,
            retry_backoff_seconds=1.0,
            contact_email=None,
        )

        self.assertEqual(ids, ["12345"])
        request = mock_fetch_bytes_with_retry.call_args.args[0]
        self.assertNotIn("email=", request.full_url)
        self.assertEqual(
            request.get_header("User-agent"),
            "paper-digest/0.1 (https://github.com/X-PG13/paper-digest)",
        )

    @patch(
        "paper_digest.pubmed_client.fetch_bytes_with_retry",
        return_value=textwrap.dedent(
            """
            <PubmedArticleSet>
              <PubmedArticle>
                <MedlineCitation>
                  <PMID>12345</PMID>
                  <Article>
                    <ArticleTitle>Example</ArticleTitle>
                  </Article>
                  <DateCreated>
                    <Year>2026</Year>
                  </DateCreated>
                </MedlineCitation>
              </PubmedArticle>
            </PubmedArticleSet>
            """
        ).encode("utf-8"),
    )
    @patch("paper_digest.pubmed_client._search_pubmed_ids", return_value=["12345"])
    def test_fetch_latest_pubmed_papers_omits_optional_email_when_absent(
        self,
        _mock_search_pubmed_ids,
        mock_fetch_bytes_with_retry,
    ) -> None:
        feed = FeedConfig(
            name="PubMed AI",
            source="pubmed",
            queries=["agent systems"],
            keywords=["agent"],
            exclude_keywords=[],
            max_results=10,
            max_items=5,
        )

        papers = fetch_latest_pubmed_papers(
            feed,
            now=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            lookback_hours=24,
            request_delay_seconds=0.0,
            contact_email=None,
        )

        self.assertEqual(len(papers), 1)
        request = mock_fetch_bytes_with_retry.call_args.args[0]
        self.assertNotIn("email=", request.full_url)

    def test_parse_pubmed_article_uses_fallback_date_defaults_and_doi(self) -> None:
        article = ET.fromstring(
            textwrap.dedent(
                """
                <PubmedArticle>
                  <MedlineCitation>
                    <PMID>12345</PMID>
                    <Article>
                      <Abstract>
                        <AbstractText>Unlabeled summary.</AbstractText>
                      </Abstract>
                      <AuthorList>
                        <Author>
                          <ForeName>Alice</ForeName>
                          <LastName>Smith</LastName>
                        </Author>
                        <Author>
                          <LastName>Solo</LastName>
                        </Author>
                      </AuthorList>
                      <PublicationTypeList>
                        <PublicationType>Journal Article</PublicationType>
                      </PublicationTypeList>
                    </Article>
                    <DateCreated>
                      <Year>2025</Year>
                      <Month>Winter</Month>
                    </DateCreated>
                  </MedlineCitation>
                  <PubmedData>
                    <ArticleIdList>
                      <ArticleId IdType="DOI">10.5555/pubmed</ArticleId>
                    </ArticleIdList>
                  </PubmedData>
                </PubmedArticle>
                """
            )
        )

        paper = parse_pubmed_article(article)

        self.assertEqual(paper.title, "PubMed 12345")
        self.assertEqual(paper.summary, "Unlabeled summary.")
        self.assertEqual(paper.authors, ["Alice Smith", "Solo"])
        self.assertEqual(paper.categories, ["Journal Article"])
        self.assertEqual(
            paper.published_at,
            datetime(2025, 12, 1, 0, 0, tzinfo=UTC),
        )
        self.assertEqual(paper.doi, "10.5555/pubmed")
        self.assertEqual(
            paper.source_urls["doi"],
            "https://doi.org/10.5555/pubmed",
        )

    def test_parse_pubmed_article_validates_required_metadata(self) -> None:
        missing_article = ET.fromstring(
            """
            <PubmedArticle>
              <MedlineCitation>
                <PMID>12345</PMID>
              </MedlineCitation>
            </PubmedArticle>
            """
        )
        missing_date = ET.fromstring(
            """
            <PubmedArticle>
              <MedlineCitation>
                <PMID>12345</PMID>
                <Article>
                  <ArticleTitle>Example</ArticleTitle>
                </Article>
              </MedlineCitation>
            </PubmedArticle>
            """
        )

        with self.assertRaisesRegex(PubMedClientError, "missing article metadata"):
            parse_pubmed_article(missing_article)
        with self.assertRaisesRegex(PubMedClientError, "missing date metadata"):
            parse_pubmed_article(missing_date)

    def test_pubmed_helpers_cover_blank_entries_and_history_fallbacks(self) -> None:
        article = ET.fromstring(
            """
            <PubmedArticle>
              <MedlineCitation>
                <PMID>12345</PMID>
                <DateCompleted>
                  <Year>2026</Year>
                </DateCompleted>
              </MedlineCitation>
              <PubmedData>
                <History>
                  <PubMedPubDate PubStatus="received">
                    <Year>2025</Year>
                  </PubMedPubDate>
                </History>
                <ArticleIdList>
                  <ArticleId IdType="pmc">PMC1</ArticleId>
                  <ArticleId IdType="doi">   </ArticleId>
                  <ArticleId IdType="doi">10.5555/example</ArticleId>
                </ArticleIdList>
              </PubmedData>
            </PubmedArticle>
            """
        )

        self.assertEqual(
            pubmed_client._extract_article_id(article, "doi"),
            "10.5555/example",
        )
        self.assertIsNone(pubmed_client._extract_article_id(article, "pii"))
        self.assertEqual(
            pubmed_client._extract_abstract(
                ET.fromstring(
                    """
                    <Abstract>
                      <AbstractText>   </AbstractText>
                      <AbstractText Label="RESULTS">Strong gains.</AbstractText>
                    </Abstract>
                    """
                )
            ),
            "RESULTS: Strong gains.",
        )
        self.assertEqual(
            pubmed_client._extract_authors(
                ET.fromstring(
                    """
                    <AuthorList>
                      <Author />
                      <Author>
                        <ForeName>Alice</ForeName>
                        <LastName>Smith</LastName>
                      </Author>
                    </AuthorList>
                    """
                )
            ),
            ["Alice Smith"],
        )
        self.assertEqual(
            pubmed_client._extract_publication_types(
                ET.fromstring(
                    """
                    <PublicationTypeList>
                      <PublicationType> </PublicationType>
                      <PublicationType>Journal Article</PublicationType>
                    </PublicationTypeList>
                    """
                )
            ),
            ["Journal Article"],
        )
        self.assertEqual(
            pubmed_client._extract_entry_datetime(article),
            datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        )
        with self.assertRaisesRegex(PubMedClientError, "missing PMID"):
            pubmed_client._required_text(None, "missing PMID")

    def test_parse_pubmed_date_validates_year_month_day_and_time(self) -> None:
        cases = [
            (
                "<PubMedPubDate><Year>bad</Year></PubMedPubDate>",
                "invalid PubMed year",
            ),
            (
                "<PubMedPubDate><Year>2026</Year><Month>bad</Month></PubMedPubDate>",
                "invalid PubMed month",
            ),
            (
                "<PubMedPubDate><Year>2026</Year><Day>bad</Day></PubMedPubDate>",
                "invalid PubMed day",
            ),
            (
                "<PubMedPubDate><Year>2026</Year><Hour>bad</Hour></PubMedPubDate>",
                "invalid PubMed hour",
            ),
            (
                "<PubMedPubDate><Year>2026</Year><Minute>bad</Minute></PubMedPubDate>",
                "invalid PubMed minute",
            ),
        ]

        for xml_text, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(PubMedClientError, message):
                    _parse_pubmed_date(ET.fromstring(xml_text))
