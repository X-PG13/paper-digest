"""OpenAlex client for fetching newly published works."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlsplit
from urllib.request import Request

from .arxiv_client import Paper
from .config import FeedConfig
from .network import fetch_bytes_with_retry

OPENALEX_WORKS_URL = "https://api.openalex.org/works"


class OpenAlexClientError(RuntimeError):
    """Raised when OpenAlex fetches or parsing fail."""


def fetch_latest_openalex_papers(
    feed: FeedConfig,
    *,
    now: datetime,
    lookback_hours: int,
    request_delay_seconds: float,
    request_timeout_seconds: int = 60,
    retry_attempts: int = 4,
    retry_backoff_seconds: float = 10.0,
    contact_email: str | None = None,
    api_key: str | None = None,
) -> list[Paper]:
    """Fetch recent OpenAlex works for a configured feed."""

    from_publication_date = (now - timedelta(hours=lookback_hours)).date().isoformat()
    filters = [
        f"from_publication_date:{from_publication_date}",
        f"to_publication_date:{now.date().isoformat()}",
    ]
    if feed.types:
        filters.append(f"type:{'|'.join(feed.types)}")

    params = {
        "search": build_openalex_search_query(feed),
        "filter": ",".join(filters),
        "sort": "publication_date:desc",
        "per-page": str(feed.max_results),
    }
    if contact_email:
        params["mailto"] = contact_email
    if api_key:
        params["api_key"] = api_key

    request = Request(
        f"{OPENALEX_WORKS_URL}?{urlencode(params)}",
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
        error_factory=OpenAlexClientError,
        operation_description=f"failed to fetch OpenAlex works for feed {feed.name!r}",
    )
    return parse_openalex_response(payload)


def parse_openalex_response(payload: bytes) -> list[Paper]:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise OpenAlexClientError("received malformed JSON from OpenAlex") from exc

    if not isinstance(raw, dict):
        raise OpenAlexClientError("OpenAlex response payload is invalid")

    results = raw.get("results")
    if not isinstance(results, list):
        raise OpenAlexClientError(
            "OpenAlex response did not include a valid results list"
        )

    papers: list[Paper] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        paper = parse_openalex_work(item)
        if paper is not None:
            papers.append(paper)
    return papers


def parse_openalex_work(item: dict[str, object]) -> Paper | None:
    work_id = _string(item.get("id"))
    publication_date = _string(item.get("publication_date"))
    if work_id is None or publication_date is None:
        return None

    published_at = _parse_publication_date(publication_date)
    short_id = _openalex_short_id(work_id)
    title = _string(item.get("display_name")) or _string(item.get("title")) or short_id

    return Paper(
        title=title,
        summary=_reconstruct_abstract(item.get("abstract_inverted_index")),
        authors=_extract_authors(item.get("authorships")),
        categories=_extract_categories(item),
        paper_id=f"openalex:{short_id}",
        abstract_url=_resolve_abstract_url(item),
        pdf_url=_resolve_pdf_url(item),
        published_at=published_at,
        updated_at=published_at,
        source="openalex",
        date_label="Published",
        doi=_string(item.get("doi")),
    )


def build_openalex_search_query(feed: FeedConfig) -> str:
    if len(feed.queries) == 1:
        return feed.queries[0]
    return " OR ".join(f'"{query}"' for query in feed.queries)


def _parse_publication_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise OpenAlexClientError(
            f"invalid OpenAlex publication date: {value!r}"
        ) from exc


def _reconstruct_abstract(value: object) -> str:
    if not isinstance(value, dict):
        return ""

    positions_to_token: dict[int, str] = {}
    for token, positions in value.items():
        if not isinstance(token, str) or not isinstance(positions, list):
            continue
        normalized_token = token.strip()
        if not normalized_token:
            continue
        for position in positions:
            if not isinstance(position, int) or position < 0:
                continue
            positions_to_token.setdefault(position, normalized_token)

    if not positions_to_token:
        return ""

    return " ".join(
        positions_to_token[position]
        for position in sorted(positions_to_token)
        if positions_to_token[position]
    )


def _extract_authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    authors: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        author = item.get("author")
        if not isinstance(author, dict):
            continue
        display_name = _string(author.get("display_name"))
        if display_name:
            authors.append(display_name)
    return authors


def _extract_categories(item: dict[str, object]) -> list[str]:
    categories: list[str] = []
    seen: set[str] = set()
    for value in (
        _display_work_type(_string(item.get("type"))),
        _nested_string(item.get("primary_topic"), "field", "display_name"),
        _nested_string(item.get("primary_topic"), "subfield", "display_name"),
        *_topic_names(item.get("topics")),
    ):
        if value is None:
            continue
        normalized = value.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        categories.append(value)
    return categories


def _display_work_type(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("-", " ").title()


def _topic_names(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    names: list[str] = []
    for item in value[:2]:
        if not isinstance(item, dict):
            continue
        display_name = _string(item.get("display_name"))
        if display_name:
            names.append(display_name)
    return names


def _resolve_abstract_url(item: dict[str, object]) -> str:
    for value in (
        _nested_string(item.get("primary_location"), "landing_page_url"),
        _string(item.get("doi")),
        _string(item.get("id")),
    ):
        if value:
            return value
    return "https://openalex.org"


def _resolve_pdf_url(item: dict[str, object]) -> str | None:
    return _nested_string(item.get("best_oa_location"), "pdf_url") or _nested_string(
        item.get("primary_location"),
        "pdf_url",
    )


def _nested_string(value: object, *path: str) -> str | None:
    current = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return _string(current)


def _openalex_short_id(value: str) -> str:
    path = urlsplit(value).path.rstrip("/")
    if not path:
        return value
    return path.rsplit("/", maxsplit=1)[-1] or value


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
