from __future__ import annotations

import pytest

from hermes_plugin_tinyfish.health import (
    TinyFishProviderHealth,
    classify_mcp_failure,
    mcp_failure_message,
)


@pytest.mark.parametrize(
    "value",
    [
        {"error": "invalid_grant"},
        '{"needs_reauth": true}',
        RuntimeError("Auth required; run `hermes mcp login tinyfish`"),
        "HTTP 401 Unauthorized",
        "refresh token was revoked",
    ],
)
def test_classify_explicit_reauthorization_failures(value: object) -> None:
    assert classify_mcp_failure(value) == "reauth_required"


class _GroupedFailure(RuntimeError):
    def __init__(self, *exceptions: BaseException) -> None:
        super().__init__("unhandled errors in a TaskGroup")
        self.exceptions = exceptions


def test_classification_unwraps_grouped_oauth_failure_on_python_310_compatible_path() -> None:
    grouped = _GroupedFailure(RuntimeError("State parameter mismatch"))

    assert classify_mcp_failure(grouped) == "reauth_required"


def test_grouped_generic_http_400_remains_unclassified() -> None:
    grouped = _GroupedFailure(RuntimeError("HTTP 400"))

    assert classify_mcp_failure(grouped) == "unknown"


def test_classification_follows_exception_cause_without_echoing_it() -> None:
    cause = RuntimeError("PKCE code challenge did not match the code verifier")
    wrapper = RuntimeError("connection failed")
    wrapper.__cause__ = cause

    assert classify_mcp_failure(wrapper) == "reauth_required"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Unknown tool: mcp__tinyfish__search", "mcp_unavailable"),
        ("MCP server is parked", "mcp_unavailable"),
        ("HTTP 503 Service Unavailable", "service_error"),
        ("HTTP 400", "unknown"),
    ],
)
def test_classification_is_conservative(value: str, expected: str) -> None:
    assert classify_mcp_failure(value) == expected


def test_failure_messages_are_actionable_and_do_not_echo_input() -> None:
    message = mcp_failure_message("reauth_required", mcp_configured=True)

    assert "hermes tinyfish reauth" in message
    assert "/reload-mcp" in message
    assert "invalid_grant" not in message


def test_health_snapshot_tracks_mcp_degradation_to_rest() -> None:
    health = TinyFishProviderHealth()

    health.record_mcp_failure("search", "reauth_required")
    health.record_rest_success("search", mcp_failure="reauth_required")

    snapshot = health.snapshot()
    assert snapshot.mcp_runtime_state == "reauth_required"
    assert snapshot.last_transport == "rest"
    assert snapshot.last_failure_kind == "reauth_required"
    assert snapshot.search_transport == "rest"
    assert snapshot.last_checked_at is not None
