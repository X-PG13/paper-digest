"""Configuration loading and validation."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigError(ValueError):
    """Raised when the project configuration is invalid."""


FeedSource = Literal["arxiv", "crossref", "pubmed", "semantic_scholar", "openalex"]
DeliveryTarget = Literal["digest", "per_feed"]
DeliveryFocusTarget = Literal["digest", "separate"]
DeliveryActionTarget = Literal["digest", "separate"]
DeliveryType = Literal[
    "email",
    "feishu_webhook",
    "wecom_webhook",
    "slack_webhook",
    "discord_webhook",
    "telegram_bot",
]
AnalysisProvider = Literal["openai"]
AnalysisReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]
DigestTemplate = Literal["default", "zh_daily_brief"]
SortMode = Literal["relevance", "published_at", "hybrid"]
FeedbackStatus = Literal["star", "follow_up", "reading", "done", "ignore"]
FocusReason = Literal["new_starred", "follow_up_resurfaced", "starred_momentum"]
ActionReason = Literal[
    "overdue",
    "overdue_1d",
    "overdue_3d",
    "overdue_7d",
    "due_soon",
    "next_action_pending",
    "recurring_review",
]


@dataclass(slots=True, frozen=True)
class FeedConfig:
    name: str
    source: FeedSource = "arxiv"
    categories: list[str] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    max_results: int = 100
    max_items: int = 20
    sort_by: SortMode | None = None


@dataclass(slots=True, frozen=True)
class EmailConfig:
    smtp_host: str
    smtp_port: int
    username: str | None
    password_env: str | None
    from_address: str
    to_addresses: list[str]
    use_tls: bool
    use_starttls: bool
    subject_prefix: str
    skip_if_empty: bool
    target: DeliveryTarget = "digest"
    include_focus: bool = True
    focus_target: DeliveryFocusTarget = "digest"
    focus_statuses: list[FeedbackStatus] = field(default_factory=list)
    focus_reasons: list[FocusReason] = field(default_factory=list)
    focus_max_items: int | None = None
    include_actions: bool = True
    action_target: DeliveryActionTarget = "digest"
    action_only: bool = False
    action_statuses: list[FeedbackStatus] = field(default_factory=list)
    action_reasons: list[ActionReason] = field(default_factory=list)
    action_max_items: int | None = None
    action_overdue_only: bool = False
    action_due_within_days: int | None = None


@dataclass(slots=True, frozen=True)
class FeishuWebhookConfig:
    webhook_url: str
    title_prefix: str
    skip_if_empty: bool
    target: DeliveryTarget = "digest"
    include_focus: bool = True
    focus_target: DeliveryFocusTarget = "digest"
    focus_statuses: list[FeedbackStatus] = field(default_factory=list)
    focus_reasons: list[FocusReason] = field(default_factory=list)
    focus_max_items: int | None = None
    include_actions: bool = True
    action_target: DeliveryActionTarget = "digest"
    action_only: bool = False
    action_statuses: list[FeedbackStatus] = field(default_factory=list)
    action_reasons: list[ActionReason] = field(default_factory=list)
    action_max_items: int | None = field(default=None)
    action_overdue_only: bool = False
    action_due_within_days: int | None = None


@dataclass(slots=True, frozen=True)
class WeComWebhookConfig:
    webhook_url: str
    title_prefix: str
    skip_if_empty: bool
    target: DeliveryTarget = "digest"
    include_focus: bool = True
    focus_target: DeliveryFocusTarget = "digest"
    focus_statuses: list[FeedbackStatus] = field(default_factory=list)
    focus_reasons: list[FocusReason] = field(default_factory=list)
    focus_max_items: int | None = None
    include_actions: bool = True
    action_target: DeliveryActionTarget = "digest"
    action_only: bool = False
    action_statuses: list[FeedbackStatus] = field(default_factory=list)
    action_reasons: list[ActionReason] = field(default_factory=list)
    action_max_items: int | None = None
    action_overdue_only: bool = False
    action_due_within_days: int | None = None


@dataclass(slots=True, frozen=True)
class SlackWebhookConfig:
    webhook_url: str
    title_prefix: str
    skip_if_empty: bool
    target: DeliveryTarget = "digest"
    include_focus: bool = True
    focus_target: DeliveryFocusTarget = "digest"
    focus_statuses: list[FeedbackStatus] = field(default_factory=list)
    focus_reasons: list[FocusReason] = field(default_factory=list)
    focus_max_items: int | None = None
    include_actions: bool = True
    action_target: DeliveryActionTarget = "digest"
    action_only: bool = False
    action_statuses: list[FeedbackStatus] = field(default_factory=list)
    action_reasons: list[ActionReason] = field(default_factory=list)
    action_max_items: int | None = None
    action_overdue_only: bool = False
    action_due_within_days: int | None = None


@dataclass(slots=True, frozen=True)
class DiscordWebhookConfig:
    webhook_url: str
    title_prefix: str
    skip_if_empty: bool
    target: DeliveryTarget = "digest"
    include_focus: bool = True
    focus_target: DeliveryFocusTarget = "digest"
    focus_statuses: list[FeedbackStatus] = field(default_factory=list)
    focus_reasons: list[FocusReason] = field(default_factory=list)
    focus_max_items: int | None = None
    include_actions: bool = True
    action_target: DeliveryActionTarget = "digest"
    action_only: bool = False
    action_statuses: list[FeedbackStatus] = field(default_factory=list)
    action_reasons: list[ActionReason] = field(default_factory=list)
    action_max_items: int | None = None
    action_overdue_only: bool = False
    action_due_within_days: int | None = None


@dataclass(slots=True, frozen=True)
class TelegramBotConfig:
    bot_token: str
    chat_id: str
    title_prefix: str
    skip_if_empty: bool
    target: DeliveryTarget = "digest"
    include_focus: bool = True
    focus_target: DeliveryFocusTarget = "digest"
    focus_statuses: list[FeedbackStatus] = field(default_factory=list)
    focus_reasons: list[FocusReason] = field(default_factory=list)
    focus_max_items: int | None = None
    include_actions: bool = True
    action_target: DeliveryActionTarget = "digest"
    action_only: bool = False
    action_statuses: list[FeedbackStatus] = field(default_factory=list)
    action_reasons: list[ActionReason] = field(default_factory=list)
    action_max_items: int | None = None
    action_overdue_only: bool = False
    action_due_within_days: int | None = None


DeliveryConfig = (
    EmailConfig
    | FeishuWebhookConfig
    | WeComWebhookConfig
    | SlackWebhookConfig
    | DiscordWebhookConfig
    | TelegramBotConfig
)


@dataclass(slots=True, frozen=True)
class StateConfig:
    enabled: bool
    path: Path
    retention_days: int


@dataclass(slots=True, frozen=True)
class FeedbackConfig:
    enabled: bool
    path: Path
    star_boost: int = 80
    follow_up_boost: int = 35
    reading_boost: int = 18
    done_penalty: int = 20
    ignore_penalty: int = 120
    hide_ignored: bool = True


@dataclass(slots=True, frozen=True)
class NotifyConfig:
    feedback_only: bool = False
    include_new_starred: bool = True
    include_follow_up_resurfaced: bool = True
    include_starred_momentum: bool = True
    max_focus_items: int = 5
    max_action_items: int = 5
    action_overdue_only: bool = False
    action_due_within_days: int | None = None


@dataclass(slots=True, frozen=True)
class DigestConfig:
    template: DigestTemplate = "default"
    top_highlights: int = 3
    feed_key_points: int = 3


@dataclass(slots=True, frozen=True)
class RankingWeights:
    title_match_weight: int = 40
    summary_match_weight: int = 18
    doi_weight: int = 12
    pdf_weight: int = 8
    rich_summary_weight: int = 6
    metadata_weight: int = 4
    multi_source_weight: int = 10
    freshness_weight_cap: int = 24


@dataclass(slots=True, frozen=True)
class RankingConfig:
    sort_by: SortMode = "hybrid"
    weights: RankingWeights = field(default_factory=RankingWeights)


@dataclass(slots=True, frozen=True)
class AnalysisConfig:
    provider: AnalysisProvider
    model: str
    api_key_env: str
    base_url: str
    timeout_seconds: int
    max_papers: int
    max_output_tokens: int
    language: str
    reasoning_effort: AnalysisReasoningEffort


def _default_feedback_config() -> FeedbackConfig:
    return FeedbackConfig(
        enabled=True,
        path=Path(".paper-digest-state/feedback.json"),
    )


@dataclass(slots=True, frozen=True)
class AppConfig:
    timezone: str
    lookback_hours: int
    output_dir: Path
    request_delay_seconds: float
    feeds: list[FeedConfig]
    state: StateConfig
    feedback: FeedbackConfig = field(default_factory=_default_feedback_config)
    notify: NotifyConfig = field(default_factory=NotifyConfig)
    request_timeout_seconds: int = 60
    fetch_retry_attempts: int = 4
    fetch_retry_backoff_seconds: float = 10.0
    openalex_api_key_env: str | None = None
    digest: DigestConfig = field(default_factory=DigestConfig)
    ranking: RankingConfig = field(default_factory=RankingConfig)
    analysis: AnalysisConfig | None = None
    deliveries: list[DeliveryConfig] = field(default_factory=list)
    email: EmailConfig | None = None


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
    request_timeout_seconds = _positive_int(
        app_section.get("request_timeout_seconds", 60),
        "app.request_timeout_seconds",
    )
    fetch_retry_attempts = _positive_int(
        app_section.get("fetch_retry_attempts", 4),
        "app.fetch_retry_attempts",
    )
    fetch_retry_backoff_seconds = _non_negative_float(
        app_section.get("fetch_retry_backoff_seconds", 10),
        "app.fetch_retry_backoff_seconds",
    )

    feeds = [
        _load_feed(raw_feed, index)
        for index, raw_feed in enumerate(feeds_section, start=1)
    ]
    state = _load_state(raw.get("state"), config_path)
    feedback = _load_feedback(raw.get("feedback"), config_path)
    notify = _load_notify(raw.get("notify"))
    digest = _load_digest(raw.get("digest"), raw.get("analysis"))
    ranking = _load_ranking(raw.get("ranking"))
    analysis = _load_analysis(raw.get("analysis"))
    deliveries = _load_deliveries(raw.get("deliveries"))
    email = _load_email(raw.get("email"))

    return AppConfig(
        timezone=timezone_name,
        lookback_hours=lookback_hours,
        output_dir=output_dir,
        request_delay_seconds=request_delay_seconds,
        feeds=feeds,
        state=state,
        feedback=feedback,
        notify=notify,
        request_timeout_seconds=request_timeout_seconds,
        fetch_retry_attempts=fetch_retry_attempts,
        fetch_retry_backoff_seconds=fetch_retry_backoff_seconds,
        openalex_api_key_env=_optional_string(
            app_section.get("openalex_api_key_env"),
            "app.openalex_api_key_env",
        ),
        digest=digest,
        ranking=ranking,
        analysis=analysis,
        deliveries=deliveries,
        email=email,
    )


def _load_feed(raw_feed: Any, index: int) -> FeedConfig:
    feed = _as_table(raw_feed, f"feeds[{index}]")
    name = str(feed.get("name", "")).strip()
    if not name:
        raise ConfigError(f"feeds[{index}].name must be a non-empty string")

    source = _feed_source(feed.get("source", "arxiv"), f"feeds[{index}].source")
    categories = _string_list(feed.get("categories", []), f"feeds[{index}].categories")
    queries = _string_list(feed.get("queries", []), f"feeds[{index}].queries")
    types = _string_list(feed.get("types", []), f"feeds[{index}].types")

    if source == "arxiv" and not categories:
        raise ConfigError(f"feeds[{index}].categories must not be empty for arxiv")
    if source in {"crossref", "pubmed", "semantic_scholar", "openalex"} and not queries:
        raise ConfigError(
            f"feeds[{index}].queries must not be empty for {source}"
        )

    return FeedConfig(
        name=name,
        source=source,
        categories=categories,
        queries=queries,
        types=types,
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
        sort_by=_optional_sort_mode(feed.get("sort_by"), f"feeds[{index}].sort_by"),
    )


def _as_table(value: Any, field_name: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise ConfigError(f"{field_name} must be a TOML table")


def _load_state(value: Any, config_path: Path) -> StateConfig:
    if value is None:
        value = {}

    state = _as_table(value, "state")
    return StateConfig(
        enabled=_bool(state.get("enabled", True), "state.enabled"),
        path=_resolve_output_dir(
            config_path,
            state.get("path", ".paper-digest-state/state.json"),
        ),
        retention_days=_positive_int(
            state.get("retention_days", 90),
            "state.retention_days",
        ),
    )


def _load_feedback(value: Any, config_path: Path) -> FeedbackConfig:
    if value is None:
        value = {}

    feedback = _as_table(value, "feedback")
    return FeedbackConfig(
        enabled=_bool(feedback.get("enabled", True), "feedback.enabled"),
        path=_resolve_output_dir(
            config_path,
            feedback.get("path", ".paper-digest-state/feedback.json"),
        ),
        star_boost=_non_negative_int(
            feedback.get("star_boost", 80),
            "feedback.star_boost",
        ),
        follow_up_boost=_non_negative_int(
            feedback.get("follow_up_boost", 35),
            "feedback.follow_up_boost",
        ),
        reading_boost=_non_negative_int(
            feedback.get("reading_boost", 18),
            "feedback.reading_boost",
        ),
        done_penalty=_non_negative_int(
            feedback.get("done_penalty", 20),
            "feedback.done_penalty",
        ),
        ignore_penalty=_non_negative_int(
            feedback.get("ignore_penalty", 120),
            "feedback.ignore_penalty",
        ),
        hide_ignored=_bool(
            feedback.get("hide_ignored", True),
            "feedback.hide_ignored",
        ),
    )


def _load_notify(value: Any) -> NotifyConfig:
    if value is None:
        return NotifyConfig()

    notify = _as_table(value, "notify")
    return NotifyConfig(
        feedback_only=_bool(
            notify.get("feedback_only", False),
            "notify.feedback_only",
        ),
        include_new_starred=_bool(
            notify.get("include_new_starred", True),
            "notify.include_new_starred",
        ),
        include_follow_up_resurfaced=_bool(
            notify.get("include_follow_up_resurfaced", True),
            "notify.include_follow_up_resurfaced",
        ),
        include_starred_momentum=_bool(
            notify.get("include_starred_momentum", True),
            "notify.include_starred_momentum",
        ),
        max_focus_items=_positive_int(
            notify.get("max_focus_items", 5),
            "notify.max_focus_items",
        ),
        max_action_items=_positive_int(
            notify.get("max_action_items", 5),
            "notify.max_action_items",
        ),
        action_overdue_only=_bool(
            notify.get("action_overdue_only", False),
            "notify.action_overdue_only",
        ),
        action_due_within_days=_optional_non_negative_int(
            notify.get("action_due_within_days"),
            "notify.action_due_within_days",
        ),
    )


def _load_email(value: Any) -> EmailConfig | None:
    if value is None:
        return None

    email = _as_table(value, "email")
    if not _bool(email.get("enabled", True), "email.enabled"):
        return None

    return _build_email_config(email, "email")


def _load_digest(value: Any, legacy_analysis_value: Any) -> DigestConfig:
    if value is None:
        if isinstance(legacy_analysis_value, dict):
            return _build_digest_config(legacy_analysis_value, "analysis")
        return DigestConfig()

    digest = _as_table(value, "digest")
    return _build_digest_config(digest, "digest")


def _build_digest_config(value: dict[str, Any], field_name: str) -> DigestConfig:
    return DigestConfig(
        template=_digest_template(
            value.get("template", "default"),
            f"{field_name}.template",
        ),
        top_highlights=_positive_int(
            value.get("top_highlights", 3),
            f"{field_name}.top_highlights",
        ),
        feed_key_points=_positive_int(
            value.get("feed_key_points", 3),
            f"{field_name}.feed_key_points",
        ),
    )


def _load_analysis(value: Any) -> AnalysisConfig | None:
    if value is None:
        return None

    analysis = _as_table(value, "analysis")
    if not _bool(analysis.get("enabled", True), "analysis.enabled"):
        return None

    return AnalysisConfig(
        provider=_analysis_provider(
            analysis.get("provider", "openai"),
            "analysis.provider",
        ),
        model=_required_string(analysis.get("model", "gpt-5-mini"), "analysis.model"),
        api_key_env=_required_string(
            analysis.get("api_key_env", "OPENAI_API_KEY"),
            "analysis.api_key_env",
        ),
        base_url=_required_string(
            analysis.get("base_url", "https://api.openai.com/v1/responses"),
            "analysis.base_url",
        ),
        timeout_seconds=_positive_int(
            analysis.get("timeout_seconds", 60),
            "analysis.timeout_seconds",
        ),
        max_papers=_positive_int(
            analysis.get("max_papers", 10),
            "analysis.max_papers",
        ),
        max_output_tokens=_positive_int(
            analysis.get("max_output_tokens", 600),
            "analysis.max_output_tokens",
        ),
        language=_required_string(
            analysis.get("language", "English"), "analysis.language"
        ),
        reasoning_effort=_analysis_reasoning_effort(
            analysis.get("reasoning_effort", "minimal"),
            "analysis.reasoning_effort",
        ),
    )


def _load_ranking(value: Any) -> RankingConfig:
    if value is None:
        return RankingConfig()

    ranking = _as_table(value, "ranking")
    return RankingConfig(
        sort_by=_sort_mode(ranking.get("sort_by", "hybrid"), "ranking.sort_by"),
        weights=RankingWeights(
            title_match_weight=_non_negative_int(
                ranking.get("title_match_weight", 40),
                "ranking.title_match_weight",
            ),
            summary_match_weight=_non_negative_int(
                ranking.get("summary_match_weight", 18),
                "ranking.summary_match_weight",
            ),
            doi_weight=_non_negative_int(
                ranking.get("doi_weight", 12),
                "ranking.doi_weight",
            ),
            pdf_weight=_non_negative_int(
                ranking.get("pdf_weight", 8),
                "ranking.pdf_weight",
            ),
            rich_summary_weight=_non_negative_int(
                ranking.get("rich_summary_weight", 6),
                "ranking.rich_summary_weight",
            ),
            metadata_weight=_non_negative_int(
                ranking.get("metadata_weight", 4),
                "ranking.metadata_weight",
            ),
            multi_source_weight=_non_negative_int(
                ranking.get("multi_source_weight", 10),
                "ranking.multi_source_weight",
            ),
            freshness_weight_cap=_non_negative_int(
                ranking.get("freshness_weight_cap", 24),
                "ranking.freshness_weight_cap",
            ),
        ),
    )


def _load_deliveries(
    value: Any,
) -> list[DeliveryConfig]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError("deliveries must be an array of tables")

    deliveries: list[DeliveryConfig] = []
    for index, raw_delivery in enumerate(value, start=1):
        field_name = f"deliveries[{index}]"
        delivery = _as_table(raw_delivery, field_name)
        delivery_type = _delivery_type(delivery.get("type"), f"{field_name}.type")
        if delivery_type == "email":
            deliveries.append(_build_email_config(delivery, field_name))
            continue
        if delivery_type == "feishu_webhook":
            deliveries.append(_build_feishu_webhook_config(delivery, field_name))
            continue
        if delivery_type == "wecom_webhook":
            deliveries.append(_build_wecom_webhook_config(delivery, field_name))
            continue
        if delivery_type == "slack_webhook":
            deliveries.append(_build_slack_webhook_config(delivery, field_name))
            continue
        if delivery_type == "discord_webhook":
            deliveries.append(_build_discord_webhook_config(delivery, field_name))
            continue
        deliveries.append(_build_telegram_bot_config(delivery, field_name))
    return deliveries


def _build_email_config(value: dict[str, Any], field_name: str) -> EmailConfig:
    username = _optional_string(value.get("username"), f"{field_name}.username")
    password_env = _optional_string(
        value.get("password_env"),
        f"{field_name}.password_env",
    )
    if (username is None) != (password_env is None):
        raise ConfigError(
            f"{field_name}.username and {field_name}.password_env "
            "must either both be set "
            "or both be omitted"
        )

    use_tls = _bool(value.get("use_tls", True), f"{field_name}.use_tls")
    use_starttls = _bool(
        value.get("use_starttls", False),
        f"{field_name}.use_starttls",
    )
    if use_tls and use_starttls:
        raise ConfigError(
            f"{field_name}.use_tls and {field_name}.use_starttls cannot both be true"
        )

    to_addresses = _string_list(
        value.get("to_addresses", []), f"{field_name}.to_addresses"
    )
    if not to_addresses:
        raise ConfigError(
            f"{field_name}.to_addresses must not be empty when email is enabled"
        )

    config = EmailConfig(
        smtp_host=_required_string(value.get("smtp_host"), f"{field_name}.smtp_host"),
        smtp_port=_positive_int(value.get("smtp_port", 465), f"{field_name}.smtp_port"),
        username=username,
        password_env=password_env,
        from_address=_required_string(
            value.get("from_address"),
            f"{field_name}.from_address",
        ),
        to_addresses=to_addresses,
        use_tls=use_tls,
        use_starttls=use_starttls,
        subject_prefix=_default_prefixed_string(
            value.get("subject_prefix", value.get("title_prefix", "[Paper Digest]")),
            f"{field_name}.subject_prefix",
            "[Paper Digest]",
        ),
        skip_if_empty=_bool(
            value.get("skip_if_empty", True),
            f"{field_name}.skip_if_empty",
        ),
        target=_delivery_target(
            value.get("target", "digest"),
            f"{field_name}.target",
        ),
        include_focus=_bool(
            value.get("include_focus", True),
            f"{field_name}.include_focus",
        ),
        focus_target=_delivery_focus_target(
            value.get("focus_target", "digest"),
            f"{field_name}.focus_target",
        ),
        focus_statuses=_focus_status_list(
            value.get("focus_statuses", []),
            f"{field_name}.focus_statuses",
        ),
        focus_reasons=_focus_reason_list(
            value.get("focus_reasons", []),
            f"{field_name}.focus_reasons",
        ),
        focus_max_items=_optional_positive_int(
            value.get("focus_max_items"),
            f"{field_name}.focus_max_items",
        ),
        include_actions=_bool(
            value.get("include_actions", True),
            f"{field_name}.include_actions",
        ),
        action_target=_delivery_action_target(
            value.get("action_target", "digest"),
            f"{field_name}.action_target",
        ),
        action_only=_bool(
            value.get("action_only", False),
            f"{field_name}.action_only",
        ),
        action_statuses=_action_status_list(
            value.get("action_statuses", []),
            f"{field_name}.action_statuses",
        ),
        action_reasons=_action_reason_list(
            value.get("action_reasons", []),
            f"{field_name}.action_reasons",
        ),
        action_max_items=_optional_positive_int(
            value.get("action_max_items"),
            f"{field_name}.action_max_items",
        ),
        action_overdue_only=_bool(
            value.get("action_overdue_only", False),
            f"{field_name}.action_overdue_only",
        ),
        action_due_within_days=_optional_non_negative_int(
            value.get("action_due_within_days"),
            f"{field_name}.action_due_within_days",
        ),
    )
    _validate_delivery_action_config(config, field_name)
    return config


def _build_feishu_webhook_config(
    value: dict[str, Any],
    field_name: str,
) -> FeishuWebhookConfig:
    config = FeishuWebhookConfig(
        webhook_url=_required_string(
            value.get("webhook_url"), f"{field_name}.webhook_url"
        ),
        title_prefix=_default_prefixed_string(
            value.get("title_prefix", "[Paper Digest]"),
            f"{field_name}.title_prefix",
            "[Paper Digest]",
        ),
        skip_if_empty=_bool(
            value.get("skip_if_empty", True),
            f"{field_name}.skip_if_empty",
        ),
        target=_delivery_target(
            value.get("target", "digest"),
            f"{field_name}.target",
        ),
        include_focus=_bool(
            value.get("include_focus", True),
            f"{field_name}.include_focus",
        ),
        focus_target=_delivery_focus_target(
            value.get("focus_target", "digest"),
            f"{field_name}.focus_target",
        ),
        focus_statuses=_focus_status_list(
            value.get("focus_statuses", []),
            f"{field_name}.focus_statuses",
        ),
        focus_reasons=_focus_reason_list(
            value.get("focus_reasons", []),
            f"{field_name}.focus_reasons",
        ),
        focus_max_items=_optional_positive_int(
            value.get("focus_max_items"),
            f"{field_name}.focus_max_items",
        ),
        include_actions=_bool(
            value.get("include_actions", True),
            f"{field_name}.include_actions",
        ),
        action_target=_delivery_action_target(
            value.get("action_target", "digest"),
            f"{field_name}.action_target",
        ),
        action_only=_bool(
            value.get("action_only", False),
            f"{field_name}.action_only",
        ),
        action_statuses=_action_status_list(
            value.get("action_statuses", []),
            f"{field_name}.action_statuses",
        ),
        action_reasons=_action_reason_list(
            value.get("action_reasons", []),
            f"{field_name}.action_reasons",
        ),
        action_max_items=_optional_positive_int(
            value.get("action_max_items"),
            f"{field_name}.action_max_items",
        ),
        action_overdue_only=_bool(
            value.get("action_overdue_only", False),
            f"{field_name}.action_overdue_only",
        ),
        action_due_within_days=_optional_non_negative_int(
            value.get("action_due_within_days"),
            f"{field_name}.action_due_within_days",
        ),
    )
    _validate_delivery_action_config(config, field_name)
    return config


def _build_wecom_webhook_config(
    value: dict[str, Any],
    field_name: str,
) -> WeComWebhookConfig:
    config = WeComWebhookConfig(
        webhook_url=_required_string(
            value.get("webhook_url"), f"{field_name}.webhook_url"
        ),
        title_prefix=_default_prefixed_string(
            value.get("title_prefix", "[Paper Digest]"),
            f"{field_name}.title_prefix",
            "[Paper Digest]",
        ),
        skip_if_empty=_bool(
            value.get("skip_if_empty", True),
            f"{field_name}.skip_if_empty",
        ),
        target=_delivery_target(
            value.get("target", "digest"),
            f"{field_name}.target",
        ),
        include_focus=_bool(
            value.get("include_focus", True),
            f"{field_name}.include_focus",
        ),
        focus_target=_delivery_focus_target(
            value.get("focus_target", "digest"),
            f"{field_name}.focus_target",
        ),
        focus_statuses=_focus_status_list(
            value.get("focus_statuses", []),
            f"{field_name}.focus_statuses",
        ),
        focus_reasons=_focus_reason_list(
            value.get("focus_reasons", []),
            f"{field_name}.focus_reasons",
        ),
        focus_max_items=_optional_positive_int(
            value.get("focus_max_items"),
            f"{field_name}.focus_max_items",
        ),
        include_actions=_bool(
            value.get("include_actions", True),
            f"{field_name}.include_actions",
        ),
        action_target=_delivery_action_target(
            value.get("action_target", "digest"),
            f"{field_name}.action_target",
        ),
        action_only=_bool(
            value.get("action_only", False),
            f"{field_name}.action_only",
        ),
        action_statuses=_action_status_list(
            value.get("action_statuses", []),
            f"{field_name}.action_statuses",
        ),
        action_reasons=_action_reason_list(
            value.get("action_reasons", []),
            f"{field_name}.action_reasons",
        ),
        action_max_items=_optional_positive_int(
            value.get("action_max_items"),
            f"{field_name}.action_max_items",
        ),
        action_overdue_only=_bool(
            value.get("action_overdue_only", False),
            f"{field_name}.action_overdue_only",
        ),
        action_due_within_days=_optional_non_negative_int(
            value.get("action_due_within_days"),
            f"{field_name}.action_due_within_days",
        ),
    )
    _validate_delivery_action_config(config, field_name)
    return config


def _build_slack_webhook_config(
    value: dict[str, Any],
    field_name: str,
) -> SlackWebhookConfig:
    config = SlackWebhookConfig(
        webhook_url=_required_string(
            value.get("webhook_url"), f"{field_name}.webhook_url"
        ),
        title_prefix=_default_prefixed_string(
            value.get("title_prefix", "[Paper Digest]"),
            f"{field_name}.title_prefix",
            "[Paper Digest]",
        ),
        skip_if_empty=_bool(
            value.get("skip_if_empty", True),
            f"{field_name}.skip_if_empty",
        ),
        target=_delivery_target(
            value.get("target", "digest"),
            f"{field_name}.target",
        ),
        include_focus=_bool(
            value.get("include_focus", True),
            f"{field_name}.include_focus",
        ),
        focus_target=_delivery_focus_target(
            value.get("focus_target", "digest"),
            f"{field_name}.focus_target",
        ),
        focus_statuses=_focus_status_list(
            value.get("focus_statuses", []),
            f"{field_name}.focus_statuses",
        ),
        focus_reasons=_focus_reason_list(
            value.get("focus_reasons", []),
            f"{field_name}.focus_reasons",
        ),
        focus_max_items=_optional_positive_int(
            value.get("focus_max_items"),
            f"{field_name}.focus_max_items",
        ),
        include_actions=_bool(
            value.get("include_actions", True),
            f"{field_name}.include_actions",
        ),
        action_target=_delivery_action_target(
            value.get("action_target", "digest"),
            f"{field_name}.action_target",
        ),
        action_only=_bool(
            value.get("action_only", False),
            f"{field_name}.action_only",
        ),
        action_statuses=_action_status_list(
            value.get("action_statuses", []),
            f"{field_name}.action_statuses",
        ),
        action_reasons=_action_reason_list(
            value.get("action_reasons", []),
            f"{field_name}.action_reasons",
        ),
        action_max_items=_optional_positive_int(
            value.get("action_max_items"),
            f"{field_name}.action_max_items",
        ),
        action_overdue_only=_bool(
            value.get("action_overdue_only", False),
            f"{field_name}.action_overdue_only",
        ),
        action_due_within_days=_optional_non_negative_int(
            value.get("action_due_within_days"),
            f"{field_name}.action_due_within_days",
        ),
    )
    _validate_delivery_action_config(config, field_name)
    return config


def _build_discord_webhook_config(
    value: dict[str, Any],
    field_name: str,
) -> DiscordWebhookConfig:
    config = DiscordWebhookConfig(
        webhook_url=_required_string(
            value.get("webhook_url"), f"{field_name}.webhook_url"
        ),
        title_prefix=_default_prefixed_string(
            value.get("title_prefix", "[Paper Digest]"),
            f"{field_name}.title_prefix",
            "[Paper Digest]",
        ),
        skip_if_empty=_bool(
            value.get("skip_if_empty", True),
            f"{field_name}.skip_if_empty",
        ),
        target=_delivery_target(
            value.get("target", "digest"),
            f"{field_name}.target",
        ),
        include_focus=_bool(
            value.get("include_focus", True),
            f"{field_name}.include_focus",
        ),
        focus_target=_delivery_focus_target(
            value.get("focus_target", "digest"),
            f"{field_name}.focus_target",
        ),
        focus_statuses=_focus_status_list(
            value.get("focus_statuses", []),
            f"{field_name}.focus_statuses",
        ),
        focus_reasons=_focus_reason_list(
            value.get("focus_reasons", []),
            f"{field_name}.focus_reasons",
        ),
        focus_max_items=_optional_positive_int(
            value.get("focus_max_items"),
            f"{field_name}.focus_max_items",
        ),
        include_actions=_bool(
            value.get("include_actions", True),
            f"{field_name}.include_actions",
        ),
        action_target=_delivery_action_target(
            value.get("action_target", "digest"),
            f"{field_name}.action_target",
        ),
        action_only=_bool(
            value.get("action_only", False),
            f"{field_name}.action_only",
        ),
        action_statuses=_action_status_list(
            value.get("action_statuses", []),
            f"{field_name}.action_statuses",
        ),
        action_reasons=_action_reason_list(
            value.get("action_reasons", []),
            f"{field_name}.action_reasons",
        ),
        action_max_items=_optional_positive_int(
            value.get("action_max_items"),
            f"{field_name}.action_max_items",
        ),
        action_overdue_only=_bool(
            value.get("action_overdue_only", False),
            f"{field_name}.action_overdue_only",
        ),
        action_due_within_days=_optional_non_negative_int(
            value.get("action_due_within_days"),
            f"{field_name}.action_due_within_days",
        ),
    )
    _validate_delivery_action_config(config, field_name)
    return config


def _build_telegram_bot_config(
    value: dict[str, Any],
    field_name: str,
) -> TelegramBotConfig:
    config = TelegramBotConfig(
        bot_token=_required_string(value.get("bot_token"), f"{field_name}.bot_token"),
        chat_id=_required_string(value.get("chat_id"), f"{field_name}.chat_id"),
        title_prefix=_default_prefixed_string(
            value.get("title_prefix", "[Paper Digest]"),
            f"{field_name}.title_prefix",
            "[Paper Digest]",
        ),
        skip_if_empty=_bool(
            value.get("skip_if_empty", True),
            f"{field_name}.skip_if_empty",
        ),
        target=_delivery_target(
            value.get("target", "digest"),
            f"{field_name}.target",
        ),
        include_focus=_bool(
            value.get("include_focus", True),
            f"{field_name}.include_focus",
        ),
        focus_target=_delivery_focus_target(
            value.get("focus_target", "digest"),
            f"{field_name}.focus_target",
        ),
        focus_statuses=_focus_status_list(
            value.get("focus_statuses", []),
            f"{field_name}.focus_statuses",
        ),
        focus_reasons=_focus_reason_list(
            value.get("focus_reasons", []),
            f"{field_name}.focus_reasons",
        ),
        focus_max_items=_optional_positive_int(
            value.get("focus_max_items"),
            f"{field_name}.focus_max_items",
        ),
        include_actions=_bool(
            value.get("include_actions", True),
            f"{field_name}.include_actions",
        ),
        action_target=_delivery_action_target(
            value.get("action_target", "digest"),
            f"{field_name}.action_target",
        ),
        action_only=_bool(
            value.get("action_only", False),
            f"{field_name}.action_only",
        ),
        action_statuses=_action_status_list(
            value.get("action_statuses", []),
            f"{field_name}.action_statuses",
        ),
        action_reasons=_action_reason_list(
            value.get("action_reasons", []),
            f"{field_name}.action_reasons",
        ),
        action_max_items=_optional_positive_int(
            value.get("action_max_items"),
            f"{field_name}.action_max_items",
        ),
        action_overdue_only=_bool(
            value.get("action_overdue_only", False),
            f"{field_name}.action_overdue_only",
        ),
        action_due_within_days=_optional_non_negative_int(
            value.get("action_due_within_days"),
            f"{field_name}.action_due_within_days",
        ),
    )
    _validate_delivery_action_config(config, field_name)
    return config


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


def _required_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if not normalized:
        raise ConfigError(f"{field_name} must be a non-empty string")
    return normalized


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


def _default_prefixed_string(value: Any, field_name: str, default: str) -> str:
    if value is None:
        return default
    return _required_string(value, field_name)


def _bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ConfigError(f"{field_name} must be true or false")


def _feed_source(value: Any, field_name: str) -> FeedSource:
    if not isinstance(value, str):
        raise ConfigError(
            f"{field_name} must be 'arxiv', 'crossref', 'pubmed', "
            "'semantic_scholar', or 'openalex'"
        )

    normalized = value.strip().lower()
    if normalized not in {
        "arxiv",
        "crossref",
        "pubmed",
        "semantic_scholar",
        "openalex",
    }:
        raise ConfigError(
            f"{field_name} must be 'arxiv', 'crossref', 'pubmed', "
            "'semantic_scholar', or 'openalex'"
        )
    if normalized == "arxiv":
        return "arxiv"
    if normalized == "crossref":
        return "crossref"
    if normalized == "pubmed":
        return "pubmed"
    if normalized == "semantic_scholar":
        return "semantic_scholar"
    return "openalex"


def _delivery_type(value: Any, field_name: str) -> DeliveryType:
    if not isinstance(value, str):
        raise ConfigError(
            f"{field_name} must be 'email', 'feishu_webhook', "
            "'wecom_webhook', 'slack_webhook', 'discord_webhook', "
            "or 'telegram_bot'"
        )

    normalized = value.strip().lower()
    if normalized not in {
        "email",
        "feishu_webhook",
        "wecom_webhook",
        "slack_webhook",
        "discord_webhook",
        "telegram_bot",
    }:
        raise ConfigError(
            f"{field_name} must be 'email', 'feishu_webhook', "
            "'wecom_webhook', 'slack_webhook', 'discord_webhook', "
            "or 'telegram_bot'"
        )
    if normalized == "email":
        return "email"
    if normalized == "feishu_webhook":
        return "feishu_webhook"
    if normalized == "wecom_webhook":
        return "wecom_webhook"
    if normalized == "slack_webhook":
        return "slack_webhook"
    if normalized == "discord_webhook":
        return "discord_webhook"
    return "telegram_bot"


def _delivery_target(value: Any, field_name: str) -> DeliveryTarget:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be 'digest' or 'per_feed'")

    normalized = value.strip().lower()
    if normalized not in {"digest", "per_feed"}:
        raise ConfigError(f"{field_name} must be 'digest' or 'per_feed'")
    if normalized == "digest":
        return "digest"
    return "per_feed"


def _delivery_focus_target(value: Any, field_name: str) -> DeliveryFocusTarget:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be 'digest' or 'separate'")

    normalized = value.strip().lower()
    if normalized not in {"digest", "separate"}:
        raise ConfigError(f"{field_name} must be 'digest' or 'separate'")
    if normalized == "digest":
        return "digest"
    return "separate"


def _delivery_action_target(value: Any, field_name: str) -> DeliveryActionTarget:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be 'digest' or 'separate'")

    normalized = value.strip().lower()
    if normalized not in {"digest", "separate"}:
        raise ConfigError(f"{field_name} must be 'digest' or 'separate'")
    if normalized == "digest":
        return "digest"
    return "separate"


def _validate_delivery_action_config(
    config: DeliveryConfig,
    field_name: str,
) -> None:
    if config.action_only and not config.include_actions:
        raise ConfigError(
            f"{field_name}.action_only cannot be true when "
            f"{field_name}.include_actions is false"
        )


def _action_status_list(value: Any, field_name: str) -> list[FeedbackStatus]:
    items = _string_list(value, field_name)
    statuses: list[FeedbackStatus] = []
    for item in items:
        statuses.append(_action_feedback_status_value(item, field_name))
    return statuses


def _action_reason_list(value: Any, field_name: str) -> list[ActionReason]:
    items = _string_list(value, field_name)
    reasons: list[ActionReason] = []
    for item in items:
        reasons.append(_action_reason_value(item, field_name))
    return reasons


def _focus_status_list(value: Any, field_name: str) -> list[FeedbackStatus]:
    items = _string_list(value, field_name)
    statuses: list[FeedbackStatus] = []
    for item in items:
        statuses.append(_focus_feedback_status_value(item, field_name))
    return statuses


def _focus_reason_list(value: Any, field_name: str) -> list[FocusReason]:
    items = _string_list(value, field_name)
    reasons: list[FocusReason] = []
    for item in items:
        reasons.append(_focus_reason_value(item, field_name))
    return reasons


def _focus_feedback_status_value(value: str, field_name: str) -> FeedbackStatus:
    normalized = value.strip().lower()
    if normalized not in {"star", "follow_up"}:
        raise ConfigError(
            f"{field_name} must contain only 'star' or 'follow_up'"
        )
    if normalized == "star":
        return "star"
    return "follow_up"


def _focus_reason_value(value: str, field_name: str) -> FocusReason:
    normalized = value.strip().lower()
    if normalized not in {"new_starred", "follow_up_resurfaced", "starred_momentum"}:
        raise ConfigError(
            f"{field_name} must contain only 'new_starred', "
            "'follow_up_resurfaced', or 'starred_momentum'"
        )
    if normalized == "new_starred":
        return "new_starred"
    if normalized == "follow_up_resurfaced":
        return "follow_up_resurfaced"
    return "starred_momentum"


def _action_feedback_status_value(value: str, field_name: str) -> FeedbackStatus:
    normalized = value.strip().lower()
    if normalized not in {"star", "follow_up", "reading"}:
        raise ConfigError(
            f"{field_name} must contain only 'star', 'follow_up', or 'reading'"
        )
    if normalized == "star":
        return "star"
    if normalized == "follow_up":
        return "follow_up"
    return "reading"


def _action_reason_value(value: str, field_name: str) -> ActionReason:
    normalized = value.strip().lower()
    if normalized not in {
        "overdue",
        "overdue_1d",
        "overdue_3d",
        "overdue_7d",
        "due_soon",
        "next_action_pending",
        "recurring_review",
    }:
        raise ConfigError(
            f"{field_name} must contain only 'overdue', 'overdue_1d', "
            "'overdue_3d', 'overdue_7d', 'due_soon', "
            "'next_action_pending', or 'recurring_review'"
        )
    if normalized == "overdue":
        return "overdue"
    if normalized == "overdue_1d":
        return "overdue_1d"
    if normalized == "overdue_3d":
        return "overdue_3d"
    if normalized == "overdue_7d":
        return "overdue_7d"
    if normalized == "due_soon":
        return "due_soon"
    if normalized == "recurring_review":
        return "recurring_review"
    return "next_action_pending"


def _analysis_provider(value: Any, field_name: str) -> AnalysisProvider:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be 'openai'")

    normalized = value.strip().lower()
    if normalized != "openai":
        raise ConfigError(f"{field_name} must be 'openai'")
    return "openai"


def _analysis_reasoning_effort(
    value: Any,
    field_name: str,
) -> AnalysisReasoningEffort:
    if not isinstance(value, str):
        raise ConfigError(
            f"{field_name} must be one of none, minimal, low, medium, high, xhigh"
        )

    normalized = value.strip().lower()
    if normalized not in {"none", "minimal", "low", "medium", "high", "xhigh"}:
        raise ConfigError(
            f"{field_name} must be one of none, minimal, low, medium, high, xhigh"
        )
    if normalized == "none":
        return "none"
    if normalized == "minimal":
        return "minimal"
    if normalized == "low":
        return "low"
    if normalized == "medium":
        return "medium"
    if normalized == "high":
        return "high"
    return "xhigh"


def _digest_template(value: Any, field_name: str) -> DigestTemplate:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be 'default' or 'zh_daily_brief'")

    normalized = value.strip().lower()
    if normalized not in {"default", "zh_daily_brief"}:
        raise ConfigError(f"{field_name} must be 'default' or 'zh_daily_brief'")
    if normalized == "default":
        return "default"
    return "zh_daily_brief"


def _sort_mode(value: Any, field_name: str) -> SortMode:
    if not isinstance(value, str):
        raise ConfigError(
            f"{field_name} must be 'relevance', 'published_at', or 'hybrid'"
        )

    normalized = value.strip().lower()
    if normalized not in {"relevance", "published_at", "hybrid"}:
        raise ConfigError(
            f"{field_name} must be 'relevance', 'published_at', or 'hybrid'"
        )
    if normalized == "relevance":
        return "relevance"
    if normalized == "published_at":
        return "published_at"
    return "hybrid"


def _optional_sort_mode(value: Any, field_name: str) -> SortMode | None:
    if value is None:
        return None
    return _sort_mode(value, field_name)


def _optional_positive_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, field_name)


def _optional_non_negative_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _non_negative_int(value, field_name)


def _positive_int(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be a positive integer") from exc
    if parsed <= 0:
        raise ConfigError(f"{field_name} must be a positive integer")
    return parsed


def _non_negative_int(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be a non-negative integer") from exc
    if parsed < 0:
        raise ConfigError(f"{field_name} must be a non-negative integer")
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
