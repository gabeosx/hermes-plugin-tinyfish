"""TinyFish plugin configuration helpers."""

from __future__ import annotations

from typing import Any, Literal

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


def search_options(config: dict[str, Any] | None = None) -> SearchOptions:
    section = tinyfish_config(config).get("search") or {}
    if not isinstance(section, dict):
        return {}
    options: SearchOptions = {}
    for key in ("location", "language", "after_date", "before_date", "domain_type", "purpose"):
        value = section.get(key)
        if value not in (None, ""):
            options[key] = str(value)
    for key in ("recency_minutes", "page"):
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
        value = _int_option(section.get(key))
        if value is not None:
            options[key] = value
    for key in ("links", "image_links"):
        value = _bool_option(section.get(key))
        if value is not None:
            options[key] = value
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
