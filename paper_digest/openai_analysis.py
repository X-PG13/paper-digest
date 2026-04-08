"""OpenAI-backed structured paper analysis."""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from .arxiv_client import Paper, PaperAnalysis
from .config import AnalysisConfig


class OpenAIAnalysisError(RuntimeError):
    """Raised when OpenAI analysis fails."""


def analyze_paper_with_openai(config: AnalysisConfig, paper: Paper) -> PaperAnalysis:
    """Analyze a single paper with the OpenAI Responses API."""

    api_key = os.getenv(config.api_key_env)
    if not api_key:
        raise OpenAIAnalysisError(
            f"analysis API key environment variable {config.api_key_env!r} is not set"
        )

    payload = {
        "model": config.model,
        "instructions": _build_instructions(config),
        "input": _build_input(paper),
        "max_output_tokens": config.max_output_tokens,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "paper_analysis",
                "strict": True,
                "schema": _analysis_schema(),
            }
        },
    }
    if config.reasoning_effort != "none":
        payload["reasoning"] = {"effort": config.reasoning_effort}

    request = Request(
        config.base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            raw_payload = response.read()
    except OSError as exc:
        raise OpenAIAnalysisError(
            f"failed to analyze paper {paper.paper_id!r}: {exc}"
        ) from exc

    response_json = _load_response_json(raw_payload)
    response_text = _extract_response_text(response_json)

    try:
        raw_analysis = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise OpenAIAnalysisError(
            "OpenAI analysis response was not valid JSON"
        ) from exc

    return _parse_paper_analysis(raw_analysis)


def _build_instructions(config: AnalysisConfig) -> str:
    template_hint = ""
    if config.template == "zh_daily_brief":
        template_hint = (
            " Prefer newsroom-style phrasing that reads naturally in a Chinese daily"
            " research briefing."
        )
    return (
        "You are writing concise research-digest notes. "
        "Use only the provided title, metadata, and abstract. "
        "Do not invent empirical claims or missing details. "
        "If the abstract does not support a point, say so cautiously. "
        f"Write every field in {config.language}. "
        "Keep each field compact and useful for a daily paper digest."
        f"{template_hint}"
    )


def _build_input(paper: Paper) -> str:
    authors = ", ".join(paper.authors) if paper.authors else "Unknown authors"
    categories = (
        ", ".join(paper.categories) if paper.categories else "Unknown categories"
    )
    return (
        f"Title: {paper.title}\n"
        f"Source: {paper.source}\n"
        f"Authors: {authors}\n"
        f"Categories: {categories}\n"
        f"Published: {paper.published_at.isoformat()}\n"
        f"Abstract URL: {paper.abstract_url}\n"
        f"Abstract:\n{paper.summary}"
    )


def _analysis_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "conclusion": {"type": "string"},
            "contributions": {
                "type": "array",
                "items": {"type": "string"},
            },
            "audience": {"type": "string"},
            "limitations": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "conclusion",
            "contributions",
            "audience",
            "limitations",
        ],
    }


def _load_response_json(payload: bytes) -> dict[str, object]:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise OpenAIAnalysisError("received malformed JSON from OpenAI") from exc

    if not isinstance(raw, dict):
        raise OpenAIAnalysisError("OpenAI response payload is invalid")

    error = raw.get("error")
    if isinstance(error, dict):
        message = error.get("message", "unknown error")
        raise OpenAIAnalysisError(f"OpenAI returned an error: {message}")

    status = raw.get("status")
    if isinstance(status, str) and status not in {"completed", "in_progress"}:
        raise OpenAIAnalysisError(
            f"OpenAI response did not complete successfully: {status}"
        )
    return raw


def _extract_response_text(raw: dict[str, object]) -> str:
    output_text = raw.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = raw.get("output")
    if not isinstance(output, list):
        raise OpenAIAnalysisError("OpenAI response did not include output content")

    fragments: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "refusal":
            raise OpenAIAnalysisError("OpenAI refused to analyze the paper")

        content = item.get("content")
        if not isinstance(content, list):
            continue

        for content_item in content:
            if not isinstance(content_item, dict):
                continue
            item_type = content_item.get("type")
            if item_type in {"output_text", "text"}:
                text = content_item.get("text")
                if isinstance(text, str) and text.strip():
                    fragments.append(text.strip())
            if item_type == "refusal":
                raise OpenAIAnalysisError("OpenAI refused to analyze the paper")

    if not fragments:
        raise OpenAIAnalysisError("OpenAI response did not include analysis text")
    return "\n".join(fragments)


def _parse_paper_analysis(raw: object) -> PaperAnalysis:
    if not isinstance(raw, dict):
        raise OpenAIAnalysisError("OpenAI analysis payload is invalid")

    conclusion = _required_string(raw.get("conclusion"), "analysis.conclusion")
    audience = _required_string(raw.get("audience"), "analysis.audience")
    contributions = _string_list(raw.get("contributions"), "analysis.contributions")
    limitations = _string_list(raw.get("limitations"), "analysis.limitations")

    return PaperAnalysis(
        conclusion=conclusion,
        contributions=contributions,
        audience=audience,
        limitations=limitations,
    )


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise OpenAIAnalysisError(f"{field_name} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise OpenAIAnalysisError(f"{field_name} must not be empty")
    return normalized


def _string_list(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise OpenAIAnalysisError(f"{field_name} must be an array of strings")

    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise OpenAIAnalysisError(f"{field_name} must contain only strings")
        normalized = " ".join(item.split())
        if normalized:
            result.append(normalized)
    return result
