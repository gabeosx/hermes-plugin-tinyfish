"""Hermes WebSearchProvider implementation for TinyFish."""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable
from typing import Any, Literal, cast

try:
    from agent.web_search_provider import WebSearchProvider as _HermesWebSearchProvider
except Exception:  # pragma: no cover - lets package import outside Hermes

    class _HermesWebSearchProvider:  # type: ignore[no-redef]
        pass


from . import rest_client
from .config import default_fetch_format, fetch_options, search_options
from .health import (
    FailureKind,
    TinyFishProviderHealth,
    Transport,
    classify_mcp_failure,
    mcp_failure_message,
)
from .normalize import TinyFishPayloadError, normalize_fetch_documents, normalize_search_response

logger = logging.getLogger(__name__)

MCP_SERVER_NAME = "tinyfish"
MCP_SEARCH_TOOLS = (
    "mcp__tinyfish__search",
    "mcp_tinyfish_search",
)
MCP_FETCH_TOOLS = (
    "mcp__tinyfish__fetch_content",
    "mcp__tinyfish__fetch",
    "mcp_tinyfish_fetch_content",
    "mcp_tinyfish_fetch",
)

# The compatibility shim below calls Hermes's process-global MCP discovery.
# Serialize plugin-triggered attempts so concurrent TinyFish provider calls do
# not amplify connection retries or OAuth refresh attempts in the same process.
# This is deliberately not a token lock and does not coordinate separate
# Hermes processes; the host still owns OAuth refresh serialization.
_discovery_lock = threading.Lock()


def _provider_env(name: str) -> str:
    """Read Hermes config-aware environment values when available."""

    try:
        from agent.web_search_provider import get_provider_env

        return str(get_provider_env(name) or "").strip()
    except Exception:
        return str(os.getenv(name, "") or "").strip()


def _safe_rest_failure(operation: str, exc: Exception) -> str:
    """Keep controlled REST diagnostics while suppressing arbitrary exceptions."""

    if isinstance(exc, rest_client.TinyFishRestError):
        return f"TinyFish REST {operation} failed: {exc}"
    return f"TinyFish REST {operation} failed ({type(exc).__name__})."


def _registry() -> Any | None:
    try:
        from tools.registry import registry

        return registry
    except Exception:
        return None


def _registered_tool_names() -> set[str]:
    registry = _registry()
    if registry is None:
        return set()
    try:
        return set(registry.get_all_tool_names())
    except Exception:
        pass
    try:
        return set(getattr(registry, "_tools", {}).keys())
    except Exception:
        return set()


def _tinyfish_mcp_configured() -> bool:
    try:
        from hermes_cli.config import load_config

        config = load_config() or {}
    except Exception:
        return False
    mcp_config = (config.get("mcp_servers") or {}).get(MCP_SERVER_NAME) or {}
    return bool(mcp_config.get("url") and mcp_config.get("auth") == "oauth")


def _discover_tinyfish_mcp_tools(
    candidates: tuple[str, ...] | None = None,
) -> None:
    """Register configured MCP tools once for concurrent plugin callers.

    A caller that arrives while another plugin-triggered discovery is running
    waits for that attempt and then returns without immediately retrying a
    failure. A later, independent provider call may try again. This preserves
    lazy MCP-first behavior while avoiding a same-process retry storm.
    """

    if not _tinyfish_mcp_configured():
        return

    # True single-flight behavior: waiters share the in-flight attempt even
    # when it fails, rather than acquiring the lock afterward and immediately
    # launching the same discovery again.
    if not _discovery_lock.acquire(blocking=False):
        with _discovery_lock:
            return

    try:
        # Hermes startup may have registered the requested tools between the
        # provider's first registry check and this lock acquisition.
        if candidates is not None:
            if _first_registered(candidates) is not None:
                return
        elif _first_registered(MCP_SEARCH_TOOLS) and _first_registered(MCP_FETCH_TOOLS):
            return

        try:
            from tools.mcp_oauth import suppress_interactive_oauth
        except Exception:
            suppress_interactive_oauth = None

        try:
            from tools.mcp_tool import discover_mcp_tools
        except Exception:
            return

        if suppress_interactive_oauth is None:
            discover_mcp_tools()
            return
        with suppress_interactive_oauth():
            discover_mcp_tools()
    finally:
        _discovery_lock.release()


def _first_registered(candidates: tuple[str, ...]) -> str | None:
    names = _registered_tool_names()
    for candidate in candidates:
        if candidate in names:
            return candidate
    return None


class TinyFishWebSearchProvider(_HermesWebSearchProvider):  # type: ignore[misc]
    """TinyFish search and extract provider.

    The provider prefers TinyFish's hosted MCP server because that path uses
    OAuth and Hermes' built-in MCP token storage. If MCP tools are unavailable,
    it falls back to direct REST calls using ``TINYFISH_API_KEY``.
    """

    def __init__(
        self,
        dispatch_tool: Callable[[str, dict[str, Any]], str] | None = None,
        health: TinyFishProviderHealth | None = None,
    ):
        self._dispatch_tool = dispatch_tool
        self.health = health or TinyFishProviderHealth()

    @property
    def name(self) -> str:
        return "tinyfish"

    @property
    def display_name(self) -> str:
        return "TinyFish"

    def is_available(self) -> bool:
        """Cheap availability check: registered MCP tools or API key only."""

        return bool(
            _first_registered(MCP_SEARCH_TOOLS)
            or _first_registered(MCP_FETCH_TOOLS)
            or _provider_env("TINYFISH_API_KEY")
        )

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return True

    def supports_crawl(self) -> bool:
        return False

    def get_setup_schema(self) -> dict[str, Any]:
        return {
            "name": "TinyFish",
            "badge": "free search/fetch",
            "tag": "OAuth MCP preferred; TINYFISH_API_KEY REST fallback.",
            "env_vars": [
                {
                    "key": "TINYFISH_API_KEY",
                    "prompt": "TinyFish API key (fallback when MCP OAuth is not configured)",
                    "url": "https://agent.tinyfish.ai/api-keys",
                }
            ],
        }

    def _dispatch_registered_tool(self, tool_name: str, args: dict[str, Any]) -> str:
        if self._dispatch_tool is not None:
            return self._dispatch_tool(tool_name, args)
        registry = _registry()
        if registry is None:
            raise TinyFishPayloadError("Hermes tool registry is not available")
        return cast(str, registry.dispatch(tool_name, args))

    def _call_mcp(
        self,
        candidates: tuple[str, ...],
        args: dict[str, Any],
        *,
        allow_discovery: bool = True,
    ) -> Any | None:
        tool_name = _first_registered(candidates)
        if tool_name is None and allow_discovery:
            _discover_tinyfish_mcp_tools(candidates)
            tool_name = _first_registered(candidates)
        if tool_name is None:
            return None
        logger.debug("TinyFish using MCP tool %s", tool_name)
        return self._dispatch_registered_tool(tool_name, args)

    def _record_mcp_failure(
        self,
        operation: Literal["search", "fetch"],
        *details: Any,
    ) -> FailureKind:
        kind = classify_mcp_failure(*details)
        self.health.record_mcp_failure(operation, kind)
        return kind

    def search(
        self,
        query: str,
        limit: int = 5,
        *,
        transport: Transport = "auto",
    ) -> dict[str, Any]:
        try:
            from tools.interrupt import is_interrupted

            if is_interrupted():
                return {"success": False, "error": "Interrupted"}
        except Exception:
            pass

        mcp_failure: FailureKind | None = None
        if transport != "rest":
            payload: Any | None = None
            try:
                payload = self._call_mcp(MCP_SEARCH_TOOLS, {"query": query})
                if payload is None:
                    mcp_failure = self._record_mcp_failure("search", "MCP tool is not registered")
                else:
                    result = normalize_search_response(payload, limit=limit)
                    self.health.record_mcp_success("search")
                    return result
            except Exception as exc:  # noqa: BLE001 - REST fallback may still work
                mcp_failure = self._record_mcp_failure("search", payload, exc)
                logger.info("TinyFish MCP search failed (category=%s)", mcp_failure)

            if transport == "mcp":
                return {
                    "success": False,
                    "error": mcp_failure_message(
                        mcp_failure or "unknown",
                        mcp_configured=_tinyfish_mcp_configured(),
                    ),
                }

        api_key = _provider_env("TINYFISH_API_KEY")
        if not api_key:
            if transport == "rest":
                error = "TINYFISH_API_KEY is required for TinyFish REST search."
            else:
                error = mcp_failure_message(
                    mcp_failure or "mcp_unavailable",
                    mcp_configured=_tinyfish_mcp_configured(),
                )
            return {
                "success": False,
                "error": error,
            }

        try:
            raw = rest_client.search(query, api_key=api_key, **search_options())
            result = normalize_search_response(raw, limit=limit)
            self.health.record_rest_success("search", mcp_failure=mcp_failure)
            if mcp_failure is not None:
                logger.warning("TinyFish search is using REST fallback (MCP category=%s)", mcp_failure)
            return result
        except Exception as exc:  # noqa: BLE001
            self.health.record_rest_failure("search")
            logger.warning("TinyFish REST search failed (%s)", type(exc).__name__)
            return {
                "success": False,
                "error": _safe_rest_failure("search", exc),
            }

    def extract(
        self,
        urls: list[str],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        try:
            from tools.interrupt import is_interrupted

            if is_interrupted():
                return [{"url": url, "title": "", "content": "", "error": "Interrupted"} for url in urls]
        except Exception:
            pass

        output_format = str(kwargs.get("format") or kwargs.get("output_format") or default_fetch_format())
        transport = cast(Transport, kwargs.get("transport", "auto"))
        allow_discovery = not bool(kwargs.get("_skip_mcp_discovery", False))
        mcp_failure: FailureKind | None = None
        if transport != "rest":
            payload: Any | None = None
            try:
                payload = self._call_mcp(
                    MCP_FETCH_TOOLS,
                    {"urls": urls, "format": output_format},
                    allow_discovery=allow_discovery,
                )
                if payload is None:
                    mcp_failure = self._record_mcp_failure("fetch", "MCP tool is not registered")
                else:
                    result = normalize_fetch_documents(payload, fallback_urls=urls)
                    self.health.record_mcp_success("fetch")
                    return result
            except Exception as exc:  # noqa: BLE001 - REST fallback may still work
                mcp_failure = self._record_mcp_failure("fetch", payload, exc)
                logger.info("TinyFish MCP fetch failed (category=%s)", mcp_failure)

            if transport == "mcp":
                error = mcp_failure_message(
                    mcp_failure or "unknown",
                    mcp_configured=_tinyfish_mcp_configured(),
                )
                return [
                    {
                        "url": url,
                        "title": "",
                        "content": "",
                        "raw_content": "",
                        "error": error,
                    }
                    for url in urls
                ]

        api_key = _provider_env("TINYFISH_API_KEY")
        if not api_key:
            if transport == "rest":
                error = "TINYFISH_API_KEY is required for TinyFish REST fetch."
            else:
                error = mcp_failure_message(
                    mcp_failure or "mcp_unavailable",
                    mcp_configured=_tinyfish_mcp_configured(),
                )
            return [
                {
                    "url": url,
                    "title": "",
                    "content": "",
                    "raw_content": "",
                    "error": error,
                }
                for url in urls
            ]

        try:
            raw = rest_client.fetch(
                urls,
                api_key=api_key,
                output_format=output_format,
                **fetch_options(),
            )
            result = normalize_fetch_documents(raw, fallback_urls=urls)
            self.health.record_rest_success("fetch", mcp_failure=mcp_failure)
            if mcp_failure is not None:
                logger.warning("TinyFish fetch is using REST fallback (MCP category=%s)", mcp_failure)
            return result
        except Exception as exc:  # noqa: BLE001
            self.health.record_rest_failure("fetch")
            logger.warning("TinyFish REST fetch failed (%s)", type(exc).__name__)
            return [
                {
                    "url": url,
                    "title": "",
                    "content": "",
                    "raw_content": "",
                    "error": _safe_rest_failure("fetch", exc),
                }
                for url in urls
            ]
