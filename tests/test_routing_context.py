from __future__ import annotations

from typing import Any

import pytest

from hermes_plugin_tinyfish import routing_context as routing
from hermes_plugin_tinyfish.config import routing_context_enabled, update_check_enabled


def _mcp_config(**tinyfish: Any) -> dict[str, Any]:
    section = {
        "url": "https://agent.tinyfish.ai/mcp",
        "auth": "oauth",
        **tinyfish,
    }
    return {"mcp_servers": {"tinyfish": section}}


class _FakeUpdateChecker:
    def __init__(self, notices: list[str | None] | None = None) -> None:
        self.notices = list(notices or [])

    def notice_context(self) -> str | None:
        return self.notices.pop(0) if self.notices else None


def test_routing_context_defaults_on_only_for_configured_tinyfish_mcp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(routing, "load_config", _mcp_config)
    context = routing.TinyFishTurnContext(_FakeUpdateChecker())  # type: ignore[arg-type]

    first = context(user_message="ordinary search", conversation_history=[])

    assert first is not None
    assert routing.ROUTING_CONTEXT_MARKER == '<tinyfish-routing-context version="3">'
    assert routing.ROUTING_CONTEXT_MARKER in first["context"]
    assert "`web_search` or `web_extract`" in first["context"]
    assert "`search` or `fetch_content`" in first["context"]
    assert "research-paper" in first["context"]
    assert "ETag/Last-Modified" in first["context"]
    assert "silently dropping" in first["context"]
    assert "plain language" in first["context"]
    assert "rewrite operator defaults" in first["context"]


@pytest.mark.parametrize(
    "message",
    [
        {"role": "user", "content": "ordinary search", "api_content": routing.ROUTING_GUIDANCE},
        {"role": "user", "content": routing.ROUTING_GUIDANCE},
        {
            "role": "user",
            "content": [{"type": "text", "text": routing.ROUTING_GUIDANCE}],
        },
    ],
)
def test_existing_marker_suppresses_duplicate_routing_guidance(
    monkeypatch: pytest.MonkeyPatch,
    message: dict[str, Any],
) -> None:
    monkeypatch.setattr(routing, "load_config", _mcp_config)
    context = routing.TinyFishTurnContext(_FakeUpdateChecker())  # type: ignore[arg-type]

    assert context(conversation_history=[message]) is None


def test_routing_guidance_returns_after_compression_removes_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(routing, "load_config", _mcp_config)
    context = routing.TinyFishTurnContext(_FakeUpdateChecker())  # type: ignore[arg-type]

    result = context(
        conversation_history=[
            {"role": "user", "content": "compacted user turn"},
            {"role": "assistant", "content": "compacted answer"},
        ]
    )

    assert result is not None
    assert result["context"].count(routing.ROUTING_CONTEXT_MARKER) == 1


def test_v1_marker_does_not_suppress_v2_routing_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(routing, "load_config", _mcp_config)
    context = routing.TinyFishTurnContext(_FakeUpdateChecker())  # type: ignore[arg-type]

    result = context(
        conversation_history=[
            {
                "role": "user",
                "content": "search",
                "api_content": '<tinyfish-routing-context version="1">old guidance',
            }
        ]
    )

    assert result is not None
    assert routing.ROUTING_CONTEXT_MARKER in result["context"]


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"tinyfish": {"routing_context": False}, **_mcp_config()},
        {"mcp_servers": {"tinyfish": {"url": "https://example.com", "auth": "oauth"}}},
        {"mcp_servers": {"tinyfish": {"url": "https://agent.tinyfish.ai/mcp"}}},
    ],
)
def test_routing_context_is_absent_when_disabled_or_mcp_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, Any],
) -> None:
    monkeypatch.setattr(routing, "load_config", lambda: config)
    context = routing.TinyFishTurnContext(_FakeUpdateChecker())  # type: ignore[arg-type]

    assert context() is None


def test_routing_context_reloads_config_and_composes_one_time_update_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configs = iter([{}, _mcp_config()])
    monkeypatch.setattr(routing, "load_config", lambda: next(configs))
    checker = _FakeUpdateChecker(["Tell the user to update.", None])
    context = routing.TinyFishTurnContext(checker)  # type: ignore[arg-type]

    first = context(conversation_history=[])
    second = context(conversation_history=[])

    assert first == {"context": "Tell the user to update."}
    assert second is not None
    assert "TinyFish tool-routing guidance" in second["context"]
    assert "Tell the user to update" not in second["context"]


def test_update_notice_composes_without_reinjecting_existing_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(routing, "load_config", _mcp_config)
    checker = _FakeUpdateChecker(["Tell the user to update."])
    context = routing.TinyFishTurnContext(checker)  # type: ignore[arg-type]

    result = context(
        conversation_history=[{"role": "user", "content": "search", "api_content": routing.ROUTING_GUIDANCE}]
    )

    assert result == {"context": "Tell the user to update."}


def test_default_true_config_switches() -> None:
    assert routing_context_enabled({}) is True
    assert update_check_enabled({}) is True
    assert routing_context_enabled({"tinyfish": {"routing_context": False}}) is False
    assert update_check_enabled({"tinyfish": {"update_check": "off"}}) is False
