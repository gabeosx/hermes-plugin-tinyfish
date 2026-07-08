from __future__ import annotations

from hermes_plugin_tinyfish import credit_policy as policy_mod
from hermes_plugin_tinyfish.config import credit_policy, reset_credit_policies, set_credit_policy
from hermes_plugin_tinyfish.credit_policy import pre_tool_call_policy


def test_credit_policy_defaults_to_deny() -> None:
    assert credit_policy("agent", {}) == "deny"


def test_set_credit_policy_normalizes_feature_name() -> None:
    config = {}

    set_credit_policy(config, "profile-setup", "request")

    assert credit_policy("profile_setup", config) == "request"


def test_reset_credit_policies() -> None:
    config = {"tinyfish": {"credit_policy": {"browser": "allow"}}}

    reset_credit_policies(config)

    assert credit_policy("browser", config) == "deny"


def test_pre_tool_policy_blocks_model_agent_by_default() -> None:
    directive = pre_tool_call_policy("tinyfish_agent_run", {"url": "https://example.com"})

    assert directive is not None
    assert directive["action"] == "block"
    assert "independent community plugin" in directive["message"]


def test_pre_tool_policy_requests_browser_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(policy_mod, "browser_cloud_provider", lambda: "tinyfish")
    monkeypatch.setattr(
        policy_mod, "credit_policy", lambda feature: "request" if feature == "browser" else "deny"
    )

    directive = pre_tool_call_policy("browser_navigate", {"url": "https://example.com/path"})

    assert directive is not None
    assert directive["action"] == "approve"
    assert "example.com" in directive["message"]
