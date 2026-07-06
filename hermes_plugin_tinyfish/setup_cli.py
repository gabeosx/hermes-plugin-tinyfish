"""CLI helpers for ``hermes tinyfish``."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .provider import (
    MCP_FETCH_TOOLS,
    MCP_SEARCH_TOOLS,
    TinyFishWebSearchProvider,
    _discover_tinyfish_mcp_tools,
)

TINYFISH_MCP_URL = "https://agent.tinyfish.ai/mcp"


def setup_tinyfish_cli(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="tinyfish_command")

    setup = sub.add_parser("setup", help="Configure TinyFish for Hermes web search/extract")
    setup.add_argument("--yes", "-y", action="store_true", help="Accept config changes without prompts")
    setup.add_argument("--api-key", help="Save TINYFISH_API_KEY as REST fallback")
    setup.add_argument("--skip-mcp", action="store_true", help="Do not configure TinyFish MCP OAuth")
    setup.add_argument("--skip-login", action="store_true", help="Do not run `hermes mcp login tinyfish`")
    setup.add_argument(
        "--login", action="store_true", help="Run `hermes mcp login tinyfish` after writing config"
    )
    setup.add_argument(
        "--no-web-backend", action="store_true", help="Do not set web.search_backend/extract_backend"
    )
    setup.add_argument("--live", action="store_true", help="Run live doctor checks after setup")

    doctor = sub.add_parser("doctor", help="Check TinyFish plugin configuration")
    doctor.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    doctor.add_argument("--live", action="store_true", help="Run a live search/fetch check")

    status = sub.add_parser("status", help="Print non-secret TinyFish configuration status")
    status.add_argument("--json", action="store_true", help="Print machine-readable JSON")


def dispatch_tinyfish_cli(args: argparse.Namespace) -> int:
    command = getattr(args, "tinyfish_command", None) or "status"
    if command == "setup":
        return cmd_setup(args)
    if command == "doctor":
        return cmd_doctor(args)
    if command == "status":
        return cmd_status(args)
    print("Usage: hermes tinyfish {setup,doctor,status}", file=sys.stderr)
    return 2


def _load_config() -> dict[str, Any]:
    from hermes_cli.config import load_config

    return dict(load_config() or {})


def _save_config(config: dict[str, Any]) -> None:
    from hermes_cli.config import save_config

    save_config(config)


def _get_env(name: str) -> str:
    try:
        from hermes_cli.config import get_env_value

        return str(get_env_value(name) or "").strip()
    except Exception:
        return str(os.getenv(name, "") or "").strip()


def _save_env(name: str, value: str) -> None:
    from hermes_cli.config import save_env_value

    save_env_value(name, value)


def _hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return Path(get_hermes_home())
    except Exception:
        return Path(os.getenv("HERMES_HOME") or Path.home() / ".hermes")


def _confirm(question: str, *, default: bool = True, assume_yes: bool = False) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        return default
    suffix = "Y/n" if default else "y/N"
    try:
        answer = input(f"{question} [{suffix}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not answer:
        return default
    return answer in {"y", "yes"}


def _prompt_secret(question: str) -> str:
    import getpass

    try:
        return getpass.getpass(question).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def _apply_mcp_config(config: dict[str, Any]) -> None:
    config.setdefault("mcp_servers", {})["tinyfish"] = {
        "url": TINYFISH_MCP_URL,
        "auth": "oauth",
        "tools": {
            "include": ["search", "fetch_content"],
            "resources": False,
            "prompts": False,
        },
    }


def _apply_web_backend_config(config: dict[str, Any]) -> None:
    web = config.setdefault("web", {})
    web["search_backend"] = "tinyfish"
    web["extract_backend"] = "tinyfish"
    if not web.get("backend"):
        web["backend"] = "tinyfish"


def cmd_setup(args: argparse.Namespace) -> int:
    config = _load_config()

    if not getattr(args, "skip_mcp", False):
        _apply_mcp_config(config)
        print("Configured TinyFish hosted MCP OAuth at https://agent.tinyfish.ai/mcp")

    if not getattr(args, "no_web_backend", False) and _confirm(
        "Set Hermes web.search_backend and web.extract_backend to tinyfish?",
        default=True,
        assume_yes=bool(getattr(args, "yes", False)),
    ):
        _apply_web_backend_config(config)
        print("Configured Hermes web backends to use TinyFish")

    _save_config(config)

    api_key = (getattr(args, "api_key", None) or "").strip()
    if (
        not api_key
        and not _get_env("TINYFISH_API_KEY")
        and sys.stdin.isatty()
        and _confirm(
            "Add TINYFISH_API_KEY as REST fallback now?",
            default=False,
            assume_yes=False,
        )
    ):
        api_key = _prompt_secret("TinyFish API key: ")
    if api_key:
        _save_env("TINYFISH_API_KEY", api_key)
        print("Saved TINYFISH_API_KEY fallback in Hermes .env")

    should_login = bool(getattr(args, "login", False))
    if not should_login and not getattr(args, "skip_login", False) and sys.stdin.isatty():
        should_login = _confirm("Run `hermes mcp login tinyfish` now?", default=True)
    if should_login:
        result = subprocess.run(["hermes", "mcp", "login", "tinyfish"], check=False)
        if result.returncode != 0:
            print("TinyFish MCP login did not complete. You can retry with `hermes mcp login tinyfish`.")

    if getattr(args, "live", False):
        doctor_args = argparse.Namespace(json=False, live=True)
        return cmd_doctor(doctor_args)

    print("Run `hermes tinyfish doctor --live` to verify the setup.")
    return 0


def _tool_names(*, discover_mcp: bool = False) -> set[str]:
    if discover_mcp:
        _discover_tinyfish_mcp_tools()
    try:
        from tools.registry import registry

        return set(registry.get_all_tool_names())
    except Exception:
        return set()


def collect_status(*, live: bool = False) -> dict[str, Any]:
    config = _load_config()
    mcp_cfg = (config.get("mcp_servers") or {}).get("tinyfish") or {}
    web_cfg = config.get("web") or {}
    names = _tool_names(discover_mcp=live)
    token_path = _hermes_home() / "mcp-tokens" / "tinyfish.json"
    api_key_configured = bool(_get_env("TINYFISH_API_KEY"))
    provider = TinyFishWebSearchProvider()

    checks: dict[str, Any] = {
        "plugin_loaded": True,
        "provider_available": provider.is_available(),
        "mcp_configured": bool(mcp_cfg.get("url") == TINYFISH_MCP_URL and mcp_cfg.get("auth") == "oauth"),
        "mcp_search_tool_registered": any(name in names for name in MCP_SEARCH_TOOLS),
        "mcp_fetch_tool_registered": any(name in names for name in MCP_FETCH_TOOLS),
        "mcp_token_cached": token_path.exists(),
        "api_key_fallback_configured": api_key_configured,
        "web_search_backend": web_cfg.get("search_backend") or web_cfg.get("backend") or "",
        "web_extract_backend": web_cfg.get("extract_backend") or web_cfg.get("backend") or "",
    }

    checks["web_backend_configured"] = (
        checks["web_search_backend"] == "tinyfish" and checks["web_extract_backend"] == "tinyfish"
    )

    if live:
        search = provider.search("TinyFish web agent", limit=1)
        checks["live_search_ok"] = bool(search.get("success") and search.get("data", {}).get("web"))
        fetch = provider.extract(["https://docs.tinyfish.ai/"], format="markdown")
        checks["live_fetch_ok"] = bool(fetch and not fetch[0].get("error"))

    checks["ok"] = bool(
        checks["web_backend_configured"]
        and (checks["mcp_configured"] or checks["api_key_fallback_configured"])
    )
    return checks


def _print_status(status: dict[str, Any]) -> None:
    print("TinyFish Hermes plugin status")
    for key in sorted(status):
        value = status[key]
        if isinstance(value, bool):
            value = "yes" if value else "no"
        print(f"  {key}: {value}")


def cmd_status(args: argparse.Namespace) -> int:
    status = collect_status(live=False)
    if getattr(args, "json", False):
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        _print_status(status)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    status = collect_status(live=bool(getattr(args, "live", False)))
    if getattr(args, "json", False):
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        _print_status(status)
        if not status["ok"]:
            print()
            print("Recommended next step: run `hermes tinyfish setup`.")
    return 0 if status["ok"] else 1
