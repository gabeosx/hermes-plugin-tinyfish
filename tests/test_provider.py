from __future__ import annotations

import contextlib
import json
import sys
import threading
import types
from concurrent.futures import ThreadPoolExecutor

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


def test_search_prefers_injected_public_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_registry.names.add("mcp__tinyfish__search")
    calls: list[tuple[str, dict[str, object]]] = []

    def dispatch(name: str, args: dict[str, object]) -> str:
        calls.append((name, args))
        return json.dumps({"results": [{"title": "Public dispatch", "url": "https://example.com"}]})

    monkeypatch.setattr(
        rest_client,
        "search",
        lambda *args, **kwargs: pytest.fail("REST should not be called"),
    )
    provider = TinyFishWebSearchProvider(dispatch_tool=dispatch)

    result = provider.search("query", limit=1)

    assert result["success"] is True
    assert result["data"]["web"][0]["title"] == "Public dispatch"
    assert calls == [("mcp__tinyfish__search", {"query": "query"})]
    assert fake_registry.calls == []


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

    def discover(candidates: tuple[str, ...] | None = None) -> None:
        del candidates
        fake_registry.names.add("mcp__tinyfish__search")

    def fail_rest(*args, **kwargs):
        raise AssertionError("REST should not be called")

    monkeypatch.setattr(provider_mod, "_discover_tinyfish_mcp_tools", discover)
    monkeypatch.setattr(rest_client, "search", fail_rest)

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is True
    assert result["data"]["web"][0]["title"] == "Discovered MCP result"
    assert fake_registry.calls == [("mcp__tinyfish__search", {"query": "query"})]


def test_concurrent_plugin_discovery_is_single_flight(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    discovery_started = threading.Event()
    release_discovery = threading.Event()
    waiter_observed = threading.Event()

    class ObservedLock:
        def __init__(self) -> None:
            self._lock = threading.Lock()

        def acquire(self, blocking: bool = True) -> bool:
            acquired = self._lock.acquire(blocking=blocking)
            if not blocking and not acquired:
                waiter_observed.set()
            return acquired

        def release(self) -> None:
            self._lock.release()

        def __enter__(self) -> ObservedLock:
            self.acquire()
            return self

        def __exit__(self, *args: object) -> None:
            self.release()

    def discover() -> None:
        nonlocal calls
        calls += 1
        discovery_started.set()
        assert release_discovery.wait(timeout=2)

    oauth_mod = types.ModuleType("tools.mcp_oauth")
    oauth_mod.suppress_interactive_oauth = contextlib.nullcontext
    mcp_tool_mod = types.ModuleType("tools.mcp_tool")
    mcp_tool_mod.discover_mcp_tools = discover
    monkeypatch.setitem(sys.modules, "tools.mcp_oauth", oauth_mod)
    monkeypatch.setitem(sys.modules, "tools.mcp_tool", mcp_tool_mod)
    monkeypatch.setattr(provider_mod, "_tinyfish_mcp_configured", lambda: True)
    monkeypatch.setattr(provider_mod, "_discovery_lock", ObservedLock())

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(provider_mod._discover_tinyfish_mcp_tools, provider_mod.MCP_SEARCH_TOOLS)
        assert discovery_started.wait(timeout=2)
        second = pool.submit(provider_mod._discover_tinyfish_mcp_tools, provider_mod.MCP_SEARCH_TOOLS)
        assert waiter_observed.wait(timeout=2)
        release_discovery.set()
        first.result(timeout=2)
        second.result(timeout=2)

    assert calls == 1


def test_fetch_can_skip_immediate_discovery_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    discovery_calls = 0

    def discover(candidates: tuple[str, ...] | None = None) -> None:
        nonlocal discovery_calls
        del candidates
        discovery_calls += 1

    monkeypatch.setattr(provider_mod, "_discover_tinyfish_mcp_tools", discover)
    provider = TinyFishWebSearchProvider()

    search = provider.search("query", limit=1, transport="mcp")
    fetch = provider.extract(
        ["https://example.com"],
        transport="mcp",
        _skip_mcp_discovery=True,
    )

    assert search["success"] is False
    assert fetch[0]["error"]
    assert discovery_calls == 1


def test_search_falls_back_to_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    seen: dict[str, object] = {}

    def fake_search(query, *, api_key, **kwargs):
        seen.update(kwargs)
        return {
            "results": [
                {
                    "title": f"REST {query}",
                    "url": "https://example.com",
                    "snippet": api_key,
                }
            ]
        }

    monkeypatch.setattr(
        rest_client,
        "search",
        fake_search,
    )

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is True
    assert result["data"]["web"][0]["title"] == "REST query"
    assert seen == {}


def test_search_passes_config_options_to_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        provider_mod,
        "search_options",
        lambda: {"location": "US", "language": "en", "page": 2},
    )
    seen: dict[str, object] = {}

    def fake_search(query, *, api_key, **kwargs):
        seen.update(kwargs)
        return {"results": [{"title": query, "url": "https://example.com", "snippet": api_key}]}

    monkeypatch.setattr(rest_client, "search", fake_search)

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is True
    assert seen == {"location": "US", "language": "en", "page": 2}


def test_extract_falls_back_to_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    seen: dict[str, object] = {}

    def fake_fetch(urls, *, api_key, output_format, **kwargs):
        seen.update(kwargs)
        return {
            "results": [
                {
                    "url": urls[0],
                    "title": output_format,
                    "text": api_key,
                }
            ],
            "errors": [],
        }

    monkeypatch.setattr(
        rest_client,
        "fetch",
        fake_fetch,
    )

    docs = TinyFishWebSearchProvider().extract(["https://example.com"], format="markdown")

    assert docs[0]["title"] == "markdown"
    assert docs[0]["content"] == "tf_test"
    assert seen == {}


def test_missing_configuration_returns_helpful_error() -> None:
    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is False
    assert "hermes tinyfish setup" in result["error"]


def test_explicit_oauth_failure_returns_reauth_guidance_without_raw_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_registry.names.add("mcp__tinyfish__search")
    fake_registry.responses["mcp__tinyfish__search"] = json.dumps(
        {"error": "invalid_grant: refresh token tf_super_secret was revoked"}
    )
    monkeypatch.setattr(provider_mod, "_tinyfish_mcp_configured", lambda: True)

    result = TinyFishWebSearchProvider().search("query", limit=1, transport="mcp")

    assert result["success"] is False
    assert "hermes tinyfish reauth" in result["error"]
    assert "/reload-mcp" in result["error"]
    assert "tf_super_secret" not in result["error"]
    assert "tf_super_secret" not in caplog.text


def test_generic_http_400_is_not_mislabeled_as_expired_oauth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_registry.names.add("mcp__tinyfish__search")
    fake_registry.responses["mcp__tinyfish__search"] = json.dumps({"error": "TinyFish returned HTTP 400"})
    monkeypatch.setattr(provider_mod, "_tinyfish_mcp_configured", lambda: True)
    provider = TinyFishWebSearchProvider()

    result = provider.search("query", limit=1, transport="mcp")

    assert result["success"] is False
    assert "unclassified reason" in result["error"]
    assert "authorization needs renewal" not in result["error"]
    assert provider.health.snapshot().last_failure_kind == "unknown"


def test_oauth_failure_degrades_to_rest_without_exposing_raw_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_registry.names.add("mcp__tinyfish__search")
    fake_registry.responses["mcp__tinyfish__search"] = json.dumps(
        {"error": "invalid_grant: tf_never_print_this"}
    )
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_rest_secret")
    monkeypatch.setattr(
        rest_client,
        "search",
        lambda query, *, api_key, **kwargs: {
            "results": [{"title": "REST result", "url": "https://example.com"}]
        },
    )
    provider = TinyFishWebSearchProvider()

    result = provider.search("query", limit=1)

    assert result["success"] is True
    assert result["data"]["web"][0]["title"] == "REST result"
    snapshot = provider.health.snapshot()
    assert snapshot.last_transport == "rest"
    assert snapshot.last_failure_kind == "reauth_required"
    assert "tf_never_print_this" not in caplog.text
    assert "tf_rest_secret" not in caplog.text


def test_mcp_only_never_uses_rest_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_registry.names.add("mcp__tinyfish__search")
    fake_registry.responses["mcp__tinyfish__search"] = json.dumps({"error": "authorization required"})
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        rest_client,
        "search",
        lambda *args, **kwargs: pytest.fail("REST must not run in MCP-only mode"),
    )
    monkeypatch.setattr(provider_mod, "_tinyfish_mcp_configured", lambda: True)

    result = TinyFishWebSearchProvider().search("query", limit=1, transport="mcp")

    assert result["success"] is False
    assert "reauth" in result["error"]


def test_rest_only_skips_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_registry.names.add("mcp__tinyfish__search")
    fake_registry.responses["mcp__tinyfish__search"] = pytest.fail
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        rest_client,
        "search",
        lambda query, *, api_key, **kwargs: {
            "results": [{"title": "REST only", "url": "https://example.com"}]
        },
    )
    provider = TinyFishWebSearchProvider()

    result = provider.search("query", limit=1, transport="rest")

    assert result["success"] is True
    assert fake_registry.calls == []
    assert provider.health.snapshot().last_transport == "rest"


def test_failed_lazy_discovery_still_falls_back_to_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        provider_mod,
        "_discover_tinyfish_mcp_tools",
        lambda candidates=None: (_ for _ in ()).throw(RuntimeError("discovery failed")),
    )
    monkeypatch.setattr(
        rest_client,
        "search",
        lambda query, *, api_key, **kwargs: {
            "results": [{"title": "REST recovery", "url": "https://example.com"}]
        },
    )

    result = TinyFishWebSearchProvider().search("query", limit=1)

    assert result["success"] is True
    assert result["data"]["web"][0]["title"] == "REST recovery"


def test_rest_failure_preserves_controlled_status_without_arbitrary_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr(
        rest_client,
        "search",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            rest_client.TinyFishRestError("TinyFish Search returned HTTP 402")
        ),
    )

    result = TinyFishWebSearchProvider().search("query", limit=1, transport="rest")

    assert result["success"] is False
    assert "HTTP 402" in result["error"]
