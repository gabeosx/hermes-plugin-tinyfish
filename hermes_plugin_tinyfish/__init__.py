"""TinyFish provider plugin for Hermes Agent."""

from __future__ import annotations

from typing import Any

__version__ = "0.1.0"


def register(ctx: Any) -> None:
    """Register the TinyFish web provider and CLI setup commands."""

    from .provider import TinyFishWebSearchProvider
    from .setup_cli import dispatch_tinyfish_cli, setup_tinyfish_cli

    provider = TinyFishWebSearchProvider(dispatch_tool=getattr(ctx, "dispatch_tool", None))
    ctx.register_web_search_provider(provider)
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
    raise AttributeError(name)


__all__ = ["TinyFishWebSearchProvider", "register"]
