"""Non-secret TinyFish transport health and MCP failure classification."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

FailureKind = Literal["reauth_required", "mcp_unavailable", "service_error", "unknown"]
McpRuntimeState = Literal[
    "not_checked",
    "healthy",
    "reauth_required",
    "unavailable",
    "error",
]
Transport = Literal["auto", "mcp", "rest"]
UsedTransport = Literal["none", "mcp", "rest"]

VALID_TRANSPORTS = ("auto", "mcp", "rest")

_REAUTH_MARKERS = (
    "invalid_grant",
    "needs_reauth",
    "reauth_required",
    "state parameter mismatch",
    "pkce code challenge did not match",
    "auth required",
    "authentication required",
    "authorization required",
    "browser-based oauth authorization",
    "browser authorization required",
    "refresh token is invalid",
    "refresh token invalid",
    "refresh token is expired",
    "refresh token expired",
    "refresh token is revoked",
    "refresh token was invalid",
    "refresh token was expired",
    "refresh token was revoked",
    "refresh token revoked",
    "invalid refresh token",
    "expired refresh token",
    "revoked refresh token",
    "invalid or expired token",
    "token is invalid or expired",
    "http 401",
    "401 unauthorized",
    "www-authenticate",
    "hermes mcp login",
)
_UNAVAILABLE_MARKERS = (
    "unknown tool:",
    "tool registry is not available",
    "mcp tool is not registered",
    "mcp tools are not registered",
    "mcp server is parked",
    "mcp server parked",
)
_SERVICE_MARKERS = (
    "connection refused",
    "connection reset",
    "connection timed out",
    "connect timeout",
    "read timeout",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "http 500",
    "http 502",
    "http 503",
    "http 504",
)


def _failure_text(
    value: Any,
    *,
    _seen: set[int] | None = None,
    _depth: int = 0,
) -> str:
    """Return classification-only text; callers must never display it."""

    if _depth > 5:
        return type(value).__name__.lower()
    seen = _seen if _seen is not None else set()
    value_id = id(value)
    if value_id in seen:
        return type(value).__name__.lower()
    seen.add(value_id)

    if isinstance(value, BaseException):
        parts = [f"{type(value).__name__}: {value}"]

        # Python 3.11 ExceptionGroup instances expose ``exceptions``. Avoid a
        # direct BaseExceptionGroup reference so this package remains
        # importable on Python 3.10, while still classifying the underlying
        # OAuth error instead of the opaque "unhandled errors in a TaskGroup"
        # wrapper returned by Hermes/MCP.
        nested = getattr(value, "exceptions", ())
        if isinstance(nested, (list, tuple)):
            parts.extend(_failure_text(item, _seen=seen, _depth=_depth + 1) for item in nested[:16])

        cause = value.__cause__ or value.__context__
        if cause is not None:
            parts.append(_failure_text(cause, _seen=seen, _depth=_depth + 1))
        return " ".join(parts).lower()
    if isinstance(value, str):
        text = value
        try:
            decoded = json.loads(value)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        else:
            text = json.dumps(decoded, sort_keys=True, default=str)
        return text.lower()
    try:
        return json.dumps(value, sort_keys=True, default=str).lower()
    except (TypeError, ValueError):
        return type(value).__name__.lower()


def classify_mcp_failure(*values: Any) -> FailureKind:
    """Classify an MCP failure without exposing its untrusted details."""

    text = " ".join(_failure_text(value) for value in values if value is not None)
    if any(marker in text for marker in _REAUTH_MARKERS):
        return "reauth_required"
    if any(marker in text for marker in _UNAVAILABLE_MARKERS):
        return "mcp_unavailable"
    if any(marker in text for marker in _SERVICE_MARKERS):
        return "service_error"
    return "unknown"


def mcp_failure_message(kind: FailureKind, *, mcp_configured: bool) -> str:
    """Return a non-secret, actionable error for a classified MCP failure."""

    if not mcp_configured:
        return (
            "TinyFish MCP OAuth is not configured. Run `hermes tinyfish setup`, or set "
            "TINYFISH_API_KEY if you want REST fallback."
        )
    if kind == "reauth_required":
        return (
            "TinyFish MCP authorization needs renewal. From an interactive terminal run "
            "`hermes tinyfish reauth`. Then run `/reload-mcp` in Hermes or restart the process."
        )
    if kind == "mcp_unavailable":
        return (
            "TinyFish MCP tools are unavailable in this Hermes process. Run `/reload-mcp` or "
            "restart Hermes. If authorization is requested, run `hermes tinyfish reauth` first."
        )
    if kind == "service_error":
        return (
            "The TinyFish MCP service is temporarily unavailable. Retry the request or run "
            "`hermes tinyfish doctor --live --transport mcp`."
        )
    return (
        "TinyFish MCP failed for an unclassified reason. Run "
        "`hermes tinyfish doctor --live --transport mcp`; if it requests authorization, run "
        "`hermes tinyfish reauth` and then reload or restart Hermes."
    )


@dataclass(frozen=True)
class HealthSnapshot:
    """Immutable, non-secret view of provider transport health."""

    mcp_runtime_state: McpRuntimeState = "not_checked"
    last_transport: UsedTransport = "none"
    last_failure_kind: FailureKind | None = None
    last_checked_at: str | None = None
    search_transport: UsedTransport = "none"
    fetch_transport: UsedTransport = "none"

    def as_dict(self) -> dict[str, Any]:
        return {
            "mcp_runtime_state": self.mcp_runtime_state,
            "last_transport": self.last_transport,
            "last_failure_kind": self.last_failure_kind,
            "last_checked_at": self.last_checked_at,
            "search_transport": self.search_transport,
            "fetch_transport": self.fetch_transport,
        }


class TinyFishProviderHealth:
    """Thread-safe in-memory health shared by provider and command surfaces."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot = HealthSnapshot()

    def record_mcp_success(self, operation: Literal["search", "fetch"]) -> None:
        self._record(operation=operation, transport="mcp", state="healthy", failure=None)

    def record_mcp_failure(
        self,
        operation: Literal["search", "fetch"],
        kind: FailureKind,
    ) -> None:
        states: dict[FailureKind, McpRuntimeState] = {
            "reauth_required": "reauth_required",
            "mcp_unavailable": "unavailable",
            "service_error": "error",
            "unknown": "error",
        }
        self._record(operation=operation, transport="none", state=states[kind], failure=kind)

    def record_rest_success(
        self,
        operation: Literal["search", "fetch"],
        *,
        mcp_failure: FailureKind | None = None,
    ) -> None:
        with self._lock:
            current = self._snapshot
            search_transport = "rest" if operation == "search" else current.search_transport
            fetch_transport = "rest" if operation == "fetch" else current.fetch_transport
            self._snapshot = HealthSnapshot(
                mcp_runtime_state=current.mcp_runtime_state,
                last_transport="rest",
                last_failure_kind=mcp_failure,
                last_checked_at=_utc_now(),
                search_transport=search_transport,
                fetch_transport=fetch_transport,
            )

    def record_rest_failure(self, operation: Literal["search", "fetch"]) -> None:
        with self._lock:
            current = self._snapshot
            self._snapshot = HealthSnapshot(
                mcp_runtime_state=current.mcp_runtime_state,
                last_transport="rest",
                last_failure_kind=current.last_failure_kind,
                last_checked_at=_utc_now(),
                search_transport=current.search_transport,
                fetch_transport=current.fetch_transport,
            )

    def snapshot(self) -> HealthSnapshot:
        with self._lock:
            return self._snapshot

    def _record(
        self,
        *,
        operation: Literal["search", "fetch"],
        transport: UsedTransport,
        state: McpRuntimeState,
        failure: FailureKind | None,
    ) -> None:
        with self._lock:
            current = self._snapshot
            search_transport = transport if operation == "search" else current.search_transport
            fetch_transport = transport if operation == "fetch" else current.fetch_transport
            self._snapshot = HealthSnapshot(
                mcp_runtime_state=state,
                last_transport=transport,
                last_failure_kind=failure,
                last_checked_at=_utc_now(),
                search_transport=search_transport,
                fetch_transport=fetch_transport,
            )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
