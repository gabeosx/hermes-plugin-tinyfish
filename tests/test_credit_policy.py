from __future__ import annotations

import sys
import types

import pytest

from hermes_plugin_tinyfish import credit_policy as policy_mod
from hermes_plugin_tinyfish.config import (
    CREDIT_FEATURES,
    RETIRED_CREDIT_FEATURES,
    credit_policy,
    credit_policy_summary,
    reset_credit_policies,
    retired_credit_policy_keys,
    set_credit_policy,
)
from hermes_plugin_tinyfish.credit_policy import pre_tool_call_policy, request_credit_approval


def test_browser_is_the_only_credit_feature_and_defaults_to_deny() -> None:
    assert CREDIT_FEATURES == ("browser",)
    assert credit_policy("browser", {}) == "deny"
    assert credit_policy_summary({}) == {"browser": "deny"}


@pytest.mark.parametrize("feature", RETIRED_CREDIT_FEATURES)
def test_retired_credit_features_are_rejected(feature: str) -> None:
    with pytest.raises(ValueError, match="Unknown TinyFish credit feature"):
        credit_policy(feature, {})


def test_set_credit_policy_supports_only_browser() -> None:
    config: dict[str, object] = {}

    set_credit_policy(config, "browser", "request")

    assert credit_policy("browser", config) == "request"


def test_reset_credit_policies_removes_retired_keys() -> None:
    config = {
        "tinyfish": {
            "credit_policy": {
                "agent": "allow",
                "browser": "allow",
                "profile_setup": "request",
                "model_tools": "allow",
            }
        }
    }

    reset_credit_policies(config)

    assert config["tinyfish"]["credit_policy"] == {"browser": "deny"}


def test_retired_credit_policy_keys_detects_legacy_config_without_mutating() -> None:
    config = {
        "tinyfish": {
            "credit_policy": {
                "model_tools": "allow",
                "browser": "request",
                "agent": "deny",
            }
        }
    }

    assert retired_credit_policy_keys(config) == ["agent", "model_tools"]
    assert config["tinyfish"]["credit_policy"]["agent"] == "deny"


def test_retired_credit_policy_keys_handles_malformed_config() -> None:
    assert retired_credit_policy_keys({"tinyfish": {"credit_policy": "deny"}}) == []


def test_pre_tool_policy_ignores_removed_agent_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_mod, "browser_cloud_provider", lambda: "tinyfish")

    assert pre_tool_call_policy("tinyfish_agent_run", {"url": "https://example.com"}) is None


def test_pre_tool_policy_requests_browser_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_mod, "browser_cloud_provider", lambda: "tinyfish")
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "request")

    directive = pre_tool_call_policy("browser_navigate", {"url": "https://example.com/path"})

    assert directive is not None
    assert directive["action"] == "approve"
    assert "example.com" in directive["message"]


def test_pre_tool_policy_blocks_browser_when_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_mod, "browser_cloud_provider", lambda: "tinyfish")
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "deny")

    directive = pre_tool_call_policy("browser_open", {"target": "example.com"})

    assert directive is not None
    assert directive["action"] == "block"
    assert "policy is 'deny'" in directive["message"]
    assert "independent community plugin" in directive["message"]


def test_pre_tool_policy_allows_browser_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_mod, "browser_cloud_provider", lambda: "tinyfish")
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "allow")

    assert pre_tool_call_policy("browser_navigate", {"url": "https://example.com"}) is None


def test_pre_tool_policy_does_not_gate_other_browser_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy_mod, "browser_cloud_provider", lambda: "local")

    assert pre_tool_call_policy("browser_navigate", {"url": "https://example.com"}) is None


def test_request_credit_approval_honors_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "allow")

    assert request_credit_approval("browser", "create") == (True, "")


def test_request_credit_approval_honors_deny(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "deny")

    approved, message = request_credit_approval("browser", "create")

    assert approved is False
    assert message.startswith("BLOCKED:")


def test_request_credit_approval_uses_hermes_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "request")
    approval_mod = types.ModuleType("tools.approval")
    approval_mod.request_tool_approval = lambda *args, **kwargs: {"approved": True}
    monkeypatch.setitem(sys.modules, "tools.approval", approval_mod)

    assert request_credit_approval("browser", "create", "https://example.com/path") == (True, "")


def test_request_credit_approval_reports_gate_denial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_mod, "credit_policy", lambda feature: "request")
    approval_mod = types.ModuleType("tools.approval")
    approval_mod.request_tool_approval = lambda *args, **kwargs: {
        "approved": False,
        "message": "Approval denied by user.",
    }
    monkeypatch.setitem(sys.modules, "tools.approval", approval_mod)

    assert request_credit_approval("browser", "create") == (False, "Approval denied by user.")
