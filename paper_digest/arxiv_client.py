"""Minimal arXiv API client."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from urllib.parse import urlencode
from urllib.request import Request

from .config import FeedbackStatus, FeedConfig
from .network import fetch_bytes_with_retry

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_NS = {"arxiv": "http://arxiv.org/schemas/atom"}
DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", re.IGNORECASE)
DOI_VALUE_RE = re.compile(r"(10\.\d{4,9}/\S+)", re.IGNORECASE)
ARXIV_ID_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/)?"
    r"(?P<identifier>(?:[a-z.-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?)"
    r"(?:\.pdf)?$",
    re.IGNORECASE,
)
TITLE_TOKEN_RE = re.compile(r"[^a-z0-9]+")


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
    doi: str | None = None
    arxiv_id: str | None = None
    source_variants: list[str] = field(default_factory=list)
    source_urls: dict[str, str] = field(default_factory=dict)
    base_relevance_score: int = 0
    relevance_score: int = 0
    match_reasons: list[str] = field(default_factory=list)
    feedback_status: FeedbackStatus | None = None
    feedback_note: str | None = None
    feedback_next_action: str | None = None
    feedback_due_date: date | None = None
    feedback_snoozed_until: date | None = None
    feedback_review_interval_days: int | None = None

    def __post_init__(self) -> None:
        self.doi = (
            _normalize_doi(self.doi)
            or _extract_doi(self.paper_id)
            or _extract_doi(self.abstract_url)
        )
        self.arxiv_id = (
            _normalize_arxiv_identifier(self.arxiv_id)
            or _extract_arxiv_identifier(self.paper_id)
            or _extract_arxiv_identifier(self.abstract_url)
            or _extract_arxiv_identifier(self.pdf_url)
        )
        self.authors = _merge_unique_strings(self.authors)
        self.categories = _merge_unique_strings(self.categories)
        self.tags = _merge_unique_strings(self.tags)
        self.topics = _merge_unique_strings(self.topics)
        self.source_variants = _merge_unique_strings(
            [*self.source_variants, self.source]
        )
        self.source_urls = _normalize_source_urls(
            self.source_urls,
            source=self.source,
            paper_id=self.paper_id,
            abstract_url=self.abstract_url,
            doi=self.doi,
            arxiv_id=self.arxiv_id,
        )
        if self.relevance_score < self.base_relevance_score:
            self.relevance_score = self.base_relevance_score
        self.match_reasons = _merge_unique_strings(self.match_reasons)
        self.feedback_note = _normalize_optional_note(self.feedback_note)
        self.feedback_next_action = _normalize_optional_note(self.feedback_next_action)
        self.feedback_due_date = _normalize_optional_date(self.feedback_due_date)
        self.feedback_snoozed_until = _normalize_optional_date(
            self.feedback_snoozed_until
        )
        self.feedback_review_interval_days = _normalize_optional_positive_int(
            self.feedback_review_interval_days
        )

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data.pop("base_relevance_score", None)
        data["published_at"] = self.published_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        data["feedback_due_date"] = (
            self.feedback_due_date.isoformat()
            if self.feedback_due_date is not None
            else None
        )
        data["feedback_snoozed_until"] = (
            self.feedback_snoozed_until.isoformat()
            if self.feedback_snoozed_until is not None
            else None
        )
        data["feedback_review_interval_days"] = self.feedback_review_interval_days
        data["canonical_id"] = self.canonical_id()
        return data

    def canonical_id(self) -> str:
        if self.doi:
            return f"doi:{self.doi}"
        if self.arxiv_id:
            return f"arxiv:{self.arxiv_id}"
        return f"title:{_normalize_title(self.title)}"

    def source_label(self) -> str:
        return " / ".join(self.source_variants)

    def match_reason_label(self, *, limit: int | None = None) -> str:
        reasons = self.match_reasons if limit is None else self.match_reasons[:limit]
        return "; ".join(reasons)

    def merge_duplicate(self, other: Paper) -> None:
        preferred = (
            self if _paper_merge_score(self) >= _paper_merge_score(other) else other
        )
        secondary = other if preferred is self else self

        self.title = preferred.title
        self.summary = preferred.summary
        self.paper_id = preferred.paper_id
        self.abstract_url = preferred.abstract_url
        self.pdf_url = preferred.pdf_url or secondary.pdf_url
        self.published_at = preferred.published_at
        self.updated_at = max(self.updated_at, other.updated_at)
        self.source = preferred.source
        self.date_label = preferred.date_label
        self.analysis = preferred.analysis or secondary.analysis
        self.doi = preferred.doi or secondary.doi
        self.arxiv_id = preferred.arxiv_id or secondary.arxiv_id
        self.authors = _merge_unique_strings([*preferred.authors, *secondary.authors])
        self.categories = _merge_unique_strings(
            [*preferred.categories, *secondary.categories]
        )
        self.tags = _merge_unique_strings([*preferred.tags, *secondary.tags])
        self.topics = _merge_unique_strings([*preferred.topics, *secondary.topics])
        self.source_variants = _merge_unique_strings(
            [*self.source_variants, *other.source_variants]
        )
        self.source_urls = _merge_source_urls(
            preferred.source_urls,
            secondary.source_urls,
        )
        self.base_relevance_score = max(
            self.base_relevance_score,
            other.base_relevance_score,
        )
        self.relevance_score = max(self.relevance_score, other.relevance_score)
        self.feedback_status = preferred.feedback_status or secondary.feedback_status
        self.feedback_note = preferred.feedback_note or secondary.feedback_note
        self.feedback_next_action = (
            preferred.feedback_next_action or secondary.feedback_next_action
        )
        self.feedback_due_date = (
            preferred.feedback_due_date or secondary.feedback_due_date
        )
        self.feedback_snoozed_until = (
            preferred.feedback_snoozed_until or secondary.feedback_snoozed_until
        )
        self.feedback_review_interval_days = (
            preferred.feedback_review_interval_days
            or secondary.feedback_review_interval_days
        )
        self.match_reasons = _merge_unique_strings(
            [*self.match_reasons, *other.match_reasons]
        )


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
    doi = _clean_text(
        entry.findtext("arxiv:doi", default="", namespaces=ARXIV_NS) or ""
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
        doi=doi or None,
        arxiv_id=_extract_arxiv_identifier(paper_id),
        source_urls={"arxiv": abstract_url},
    )


def _parse_atom_datetime(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ArxivClientError(f"invalid datetime from arXiv: {value!r}") from exc


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_doi(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = DOI_PREFIX_RE.sub("", value.strip()).strip()
    match = DOI_VALUE_RE.search(normalized)
    if match is None:
        return None
    return match.group(1).rstrip(".,;)").lower()


def _extract_doi(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_doi(value)


def _normalize_arxiv_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    match = ARXIV_ID_RE.search(value.strip())
    if match is None:
        return None
    identifier = match.group("identifier").lower()
    return re.sub(r"v\d+$", "", identifier)


def _extract_arxiv_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_arxiv_identifier(value)


def _normalize_title(value: str) -> str:
    normalized = TITLE_TOKEN_RE.sub(" ", value.casefold()).strip()
    return " ".join(normalized.split())


def _merge_unique_strings(values: Iterable[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
    return merged


def _normalize_optional_note(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_optional_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _normalize_optional_positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value <= 0:
        return None
    return value


def _normalize_source_urls(
    values: dict[str, str],
    *,
    source: str,
    paper_id: str,
    abstract_url: str,
    doi: str | None,
    arxiv_id: str | None,
) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in values.items():
        key_name = key.strip().lower()
        url = value.strip()
        if not key_name or not url:
            continue
        normalized[key_name] = url

    if source.strip() and abstract_url.strip():
        normalized.setdefault(source.strip().lower(), abstract_url.strip())
    if doi is not None:
        normalized.setdefault("doi", f"https://doi.org/{doi}")
    if arxiv_id is not None:
        normalized.setdefault("arxiv", f"https://arxiv.org/abs/{arxiv_id}")
    if source == "pubmed" and paper_id.startswith("pubmed:"):
        normalized.setdefault(
            "pubmed",
            f"https://pubmed.ncbi.nlm.nih.gov/{paper_id.removeprefix('pubmed:')}/",
        )
    if source == "openalex" and paper_id.startswith("openalex:"):
        normalized.setdefault(
            "openalex",
            f"https://openalex.org/{paper_id.removeprefix('openalex:')}",
        )
    return normalized


def _merge_source_urls(*mappings: dict[str, str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for mapping in mappings:
        for key, value in mapping.items():
            normalized_key = key.strip().lower()
            normalized_value = value.strip()
            if not normalized_key or not normalized_value:
                continue
            merged.setdefault(normalized_key, normalized_value)
    return merged


def _paper_merge_score(paper: Paper) -> tuple[int, int, int, int, int, int, int]:
    return (
        1 if paper.doi else 0,
        len(paper.summary),
        len(paper.authors),
        1 if paper.pdf_url else 0,
        len(paper.categories),
        1 if paper.arxiv_id else 0,
        1 if paper.date_label == "Published" else 0,
    )
