"""TinyFish plugin configuration helpers."""

from __future__ import annotations

from typing import Any, Literal

TINYFISH_MCP_URL = "https://agent.tinyfish.ai/mcp"

CreditFeature = Literal["browser"]
CreditPolicy = Literal["deny", "request", "allow"]

CREDIT_FEATURES: tuple[CreditFeature, ...] = ("browser",)
RETIRED_CREDIT_FEATURES: tuple[str, ...] = ("agent", "profile_setup", "model_tools")
# Compatibility alias for callers that describe these values as config keys.
RETIRED_CREDIT_POLICY_KEYS = RETIRED_CREDIT_FEATURES
CREDIT_POLICIES: tuple[CreditPolicy, ...] = ("deny", "request", "allow")

FEATURE_ALIASES: dict[str, CreditFeature] = {"browser": "browser"}


SearchOptions = dict[str, Any]
FetchOptions = dict[str, Any]


def load_config() -> dict[str, Any]:
    try:
        from hermes_cli.config import load_config as _load_config

        return dict(_load_config() or {})
    except Exception:
        return {}


def save_config(config: dict[str, Any]) -> None:
    from hermes_cli.config import save_config

    save_config(config)


def normalize_feature(value: str) -> CreditFeature:
    key = value.strip().lower().replace("_", "-")
    try:
        return FEATURE_ALIASES[key]
    except KeyError as exc:
        valid = ", ".join(sorted(FEATURE_ALIASES))
        raise ValueError(f"Unknown TinyFish credit feature '{value}'. Valid features: {valid}") from exc


def normalize_policy(value: Any) -> CreditPolicy:
    policy = str(value or "deny").strip().lower()
    if policy not in CREDIT_POLICIES:
        valid = ", ".join(CREDIT_POLICIES)
        raise ValueError(f"Unknown TinyFish credit policy '{value}'. Valid policies: {valid}")
    return policy


def tinyfish_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config() if config is None else config
    section = cfg.get("tinyfish") or {}
    return section if isinstance(section, dict) else {}


def routing_context_enabled(config: dict[str, Any] | None = None) -> bool:
    value = _bool_option(tinyfish_config(config).get("routing_context"))
    return True if value is None else value


def update_check_enabled(config: dict[str, Any] | None = None) -> bool:
    value = _bool_option(tinyfish_config(config).get("update_check"))
    return True if value is None else value


def credit_policy(feature: CreditFeature | str, config: dict[str, Any] | None = None) -> CreditPolicy:
    normalized = normalize_feature(str(feature))
    section = tinyfish_config(config)
    policies = section.get("credit_policy") or {}
    if not isinstance(policies, dict):
        return "deny"
    return normalize_policy(policies.get(normalized, "deny"))


def set_credit_policy(
    config: dict[str, Any], feature: CreditFeature | str, policy: CreditPolicy | str
) -> None:
    normalized_feature = normalize_feature(str(feature))
    normalized_policy = normalize_policy(policy)
    section = config.setdefault("tinyfish", {})
    if not isinstance(section, dict):
        section = {}
        config["tinyfish"] = section
    policies = section.setdefault("credit_policy", {})
    if not isinstance(policies, dict):
        policies = {}
        section["credit_policy"] = policies
    policies[normalized_feature] = normalized_policy


def reset_credit_policies(config: dict[str, Any]) -> None:
    section = config.setdefault("tinyfish", {})
    if not isinstance(section, dict):
        section = {}
        config["tinyfish"] = section
    # Replacing the mapping both restores the safe default and removes retired
    # Agent/Profile/model-tool policy keys left by pre-0.3 installations.
    section["credit_policy"] = {"browser": "deny"}


def credit_policy_summary(config: dict[str, Any] | None = None) -> dict[str, CreditPolicy]:
    return {feature: credit_policy(feature, config) for feature in CREDIT_FEATURES}


def retired_credit_policy_keys(config: dict[str, Any] | None = None) -> list[str]:
    """Return retired pre-0.3 policy keys without mutating user configuration."""

    policies = tinyfish_config(config).get("credit_policy") or {}
    if not isinstance(policies, dict):
        return []
    return [feature for feature in RETIRED_CREDIT_FEATURES if feature in policies]


def _int_option(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_option(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _string_list_option(value: Any) -> list[str] | None:
    if value in (None, ""):
        return None
    if not isinstance(value, (list, tuple)):
        return None
    items = [str(item).strip() for item in value if str(item).strip()]
    return items or None


def search_options(config: dict[str, Any] | None = None) -> SearchOptions:
    section = tinyfish_config(config).get("search") or {}
    if not isinstance(section, dict):
        return {}
    options: SearchOptions = {}
    for key in (
        "location",
        "language",
        "include_domains",
        "exclude_domains",
        "after_date",
        "before_date",
        "domain_type",
        "purpose",
    ):
        value = section.get(key)
        if value not in (None, ""):
            options[key] = str(value)
    for key in ("recency_minutes", "pub_year_min", "pub_year_max", "page"):
        value = _int_option(section.get(key))
        if value is not None:
            options[key] = value
    return options


def fetch_options(config: dict[str, Any] | None = None) -> FetchOptions:
    section = tinyfish_config(config).get("fetch") or {}
    if not isinstance(section, dict):
        return {}
    options: FetchOptions = {}
    for key in ("ttl", "per_url_timeout_ms"):
        int_value = _int_option(section.get(key))
        if int_value is not None:
            options[key] = int_value
    for key in ("links", "image_links", "include_etag_and_last_modified"):
        bool_value = _bool_option(section.get(key))
        if bool_value is not None:
            options[key] = bool_value
    for key in ("purpose", "if_none_match", "if_modified_since"):
        text_value = section.get(key)
        if text_value not in (None, ""):
            options[key] = str(text_value)
    for key in ("include_selectors", "exclude_selectors"):
        list_value = _string_list_option(section.get(key))
        if list_value is not None:
            options[key] = list_value
    return options


def default_fetch_format(config: dict[str, Any] | None = None) -> str:
    section = tinyfish_config(config).get("fetch") or {}
    if isinstance(section, dict) and section.get("format"):
        return str(section["format"])
    return "markdown"


def browser_cloud_provider(config: dict[str, Any] | None = None) -> str:
    cfg = load_config() if config is None else config
    section = cfg.get("browser") or {}
    if not isinstance(section, dict):
        return ""
    return str(section.get("cloud_provider") or "").strip().lower()
