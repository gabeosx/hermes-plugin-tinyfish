"""Hermes WebSearchProvider implementation for TinyFish."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any, cast

try:
    from agent.web_search_provider import WebSearchProvider as _HermesWebSearchProvider
except Exception:  # pragma: no cover - lets package import outside Hermes

    class _HermesWebSearchProvider:  # type: ignore[no-redef]
        pass


from . import rest_client
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


def _provider_env(name: str) -> str:
    """Read Hermes config-aware environment values when available."""

    try:
        from agent.web_search_provider import get_provider_env

        return str(get_provider_env(name) or "").strip()
    except Exception:
        return str(os.getenv(name, "") or "").strip()


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


def _discover_tinyfish_mcp_tools() -> None:
    """Register configured MCP tools for this process without prompting for OAuth."""

    if not _tinyfish_mcp_configured():
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

    def __init__(self, dispatch_tool: Callable[[str, dict[str, Any]], str] | None = None):
        self._dispatch_tool = dispatch_tool

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

    def _call_mcp(self, candidates: tuple[str, ...], args: dict[str, Any]) -> Any | None:
        tool_name = _first_registered(candidates)
        if tool_name is None:
            _discover_tinyfish_mcp_tools()
            tool_name = _first_registered(candidates)
        if tool_name is None:
            return None
        logger.debug("TinyFish using MCP tool %s", tool_name)
        return self._dispatch_registered_tool(tool_name, args)

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        try:
            from tools.interrupt import is_interrupted

            if is_interrupted():
                return {"success": False, "error": "Interrupted"}
        except Exception:
            pass

        mcp_error = ""
        try:
            payload = self._call_mcp(MCP_SEARCH_TOOLS, {"query": query})
            if payload is not None:
                return normalize_search_response(payload, limit=limit)
        except Exception as exc:  # noqa: BLE001 - REST fallback may still work
            mcp_error = str(exc)
            logger.info("TinyFish MCP search unavailable, trying REST fallback: %s", exc)

        api_key = _provider_env("TINYFISH_API_KEY")
        if not api_key:
            suffix = f" MCP error: {mcp_error}" if mcp_error else ""
            return {
                "success": False,
                "error": (
                    "TinyFish is not configured. Run `hermes tinyfish setup` "
                    "to configure MCP OAuth, or set TINYFISH_API_KEY for REST fallback." + suffix
                ),
            }

        try:
            raw = rest_client.search(query, api_key=api_key)
            return normalize_search_response(raw, limit=limit)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TinyFish REST search failed: %s", exc)
            detail = f"; MCP error: {mcp_error}" if mcp_error else ""
            return {"success": False, "error": f"TinyFish search failed: {exc}{detail}"}

    def extract(self, urls: list[str], **kwargs: Any) -> list[dict[str, Any]]:
        try:
            from tools.interrupt import is_interrupted

            if is_interrupted():
                return [{"url": url, "title": "", "content": "", "error": "Interrupted"} for url in urls]
        except Exception:
            pass

        output_format = str(kwargs.get("format") or kwargs.get("output_format") or "markdown")
        mcp_error = ""
        try:
            payload = self._call_mcp(
                MCP_FETCH_TOOLS,
                {"urls": urls, "format": output_format},
            )
            if payload is not None:
                return normalize_fetch_documents(payload, fallback_urls=urls)
        except Exception as exc:  # noqa: BLE001 - REST fallback may still work
            mcp_error = str(exc)
            logger.info("TinyFish MCP fetch unavailable, trying REST fallback: %s", exc)

        api_key = _provider_env("TINYFISH_API_KEY")
        if not api_key:
            suffix = f" MCP error: {mcp_error}" if mcp_error else ""
            return [
                {
                    "url": url,
                    "title": "",
                    "content": "",
                    "raw_content": "",
                    "error": (
                        "TinyFish is not configured. Run `hermes tinyfish setup` "
                        "to configure MCP OAuth, or set TINYFISH_API_KEY for REST fallback." + suffix
                    ),
                }
                for url in urls
            ]

        try:
            raw = rest_client.fetch(urls, api_key=api_key, output_format=output_format)
            return normalize_fetch_documents(raw, fallback_urls=urls)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TinyFish REST fetch failed: %s", exc)
            detail = f"; MCP error: {mcp_error}" if mcp_error else ""
            return [
                {
                    "url": url,
                    "title": "",
                    "content": "",
                    "raw_content": "",
                    "error": f"TinyFish fetch failed: {exc}{detail}",
                }
                for url in urls
            ]
