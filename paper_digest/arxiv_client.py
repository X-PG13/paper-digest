"""Minimal arXiv API client."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlencode
from urllib.request import Request

from .config import FeedConfig
from .network import fetch_bytes_with_retry

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivClientError(RuntimeError):
    """Raised when the arXiv client cannot fetch or parse results."""


@dataclass(slots=True)
class PaperAnalysis:
    conclusion: str
    contributions: list[str] = field(default_factory=list)
    audience: str = ""
    limitations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Paper:
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    paper_id: str
    abstract_url: str
    pdf_url: str | None
    published_at: datetime
    updated_at: datetime
    source: str = "arxiv"
    date_label: str = "Published"
    analysis: PaperAnalysis | None = None
    tags: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["published_at"] = self.published_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data


def build_search_query(categories: Iterable[str]) -> str:
    clauses = [f"cat:{category}" for category in categories]
    return "(" + " OR ".join(clauses) + ")"


def fetch_latest_papers(
    feed: FeedConfig,
    *,
    request_delay_seconds: float,
    request_timeout_seconds: int = 60,
    retry_attempts: int = 4,
    retry_backoff_seconds: float = 10.0,
) -> list[Paper]:
    params = {
        "search_query": build_search_query(feed.categories),
        "start": 0,
        "max_results": feed.max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API_URL}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "User-Agent": "paper-digest/0.1 (research-digest generator)",
            "Accept": "application/atom+xml",
        },
    )

    payload = fetch_bytes_with_retry(
        request,
        timeout_seconds=request_timeout_seconds,
        request_delay_seconds=request_delay_seconds,
        retry_attempts=retry_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
        error_factory=ArxivClientError,
        operation_description=f"failed to fetch papers for feed {feed.name!r}",
    )
    papers = parse_feed(payload)
    return papers


def parse_feed(payload: bytes) -> list[Paper]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ArxivClientError("received malformed XML from arXiv") from exc
    return [parse_entry(entry) for entry in root.findall("atom:entry", ATOM_NS)]


def parse_entry(entry: ET.Element) -> Paper:
    title = _clean_text(
        entry.findtext("atom:title", default="", namespaces=ATOM_NS) or ""
    )
    summary = _clean_text(
        entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or ""
    )
    paper_id = (entry.findtext("atom:id", default="", namespaces=ATOM_NS) or "").strip()
    published_at = _parse_atom_datetime(
        entry.findtext("atom:published", default="", namespaces=ATOM_NS) or ""
    )
    updated_at = _parse_atom_datetime(
        entry.findtext("atom:updated", default="", namespaces=ATOM_NS) or ""
    )

    authors = [
        _clean_text(author.findtext("atom:name", default="", namespaces=ATOM_NS) or "")
        for author in entry.findall("atom:author", ATOM_NS)
    ]
    categories = [
        category.attrib["term"]
        for category in entry.findall("atom:category", ATOM_NS)
        if "term" in category.attrib
    ]

    pdf_url: str | None = None
    abstract_url = paper_id
    for link in entry.findall("atom:link", ATOM_NS):
        href = link.attrib.get("href", "").strip()
        title_attr = link.attrib.get("title")
        if href and link.attrib.get("rel") == "alternate":
            abstract_url = href
        if href and title_attr == "pdf":
            pdf_url = href

    return Paper(
        title=title,
        summary=summary,
        authors=authors,
        categories=categories,
        paper_id=paper_id,
        abstract_url=abstract_url,
        pdf_url=pdf_url,
        published_at=published_at,
        updated_at=updated_at,
        source="arxiv",
        date_label="Published",
    )


def _parse_atom_datetime(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ArxivClientError(f"invalid datetime from arXiv: {value!r}") from exc


def _clean_text(value: str) -> str:
    return " ".join(value.split())
