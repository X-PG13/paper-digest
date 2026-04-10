"""Semantic Scholar client for fetching newly published papers."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request

from .arxiv_client import Paper
from .config import FeedConfig
from .network import fetch_bytes_with_retry

SEMANTIC_SCHOLAR_SEARCH_URL = (
    "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
)
SEMANTIC_SCHOLAR_FIELDS = ",".join(
    [
        "paperId",
        "title",
        "abstract",
        "url",
        "publicationDate",
        "authors",
        "publicationTypes",
        "fieldsOfStudy",
        "openAccessPdf",
        "externalIds",
    ]
)


class SemanticScholarClientError(RuntimeError):
    """Raised when Semantic Scholar fetches or parsing fail."""


def fetch_latest_semantic_scholar_papers(
    feed: FeedConfig,
    *,
    now: datetime,
    lookback_hours: int,
    request_delay_seconds: float,
    request_timeout_seconds: int = 60,
    retry_attempts: int = 4,
    retry_backoff_seconds: float = 10.0,
    contact_email: str | None = None,
) -> list[Paper]:
    """Fetch recent Semantic Scholar papers for a configured feed."""

    params = {
        "query": build_semantic_scholar_query(feed),
        "fields": SEMANTIC_SCHOLAR_FIELDS,
        "sort": "publicationDate:desc",
        "publicationDateOrYear": _date_window(now, lookback_hours),
        "limit": str(feed.max_results),
    }
    request = Request(
        f"{SEMANTIC_SCHOLAR_SEARCH_URL}?{urlencode(params)}",
        headers={
            "User-Agent": _build_user_agent(contact_email),
            "Accept": "application/json",
        },
    )
    payload = fetch_bytes_with_retry(
        request,
        timeout_seconds=request_timeout_seconds,
        request_delay_seconds=request_delay_seconds,
        retry_attempts=retry_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
        error_factory=SemanticScholarClientError,
        operation_description=(
            f"failed to fetch Semantic Scholar papers for feed {feed.name!r}"
        ),
    )
    papers = parse_semantic_scholar_response(payload)
    if not feed.types:
        return papers

    allowed_types = {paper_type.casefold() for paper_type in feed.types}
    return [
        paper
        for paper in papers
        if {category.casefold() for category in paper.categories} & allowed_types
    ]


def parse_semantic_scholar_response(payload: bytes) -> list[Paper]:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SemanticScholarClientError(
            "received malformed JSON from Semantic Scholar"
        ) from exc

    if not isinstance(raw, dict):
        raise SemanticScholarClientError(
            "Semantic Scholar response payload is invalid"
        )

    items = raw.get("data")
    if not isinstance(items, list):
        raise SemanticScholarClientError(
            "Semantic Scholar response did not include a valid data list"
        )

    papers: list[Paper] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paper = parse_semantic_scholar_item(item)
        if paper is not None:
            papers.append(paper)
    return papers


def parse_semantic_scholar_item(item: dict[str, object]) -> Paper | None:
    paper_id = _string(item.get("paperId"))
    publication_date = _string(item.get("publicationDate"))
    if paper_id is None or publication_date is None:
        return None

    published_at = _parse_publication_date(publication_date)
    abstract_url = _resolve_abstract_url(item)
    external_ids = item.get("externalIds")

    return Paper(
        title=_string(item.get("title")) or f"Semantic Scholar {paper_id}",
        summary=_string(item.get("abstract")) or "",
        authors=_extract_authors(item.get("authors")),
        categories=_extract_categories(item),
        paper_id=f"semantic_scholar:{paper_id}",
        abstract_url=abstract_url,
        pdf_url=_extract_pdf_url(item.get("openAccessPdf")),
        published_at=published_at,
        updated_at=published_at,
        source="semantic_scholar",
        date_label="Published",
        doi=_external_id(external_ids, "DOI"),
        arxiv_id=_external_id(external_ids, "ArXiv"),
    )


def build_semantic_scholar_query(feed: FeedConfig) -> str:
    if len(feed.queries) == 1:
        return feed.queries[0]
    return " OR ".join(f"({query})" for query in feed.queries)


def _date_window(now: datetime, lookback_hours: int) -> str:
    start_date = (now - timedelta(hours=lookback_hours)).date().isoformat()
    end_date = now.date().isoformat()
    return f"{start_date}:{end_date}"


def _parse_publication_date(value: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise SemanticScholarClientError(
        f"invalid Semantic Scholar publication date: {value!r}"
    )


def _resolve_abstract_url(item: dict[str, object]) -> str:
    external_ids = item.get("externalIds")
    if isinstance(external_ids, dict):
        arxiv_id = _string(external_ids.get("ArXiv"))
        if arxiv_id:
            return f"https://arxiv.org/abs/{arxiv_id}"
        doi = _string(external_ids.get("DOI"))
        if doi:
            return f"https://doi.org/{doi}"

    return _string(item.get("url")) or "https://www.semanticscholar.org"


def _external_id(value: object, key: str) -> str | None:
    if not isinstance(value, dict):
        return None
    return _string(value.get(key))


def _extract_pdf_url(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    return _string(value.get("url"))


def _extract_categories(item: dict[str, object]) -> list[str]:
    categories: list[str] = []
    seen: set[str] = set()
    for value in (
        *_string_list(item.get("fieldsOfStudy")),
        *_string_list(item.get("publicationTypes")),
    ):
        normalized = value.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        categories.append(value)
    return categories


def _extract_authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    authors: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _string(item.get("name"))
        if name:
            authors.append(name)
    return authors


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _string(item)
        if text:
            result.append(text)
    return result


def _string(value: object) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return None


def _build_user_agent(contact_email: str | None) -> str:
    base = "paper-digest/0.1 (https://github.com/X-PG13/paper-digest)"
    if contact_email:
        return f"{base}; mailto:{contact_email}"
    return base
