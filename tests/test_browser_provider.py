from __future__ import annotations

from hermes_plugin_tinyfish import rest_client
from hermes_plugin_tinyfish.browser_provider import TinyFishBrowserProvider


def test_browser_provider_unavailable_by_default(monkeypatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")

    assert TinyFishBrowserProvider().is_available() is False


def test_browser_provider_available_when_policy_enabled(monkeypatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr("hermes_plugin_tinyfish.browser_provider.credit_policy", lambda feature: "request")

    assert TinyFishBrowserProvider().is_available() is True


def test_browser_provider_create_session_shape(monkeypatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    monkeypatch.setattr("hermes_plugin_tinyfish.browser_provider.credit_policy", lambda feature: "allow")
    monkeypatch.setattr(
        rest_client,
        "create_browser_session",
        lambda **kwargs: {
            "session_id": "sess_123",
            "cdp_url": "wss://example.com/devtools",
            "base_url": "https://example.com",
        },
    )

    result = TinyFishBrowserProvider().create_session("task")

    assert result["bb_session_id"] == "sess_123"
    assert result["cdp_url"] == "wss://example.com/devtools"
    assert result["features"]["tinyfish"] is True


def test_browser_provider_close_session(monkeypatch) -> None:
    monkeypatch.setenv("TINYFISH_API_KEY", "tf_test")
    seen = {}

    def fake_close(session_id, *, api_key):
        seen["session_id"] = session_id
        seen["api_key"] = api_key
        return True

    monkeypatch.setattr(rest_client, "close_browser_session", fake_close)

    assert TinyFishBrowserProvider().close_session("sess_123") is True
    assert seen == {"session_id": "sess_123", "api_key": "tf_test"}
