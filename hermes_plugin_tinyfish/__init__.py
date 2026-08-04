"""TinyFish provider plugin for Hermes Agent."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path
from typing import Any

_DISTRIBUTION_NAME = "hermes-plugin-tinyfish"
_PLUGIN_MANIFEST = Path(__file__).resolve().parents[1] / "plugin.yaml"


def _version_from_plugin_manifest(path: Path | None = None) -> str | None:
    path = _PLUGIN_MANIFEST if path is None else path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None

    for line in lines:
        if not line.startswith("version:"):
            continue
        value = line.partition(":")[2].split("#", 1)[0].strip().strip("'\"")
        return value or None
    return None


def _resolve_version() -> str:
    try:
        installed_version = metadata.version(_DISTRIBUTION_NAME)
    except Exception:  # Importing a directory plugin must not depend on package metadata.
        installed_version = ""
    if installed_version:
        return installed_version
    return _version_from_plugin_manifest() or "0+unknown"


__version__ = _resolve_version()


def register(ctx: Any) -> None:
    """Register TinyFish providers, lifecycle hooks, and CLI commands."""

    from .browser_provider import TinyFishBrowserProvider
    from .credit_policy import pre_tool_call_policy
    from .provider import TinyFishWebSearchProvider
    from .routing_context import TinyFishTurnContext
    from .setup_cli import dispatch_tinyfish_cli, setup_tinyfish_cli, tinyfish_status_command
    from .update_check import UpdateChecker, resolve_install_info

    provider = TinyFishWebSearchProvider(dispatch_tool=getattr(ctx, "dispatch_tool", None))
    update_checker = UpdateChecker(resolve_install_info(ctx, __version__))
    turn_context = TinyFishTurnContext(update_checker)
    ctx.register_web_search_provider(provider)
    if hasattr(ctx, "register_browser_provider"):
        ctx.register_browser_provider(TinyFishBrowserProvider())
    if hasattr(ctx, "register_hook"):
        ctx.register_hook("pre_tool_call", pre_tool_call_policy)
        ctx.register_hook("pre_llm_call", turn_context)
    update_checker.start()

    def _dispatch_cli(args: Any) -> int:
        exit_code = dispatch_tinyfish_cli(args, provider=provider, update_checker=update_checker)
        if exit_code:
            raise SystemExit(exit_code)
        return 0

    ctx.register_cli_command(
        name="tinyfish",
        help="Configure and diagnose the TinyFish web provider",
        setup_fn=setup_tinyfish_cli,
        handler_fn=_dispatch_cli,
        description="Configure TinyFish MCP OAuth, API-key fallback, and Hermes web backend routing.",
    )
    if hasattr(ctx, "register_command"):
        ctx.register_command(
            name="tinyfish-status",
            handler=lambda raw_args: tinyfish_status_command(
                raw_args,
                provider=provider,
                update_checker=update_checker,
            ),
            description="Show TinyFish provider status; pass 'live' to test Search and Fetch.",
            args_hint="[live]",
        )


def __getattr__(name: str) -> Any:
    if name == "TinyFishWebSearchProvider":
        from .provider import TinyFishWebSearchProvider

        return TinyFishWebSearchProvider
    if name == "TinyFishBrowserProvider":
        from .browser_provider import TinyFishBrowserProvider

        return TinyFishBrowserProvider
    raise AttributeError(name)


__all__ = ["TinyFishBrowserProvider", "TinyFishWebSearchProvider", "__version__", "register"]
