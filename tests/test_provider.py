from __future__ import annotations

import json

import pytest

from hermes_plugin_tinyfish import provider as provider_mod
from hermes_plugin_tinyfish import rest_client
from hermes_plugin_tinyfish.provider import TinyFishWebSearchProvider
from tests.conftest import fake_registry


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch: pytest.MonkeyPatch):
    fake_registry.names.clear()
    fake_registry.responses.clear()
    fake_registry.calls.clear()
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)


def test_is_available_when_mcp_tool_registered() -> None:
    fake_registry.names.add("mcp__tinyfish__search")

    assert TinyFishWebSearchProvider().is_available() is True


def test_is_available_when_api_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")

    assert TinyFishWebSearchProvider().is_available() is True


def test_search_uses_mcp_before_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_registry.names.add("mcp__tinyfish__search")
    fake_registry.responses["mcp__tinyfish__search"] = json.dumps(
        {
            "result": {
                "results": [
                    {
                        "title": "MCP result",
                        "url": "https://example.com",
                        "snippet": "from MCP",
                    }
                ]
            }
        }
    )

    def fail_rest(*args, **kwargs):
        raise AssertionError("REST should not be called")

    monkeypatch.setattr(rest_client, "search", fail_rest)

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is True
    assert result["data"]["web"][0]["title"] == "MCP result"
    assert fake_registry.calls == [("mcp__tinyfish__search", {"query": "query"})]


def test_search_discovers_mcp_tools_before_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_registry.responses["mcp__tinyfish__search"] = json.dumps(
        {
            "results": [
                {
                    "title": "Discovered MCP result",
                    "url": "https://example.com",
                    "snippet": "from discovered MCP",
                }
            ]
        }
    )

    def discover() -> None:
        fake_registry.names.add("mcp__tinyfish__search")

    def fail_rest(*args, **kwargs):
        raise AssertionError("REST should not be called")

    monkeypatch.setattr(provider_mod, "_discover_tinyfish_mcp_tools", discover)
    monkeypatch.setattr(rest_client, "search", fail_rest)

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is True
    assert result["data"]["web"][0]["title"] == "Discovered MCP result"
    assert fake_registry.calls == [("mcp__tinyfish__search", {"query": "query"})]


def test_search_falls_back_to_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        rest_client,
        "search",
        lambda query, *, api_key: {
            "results": [
                {
                    "title": f"REST {query}",
                    "url": "https://example.com",
                    "snippet": api_key,
                }
            ]
        },
    )

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is True
    assert result["data"]["web"][0]["title"] == "REST query"


def test_extract_falls_back_to_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        rest_client,
        "fetch",
        lambda urls, *, api_key, output_format: {
            "results": [
                {
                    "url": urls[0],
                    "title": output_format,
                    "text": api_key,
                }
            ],
            "errors": [],
        },
    )

    docs = TinyFishWebSearchProvider().extract(["https://example.com"], format="markdown")

    assert docs[0]["title"] == "markdown"
    assert docs[0]["content"] == "tf_test"


def test_missing_configuration_returns_helpful_error() -> None:
    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is False
    assert "hermes tinyfish setup" in result["error"]
