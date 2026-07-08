"""TinyFish provider plugin for Hermes Agent."""

from __future__ import annotations

from typing import Any

__version__ = "0.1.0"


def register(ctx: Any) -> None:
    """Register TinyFish providers, policy hooks, optional tools, and CLI commands."""

    from .browser_provider import TinyFishBrowserProvider
    from .config import credit_policy
    from .credit_policy import pre_tool_call_policy
    from .provider import TinyFishWebSearchProvider
    from .setup_cli import dispatch_tinyfish_cli, setup_tinyfish_cli
    from .tools import TOOLS, TOOLSET, _tool_available

    provider = TinyFishWebSearchProvider(dispatch_tool=getattr(ctx, "dispatch_tool", None))
    ctx.register_web_search_provider(provider)
    if hasattr(ctx, "register_browser_provider"):
        ctx.register_browser_provider(TinyFishBrowserProvider())
    if hasattr(ctx, "register_hook"):
        ctx.register_hook("pre_tool_call", pre_tool_call_policy)
    if hasattr(ctx, "register_tool") and credit_policy("model_tools") in {"request", "allow"}:
        for name, schema, handler in TOOLS:
            ctx.register_tool(
                name=name,
                toolset=TOOLSET,
                schema=schema,
                handler=handler,
                check_fn=_tool_available,
                description=str(schema.get("description") or ""),
            )
    ctx.register_cli_command(
        name="tinyfish",
        help="Configure and diagnose the TinyFish web provider",
        setup_fn=setup_tinyfish_cli,
        handler_fn=dispatch_tinyfish_cli,
        description="Configure TinyFish MCP OAuth, API-key fallback, and Hermes web backend routing.",
    )


def __getattr__(name: str) -> Any:
    if name == "TinyFishWebSearchProvider":
        from .provider import TinyFishWebSearchProvider

        return TinyFishWebSearchProvider
    if name == "TinyFishBrowserProvider":
        from .browser_provider import TinyFishBrowserProvider

        return TinyFishBrowserProvider
    raise AttributeError(name)


__all__ = ["TinyFishBrowserProvider", "TinyFishWebSearchProvider", "register"]
