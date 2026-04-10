"""PubMed client for fetching newly entered records."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request

from .arxiv_client import Paper
from .config import FeedConfig
from .network import fetch_bytes_with_retry

PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_ARTICLE_URL_TEMPLATE = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

_MONTH_NUMBERS = {
    "1": 1,
    "01": 1,
    "jan": 1,
    "january": 1,
    "2": 2,
    "02": 2,
    "feb": 2,
    "february": 2,
    "3": 3,
    "03": 3,
    "mar": 3,
    "march": 3,
    "4": 4,
    "04": 4,
    "apr": 4,
    "april": 4,
    "spring": 4,
    "5": 5,
    "05": 5,
    "may": 5,
    "6": 6,
    "06": 6,
    "jun": 6,
    "june": 6,
    "summer": 6,
    "7": 7,
    "07": 7,
    "jul": 7,
    "july": 7,
    "8": 8,
    "08": 8,
    "aug": 8,
    "august": 8,
    "9": 9,
    "09": 9,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "autumn": 9,
    "fall": 9,
    "10": 10,
    "oct": 10,
    "october": 10,
    "11": 11,
    "nov": 11,
    "november": 11,
    "12": 12,
    "dec": 12,
    "december": 12,
    "winter": 12,
}


class PubMedClientError(RuntimeError):
    """Raised when PubMed fetches or parsing fail."""


def fetch_latest_pubmed_papers(
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
    """Fetch recent PubMed records for a configured feed."""

    id_list = _search_pubmed_ids(
        feed,
        now=now,
        lookback_hours=lookback_hours,
        request_delay_seconds=request_delay_seconds,
        request_timeout_seconds=request_timeout_seconds,
        retry_attempts=retry_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
        contact_email=contact_email,
    )
    if not id_list:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "xml",
        "tool": "paper-digest",
    }
    if contact_email:
        params["email"] = contact_email

    request = Request(
        f"{PUBMED_EFETCH_URL}?{urlencode(params)}",
        headers={
            "User-Agent": _build_user_agent(contact_email),
            "Accept": "application/xml",
        },
    )
    payload = fetch_bytes_with_retry(
        request,
        timeout_seconds=request_timeout_seconds,
        request_delay_seconds=request_delay_seconds,
        retry_attempts=retry_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
        error_factory=PubMedClientError,
        operation_description=f"failed to fetch PubMed records for feed {feed.name!r}",
    )
    return parse_pubmed_response(payload)


def parse_pubmed_response(payload: bytes) -> list[Paper]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise PubMedClientError("received malformed XML from PubMed") from exc

    articles = root.findall("PubmedArticle")
    return [parse_pubmed_article(article) for article in articles]


def parse_pubmed_article(article: ET.Element) -> Paper:
    pmid = _required_text(
        article.find("./MedlineCitation/PMID"),
        "PubMed PMID is missing",
    )
    article_root = article.find("./MedlineCitation/Article")
    if article_root is None:
        raise PubMedClientError(f"PubMed record {pmid} is missing article metadata")

    title = _element_text(article_root.find("ArticleTitle")) or f"PubMed {pmid}"
    summary = _extract_abstract(article_root.find("Abstract"))
    authors = _extract_authors(article_root.find("AuthorList"))
    categories = _extract_publication_types(article_root.find("PublicationTypeList"))
    entered_at = _extract_entry_datetime(article)
    abstract_url = PUBMED_ARTICLE_URL_TEMPLATE.format(pmid=pmid)
    doi = _extract_article_id(article, "doi")

    return Paper(
        title=title,
        summary=summary,
        authors=authors,
        categories=categories,
        paper_id=f"pubmed:{pmid}",
        abstract_url=abstract_url,
        pdf_url=None,
        published_at=entered_at,
        updated_at=entered_at,
        source="pubmed",
        date_label="Entered",
        doi=doi,
    )


def _search_pubmed_ids(
    feed: FeedConfig,
    *,
    now: datetime,
    lookback_hours: int,
    request_delay_seconds: float,
    request_timeout_seconds: int,
    retry_attempts: int,
    retry_backoff_seconds: float,
    contact_email: str | None,
) -> list[str]:
    from_entry_date = (now - timedelta(hours=lookback_hours)).date().strftime(
        "%Y/%m/%d"
    )
    to_entry_date = now.date().strftime("%Y/%m/%d")
    params = {
        "db": "pubmed",
        "term": build_pubmed_search_term(feed),
        "retmax": str(feed.max_results),
        "retmode": "json",
        "sort": "pub_date",
        "datetype": "edat",
        "mindate": from_entry_date,
        "maxdate": to_entry_date,
        "tool": "paper-digest",
    }
    if contact_email:
        params["email"] = contact_email

    request = Request(
        f"{PUBMED_ESEARCH_URL}?{urlencode(params)}",
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
        error_factory=PubMedClientError,
        operation_description=f"failed to search PubMed for feed {feed.name!r}",
    )
    return parse_pubmed_search_response(payload)


def parse_pubmed_search_response(payload: bytes) -> list[str]:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PubMedClientError("received malformed JSON from PubMed") from exc

    search_result = raw.get("esearchresult")
    if not isinstance(search_result, dict):
        raise PubMedClientError("PubMed search response did not include esearchresult")

    id_list = search_result.get("idlist")
    if not isinstance(id_list, list):
        raise PubMedClientError("PubMed search response did not include a valid idlist")

    return [str(item).strip() for item in id_list if str(item).strip()]


def build_pubmed_search_term(feed: FeedConfig) -> str:
    query_clause = " OR ".join(f"({query})" for query in feed.queries)
    if not feed.types:
        return query_clause

    type_clause = " OR ".join(
        f'"{publication_type}"[Publication Type]' for publication_type in feed.types
    )
    return f"({query_clause}) AND ({type_clause})"


def _extract_article_id(article: ET.Element, id_type: str) -> str | None:
    article_id_list = article.find("./PubmedData/ArticleIdList")
    if article_id_list is None:
        return None

    target_type = id_type.casefold()
    for article_id in article_id_list.findall("ArticleId"):
        if article_id.attrib.get("IdType", "").casefold() != target_type:
            continue
        text = _element_text(article_id)
        if text:
            return text
    return None


def _extract_abstract(abstract_root: ET.Element | None) -> str:
    if abstract_root is None:
        return ""

    sections: list[str] = []
    for item in abstract_root.findall("AbstractText"):
        text = _element_text(item)
        if not text:
            continue
        label = (item.attrib.get("Label") or "").strip()
        if label:
            sections.append(f"{label}: {text}")
        else:
            sections.append(text)
    return " ".join(sections)


def _extract_authors(author_list_root: ET.Element | None) -> list[str]:
    if author_list_root is None:
        return []

    authors: list[str] = []
    for item in author_list_root.findall("Author"):
        collective = _element_text(item.find("CollectiveName"))
        if collective:
            authors.append(collective)
            continue

        fore_name = _element_text(item.find("ForeName"))
        last_name = _element_text(item.find("LastName"))
        full_name = " ".join(part for part in [fore_name, last_name] if part)
        if full_name:
            authors.append(full_name)
    return authors


def _extract_publication_types(root: ET.Element | None) -> list[str]:
    if root is None:
        return []
    publication_types: list[str] = []
    for item in root.findall("PublicationType"):
        text = _element_text(item)
        if text:
            publication_types.append(text)
    return publication_types


def _extract_entry_datetime(article: ET.Element) -> datetime:
    history = article.find("./PubmedData/History")
    if history is not None:
        for status in ("entrez", "pubmed", "medline"):
            node = history.find(f"./PubMedPubDate[@PubStatus='{status}']")
            if node is not None:
                return _parse_pubmed_date(node)

    for fallback_path in (
        "./MedlineCitation/DateCreated",
        "./MedlineCitation/DateCompleted",
        "./MedlineCitation/Article/ArticleDate",
        "./MedlineCitation/Article/Journal/JournalIssue/PubDate",
    ):
        node = article.find(fallback_path)
        if node is not None:
            return _parse_pubmed_date(node)

    raise PubMedClientError("PubMed record is missing date metadata")


def _parse_pubmed_date(node: ET.Element) -> datetime:
    year_text = _required_text(node.find("Year"), "PubMed date is missing year")
    try:
        year = int(year_text)
    except ValueError as exc:
        raise PubMedClientError(f"invalid PubMed year: {year_text!r}") from exc

    month_text = _element_text(node.find("Month")) or "1"
    month_key = month_text.strip().lower()
    month = _MONTH_NUMBERS.get(month_key)
    if month is None:
        raise PubMedClientError(f"invalid PubMed month: {month_text!r}")

    day_text = _element_text(node.find("Day")) or "1"
    try:
        day = int(day_text)
    except ValueError as exc:
        raise PubMedClientError(f"invalid PubMed day: {day_text!r}") from exc

    hour = _optional_int(_element_text(node.find("Hour")), default=0, field_name="hour")
    minute = _optional_int(
        _element_text(node.find("Minute")),
        default=0,
        field_name="minute",
    )
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _optional_int(value: str | None, *, default: int, field_name: str) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise PubMedClientError(f"invalid PubMed {field_name}: {value!r}") from exc


def _required_text(node: ET.Element | None, message: str) -> str:
    text = _element_text(node)
    if not text:
        raise PubMedClientError(message)
    return text


def _element_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join(part.strip() for part in node.itertext() if part and part.strip())


def _build_user_agent(contact_email: str | None) -> str:
    base = "paper-digest/0.1 (https://github.com/X-PG13/paper-digest)"
    if contact_email:
        return f"{base}; mailto:{contact_email}"
    return base
