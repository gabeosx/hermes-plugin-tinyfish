"""Credit policy helpers for TinyFish credit-risking features."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .config import CreditFeature, CreditPolicy, browser_cloud_provider, credit_policy, normalize_feature

FEATURE_LABELS: dict[CreditFeature, str] = {
    "browser": "TinyFish Browser API",
}

INDEPENDENT_NOTICE = "This is an independent community plugin and is not affiliated with TinyFish or Hermes."
PRICING_NOTICE = "Pricing/free-use assumptions are based on current TinyFish documentation and may change."


def target_domain(target: str | None) -> str:
    if not target:
        return ""
    parsed = urlparse(target)
    if parsed.netloc:
        return parsed.netloc
    return target[:120]


def policy_message(feature: CreditFeature | str, policy: CreditPolicy | None = None) -> str:
    normalized = normalize_feature(str(feature))
    resolved = policy or credit_policy(normalized)
    return (
        f"{FEATURE_LABELS[normalized]} may consume TinyFish credits. "
        f"Current policy is '{resolved}'. Default policy is 'deny'. "
        f"{INDEPENDENT_NOTICE} {PRICING_NOTICE}"
    )


def block_message(feature: CreditFeature | str) -> str:
    normalized = normalize_feature(str(feature))
    return (
        f"BLOCKED: {policy_message(normalized, 'deny')} "
        "Run `hermes tinyfish credits set "
        f"{normalized.replace('_', '-')} request` to require approval per invocation, "
        "or set it to `allow` to permit calls without per-invocation approval."
    )


def approval_reason(feature: CreditFeature | str, operation: str, target: str | None = None) -> str:
    normalized = normalize_feature(str(feature))
    domain = target_domain(target)
    target_text = f" Target: {domain}." if domain else ""
    return (
        f"{FEATURE_LABELS[normalized]} operation '{operation}' may consume TinyFish credits."
        f"{target_text} {INDEPENDENT_NOTICE} {PRICING_NOTICE}"
    )


def request_credit_approval(
    feature: CreditFeature | str, operation: str, target: str | None = None
) -> tuple[bool, str]:
    normalized = normalize_feature(str(feature))
    policy = credit_policy(normalized)
    if policy == "deny":
        return False, block_message(normalized)
    if policy == "allow":
        return True, ""

    reason = approval_reason(normalized, operation, target)
    try:
        from tools.approval import request_tool_approval

        result = request_tool_approval(
            f"tinyfish_{normalized}",
            reason,
            rule_key=f"tinyfish:{normalized}:{operation}:{target_domain(target)}",
        )
    except Exception as exc:
        return False, (
            f"BLOCKED: {FEATURE_LABELS[normalized]} requires approval, but Hermes' "
            f"approval gate is unavailable ({exc})."
        )
    if result.get("approved"):
        return True, ""
    return False, str(result.get("message") or f"BLOCKED: approval required for {FEATURE_LABELS[normalized]}")


def _directive_for_feature(
    feature: CreditFeature, operation: str, target: str | None
) -> dict[str, str] | None:
    policy = credit_policy(feature)
    if policy == "deny":
        return {"action": "block", "message": block_message(feature)}
    if policy == "request":
        return {
            "action": "approve",
            "message": approval_reason(feature, operation, target),
            "rule_key": f"tinyfish:{feature}:{operation}:{target_domain(target)}",
        }
    return None


def pre_tool_call_policy(
    tool_name: str, args: dict[str, Any] | None = None, **_: Any
) -> dict[str, str] | None:
    """Hermes plugin hook for policy-gating TinyFish credit-risking tools."""

    params = args or {}

    if tool_name.startswith("browser_") and browser_cloud_provider() == "tinyfish":
        target = str(params.get("url") or params.get("target") or "")
        return _directive_for_feature("browser", tool_name, target)

    return None
