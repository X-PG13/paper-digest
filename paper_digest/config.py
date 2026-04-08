"""Configuration loading and validation."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigError(ValueError):
    """Raised when the project configuration is invalid."""


@dataclass(slots=True, frozen=True)
class FeedConfig:
    name: str
    categories: list[str]
    keywords: list[str]
    exclude_keywords: list[str]
    max_results: int
    max_items: int


@dataclass(slots=True, frozen=True)
class AppConfig:
    timezone: str
    lookback_hours: int
    output_dir: Path
    request_delay_seconds: float
    feeds: list[FeedConfig]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).expanduser()
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {config_path}") from exc

    try:
        raw = tomllib.loads(raw_text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("config root must be a TOML table")

    app_section = _as_table(raw.get("app"), "app")
    feeds_section = raw.get("feeds")
    if not isinstance(feeds_section, list) or not feeds_section:
        raise ConfigError("config must define at least one [[feeds]] entry")

    timezone_name = _validate_timezone(str(app_section.get("timezone", "UTC")).strip())
    lookback_hours = _positive_int(
        app_section.get("lookback_hours", 24),
        "app.lookback_hours",
    )
    output_dir = _resolve_output_dir(
        config_path,
        app_section.get("output_dir", "output"),
    )
    request_delay_seconds = _non_negative_float(
        app_section.get("request_delay_seconds", 3),
        "app.request_delay_seconds",
    )

    feeds = [
        _load_feed(raw_feed, index)
        for index, raw_feed in enumerate(feeds_section, start=1)
    ]

    return AppConfig(
        timezone=timezone_name,
        lookback_hours=lookback_hours,
        output_dir=output_dir,
        request_delay_seconds=request_delay_seconds,
        feeds=feeds,
    )


def _load_feed(raw_feed: Any, index: int) -> FeedConfig:
    feed = _as_table(raw_feed, f"feeds[{index}]")
    name = str(feed.get("name", "")).strip()
    if not name:
        raise ConfigError(f"feeds[{index}].name must be a non-empty string")

    categories = _string_list(feed.get("categories", []), f"feeds[{index}].categories")
    if not categories:
        raise ConfigError(f"feeds[{index}].categories must not be empty")

    return FeedConfig(
        name=name,
        categories=categories,
        keywords=_string_list(feed.get("keywords", []), f"feeds[{index}].keywords"),
        exclude_keywords=_string_list(
            feed.get("exclude_keywords", []),
            f"feeds[{index}].exclude_keywords",
        ),
        max_results=_positive_int(
            feed.get("max_results", 100),
            f"feeds[{index}].max_results",
        ),
        max_items=_positive_int(
            feed.get("max_items", 20),
            f"feeds[{index}].max_items",
        ),
    )


def _as_table(value: Any, field_name: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise ConfigError(f"{field_name} must be a TOML table")


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ConfigError(f"{field_name} must be an array of strings")

    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(f"{field_name} must contain only strings")
        normalized = item.strip()
        if not normalized:
            raise ConfigError(f"{field_name} must not contain empty strings")
        result.append(normalized)
    return result


def _positive_int(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be a positive integer") from exc
    if parsed <= 0:
        raise ConfigError(f"{field_name} must be a positive integer")
    return parsed


def _non_negative_float(value: Any, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be a non-negative number") from exc
    if parsed < 0:
        raise ConfigError(f"{field_name} must be a non-negative number")
    return parsed


def _resolve_output_dir(config_path: Path, value: Any) -> Path:
    raw_path = Path(str(value)).expanduser()
    if not raw_path.is_absolute():
        raw_path = config_path.parent / raw_path
    return raw_path.resolve()


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ConfigError(f"unknown timezone: {value}") from exc
    return value
