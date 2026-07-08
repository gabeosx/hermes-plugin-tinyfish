from __future__ import annotations

from hermes_plugin_tinyfish.config import credit_policy_summary
from hermes_plugin_tinyfish.setup_cli import (
    _apply_default_credit_policy,
    _apply_mcp_config,
    _apply_web_backend_config,
)


def test_apply_mcp_config() -> None:
    config = {}

    _apply_mcp_config(config)

    assert config["mcp_servers"]["tinyfish"]["url"] == "https://agent.tinyfish.ai/mcp"
    assert config["mcp_servers"]["tinyfish"]["auth"] == "oauth"
    assert config["mcp_servers"]["tinyfish"]["tools"]["include"] == ["search", "fetch_content"]


def test_apply_web_backend_config_preserves_existing_shared_backend() -> None:
    config = {"web": {"backend": "tavily"}}

    _apply_web_backend_config(config)

    assert config["web"]["backend"] == "tavily"
    assert config["web"]["search_backend"] == "tinyfish"
    assert config["web"]["extract_backend"] == "tinyfish"


def test_apply_default_credit_policy_defaults_to_deny() -> None:
    config = {}

    _apply_default_credit_policy(config)

    assert credit_policy_summary(config) == {
        "agent": "deny",
        "browser": "deny",
        "profile_setup": "deny",
        "model_tools": "deny",
    }


def test_apply_default_credit_policy_preserves_existing_choice() -> None:
    config = {"tinyfish": {"credit_policy": {"browser": "request"}}}

    _apply_default_credit_policy(config)

    assert credit_policy_summary(config)["browser"] == "request"
    assert credit_policy_summary(config)["agent"] == "deny"
