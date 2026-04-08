"""Crossref client for fetching newly indexed works."""

from __future__ import annotations

import html
import json
import re
from datetime import UTC, datetime, timedelta
from time import sleep
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .arxiv_client import Paper
from .config import FeedConfig

CROSSREF_API_URL = "https://api.crossref.org/works"


class CrossrefClientError(RuntimeError):
    """Raised when Crossref fetches or parsing fail."""


def fetch_latest_crossref_papers(
    feed: FeedConfig,
    *,
    now: datetime,
    lookback_hours: int,
    request_delay_seconds: float,
    contact_email: str | None = None,
) -> list[Paper]:
    """Fetch recent Crossref works for a configured feed."""

    from_index_date = (now - timedelta(hours=lookback_hours)).date().isoformat()
    filters = [f"from-index-date:{from_index_date}"]
    for work_type in feed.types:
        filters.append(f"type:{work_type}")

    params = {
        "rows": feed.max_results,
        "sort": "indexed",
        "order": "desc",
        "filter": ",".join(filters),
        "query.bibliographic": " ".join(feed.queries),
    }
    if contact_email:
        params["mailto"] = contact_email

    request = Request(
        f"{CROSSREF_API_URL}?{urlencode(params)}",
        headers={
            "User-Agent": _build_user_agent(contact_email),
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read()
    except OSError as exc:
        raise CrossrefClientError(
            f"failed to fetch works for feed {feed.name!r}: {exc}"
        ) from exc

    papers = parse_crossref_response(payload)
    if request_delay_seconds > 0:
        sleep(request_delay_seconds)
    return papers


def parse_crossref_response(payload: bytes) -> list[Paper]:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise CrossrefClientError("received malformed JSON from Crossref") from exc

    message = raw.get("message")
    if not isinstance(message, dict):
        raise CrossrefClientError("Crossref response did not include a message object")

    items = message.get("items", [])
    if not isinstance(items, list):
        raise CrossrefClientError("Crossref response items payload is invalid")

    return [parse_crossref_item(item) for item in items if isinstance(item, dict)]


def parse_crossref_item(item: dict[str, object]) -> Paper:
    doi = _required_string(item.get("DOI"), "Crossref DOI is missing")
    abstract_url = _string(item.get("URL")) or f"https://doi.org/{doi}"
    indexed_at = _parse_crossref_datetime(item.get("indexed"))

    title_values = item.get("title", [])
    title = (
        _clean_text(title_values[0])
        if isinstance(title_values, list) and title_values
        else doi
    )

    subjects = item.get("subject")
    categories = (
        [subject for subject in subjects if isinstance(subject, str)]
        if isinstance(subjects, list)
        else []
    )

    return Paper(
        title=title,
        summary=_extract_abstract(item.get("abstract")),
        authors=_extract_authors(item.get("author")),
        categories=categories,
        paper_id=f"https://doi.org/{doi}",
        abstract_url=abstract_url,
        pdf_url=None,
        published_at=indexed_at,
        updated_at=indexed_at,
        source="crossref",
        date_label="Indexed",
    )


def _extract_authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    authors: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        literal = _string(item.get("literal"))
        if literal:
            authors.append(literal)
            continue

        given = _string(item.get("given"))
        family = _string(item.get("family"))
        full_name = " ".join(part for part in [given, family] if part)
        if full_name:
            authors.append(full_name)
    return authors


def _extract_abstract(value: object) -> str:
    if not isinstance(value, str):
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return _clean_text(html.unescape(without_tags))


def _parse_crossref_datetime(value: object) -> datetime:
    if not isinstance(value, dict):
        raise CrossrefClientError("Crossref item is missing indexed date information")

    date_time = value.get("date-time")
    if isinstance(date_time, str):
        return _parse_iso_datetime(date_time)

    timestamp = value.get("timestamp")
    if isinstance(timestamp, int):
        return datetime.fromtimestamp(timestamp / 1000, tz=UTC)

    raise CrossrefClientError("Crossref indexed date format is invalid")


def _parse_iso_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CrossrefClientError(f"invalid Crossref datetime: {value!r}") from exc


def _required_string(value: object, message: str) -> str:
    result = _string(value)
    if not result:
        raise CrossrefClientError(message)
    return result


def _string(value: object) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return None


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _build_user_agent(contact_email: str | None) -> str:
    base = "paper-digest/0.1 (https://github.com/X-PG13/paper-digest)"
    if contact_email:
        return f"{base}; mailto:{contact_email}"
    return base
