from __future__ import annotations

from hermes_plugin_tinyfish.setup_cli import _apply_mcp_config, _apply_web_backend_config


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
