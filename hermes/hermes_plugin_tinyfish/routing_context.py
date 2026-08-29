"""Context-bounded TinyFish tool-routing guidance for Hermes turns."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .config import TINYFISH_MCP_URL, load_config, routing_context_enabled
from .update_check import UpdateChecker

ROUTING_CONTEXT_MARKER = '<tinyfish-routing-context version="3">'
ROUTING_GUIDANCE = f"""{ROUTING_CONTEXT_MARKER}
TinyFish tool-routing guidance:
- For ordinary web discovery or reading a page, use Hermes `web_search` or `web_extract`; the TinyFish provider keeps those calls MCP-first and applies any operator-configured TinyFish defaults on either transport.
- When the request needs TinyFish-specific controls that the generic schemas cannot express—domain/date/language/location/purpose/pagination filters, news or research-paper modes, publication-year filters, selectors, output formats, link or image extraction, conditional ETag/Last-Modified validators, cache TTL, or per-URL timeouts—use the native `search` or `fetch_content` tool registered by the `tinyfish` MCP server. Use the exact names Hermes exposes, commonly `mcp__tinyfish__search` and `mcp__tinyfish__fetch_content`.
- Infer the choice from the user's plain language. Do not ask them to choose MCP versus the plugin, and do not rewrite operator defaults for one request. If a required native tool is unavailable, use the generic provider only when it can preserve the requested constraints; otherwise explain which control is unavailable rather than silently dropping it."""


def tinyfish_mcp_configured(config: dict[str, Any]) -> bool:
    servers = config.get("mcp_servers") or {}
    if not isinstance(servers, dict):
        return False
    tinyfish = servers.get("tinyfish") or {}
    return bool(
        isinstance(tinyfish, dict)
        and tinyfish.get("url") == TINYFISH_MCP_URL
        and tinyfish.get("auth") == "oauth"
    )


def _contains_routing_marker(value: object) -> bool:
    if isinstance(value, str):
        return ROUTING_CONTEXT_MARKER in value
    if isinstance(value, Mapping):
        return any(_contains_routing_marker(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_routing_marker(item) for item in value)
    return False


def routing_guidance_present(conversation_history: object) -> bool:
    """Return whether Hermes already carries this routing version in context."""

    if not isinstance(conversation_history, Sequence) or isinstance(
        conversation_history, (str, bytes, bytearray)
    ):
        return False
    for message in conversation_history:
        if not isinstance(message, Mapping):
            continue
        if _contains_routing_marker(message.get("api_content")):
            return True
        if _contains_routing_marker(message.get("content")):
            return True
    return False


class TinyFishTurnContext:
    """Compose once-per-active-context routing with a maintenance notice."""

    def __init__(self, update_checker: UpdateChecker) -> None:
        self.update_checker = update_checker

    def __call__(self, **kwargs: Any) -> dict[str, str] | None:
        config = load_config()
        context: list[str] = []
        routing_needed = not routing_guidance_present(kwargs.get("conversation_history"))
        if routing_context_enabled(config) and tinyfish_mcp_configured(config) and routing_needed:
            context.append(ROUTING_GUIDANCE)
        update_notice = self.update_checker.notice_context()
        if update_notice:
            context.append(update_notice)
        if not context:
            return None
        return {"context": "\n\n".join(context)}
