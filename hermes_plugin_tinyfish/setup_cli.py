"""CLI helpers for ``hermes tinyfish``."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import rest_client
from .config import (
    CREDIT_FEATURES,
    CREDIT_POLICIES,
    RETIRED_CREDIT_POLICY_KEYS,
    credit_policy_summary,
    normalize_feature,
    normalize_policy,
    reset_credit_policies,
    retired_credit_policy_keys,
    set_credit_policy,
)
from .credit_policy import INDEPENDENT_NOTICE, PRICING_NOTICE, request_credit_approval
from .provider import (
    MCP_FETCH_TOOLS,
    MCP_SEARCH_TOOLS,
    TinyFishWebSearchProvider,
    _discover_tinyfish_mcp_tools,
)

TINYFISH_MCP_URL = "https://agent.tinyfish.ai/mcp"


def setup_tinyfish_cli(parser: argparse.ArgumentParser) -> None:
    parser.description = (
        "Configure and diagnose the independent TinyFish Hermes plugin. "
        f"{INDEPENDENT_NOTICE} {PRICING_NOTICE}"
    )
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
    doctor.add_argument(
        "--live-paid",
        action="store_true",
        help="Create and close a TinyFish Browser session according to its credit policy",
    )

    status = sub.add_parser("status", help="Print non-secret TinyFish configuration status")
    status.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    credits = sub.add_parser("credits", help="Inspect or update TinyFish credit-risking feature policies")
    credits_sub = credits.add_subparsers(dest="credits_command")
    credits_status = credits_sub.add_parser("status", help="Show TinyFish credit policy status")
    credits_status.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    credits_set = credits_sub.add_parser("set", help="Set a feature policy: deny, request, or allow")
    credits_set.add_argument("feature", choices=list(CREDIT_FEATURES))
    credits_set.add_argument("policy", choices=list(CREDIT_POLICIES))
    credits_sub.add_parser("reset", help="Reset Browser to deny and remove retired Agent/Profile policy keys")

    usage = sub.add_parser("usage", help="Read TinyFish Fetch operation history")
    usage.add_argument("--json", action="store_true", help="Print machine-readable JSON")


def dispatch_tinyfish_cli(args: argparse.Namespace) -> int:
    command = getattr(args, "tinyfish_command", None) or "status"
    if command == "setup":
        return cmd_setup(args)
    if command == "doctor":
        return cmd_doctor(args)
    if command == "status":
        return cmd_status(args)
    if command == "credits":
        return cmd_credits(args)
    if command == "usage":
        return cmd_usage(args)
    print("Usage: hermes tinyfish {setup,doctor,status,credits,usage}", file=sys.stderr)
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


def _apply_default_credit_policy(config: dict[str, Any]) -> None:
    section = config.setdefault("tinyfish", {})
    if not isinstance(section, dict):
        section = {}
        config["tinyfish"] = section
    policies = section.setdefault("credit_policy", {})
    if not isinstance(policies, dict):
        policies = {}
        section["credit_policy"] = policies
    for feature in CREDIT_FEATURES:
        policies.setdefault(feature, "deny")


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

    _apply_default_credit_policy(config)
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
    browser_policy = credit_policy_summary(config)["browser"]
    print(
        "Credit-risking TinyFish Browser sessions are governed by the browser policy "
        f"(current: {browser_policy}; default: deny)."
    )
    return 0


def _tool_names(*, discover_mcp: bool = False) -> set[str]:
    try:
        if discover_mcp:
            _discover_tinyfish_mcp_tools()
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
        "credit_policy": credit_policy_summary(config),
        "retired_credit_policy_keys": retired_credit_policy_keys(config),
        "independent_plugin_notice": INDEPENDENT_NOTICE,
        "pricing_notice": PRICING_NOTICE,
        "web_search_backend": web_cfg.get("search_backend") or web_cfg.get("backend") or "",
        "web_extract_backend": web_cfg.get("extract_backend") or web_cfg.get("backend") or "",
        "browser_cloud_provider": (config.get("browser") or {}).get("cloud_provider", "")
        if isinstance(config.get("browser") or {}, dict)
        else "",
    }

    checks["web_backend_configured"] = (
        checks["web_search_backend"] == "tinyfish" and checks["web_extract_backend"] == "tinyfish"
    )

    configured_ok = bool(
        checks["web_backend_configured"]
        and (checks["mcp_configured"] or checks["api_key_fallback_configured"])
    )
    checks["ok"] = configured_ok

    if live:
        try:
            search = provider.search("TinyFish web agent", limit=1)
            checks["live_search_ok"] = bool(search.get("success") and search.get("data", {}).get("web"))
            if not checks["live_search_ok"]:
                checks["live_search_error"] = str(
                    search.get("error") or "TinyFish Search returned no web results."
                )
        except Exception as exc:  # noqa: BLE001
            checks["live_search_ok"] = False
            checks["live_search_error"] = f"{type(exc).__name__}: {exc}"

        try:
            fetch = provider.extract(["https://docs.tinyfish.ai/"], format="markdown")
            extracted_content = ""
            if fetch:
                extracted_content = str(fetch[0].get("content") or fetch[0].get("raw_content") or "").strip()
            checks["live_fetch_ok"] = bool(fetch and not fetch[0].get("error") and extracted_content)
            if not checks["live_fetch_ok"]:
                error = fetch[0].get("error") if fetch else None
                checks["live_fetch_error"] = str(error or "TinyFish Fetch returned no extracted content.")
        except Exception as exc:  # noqa: BLE001
            checks["live_fetch_ok"] = False
            checks["live_fetch_error"] = f"{type(exc).__name__}: {exc}"

        checks["ok"] = bool(configured_ok and checks["live_search_ok"] and checks["live_fetch_ok"])
    return checks


def _print_status(status: dict[str, Any]) -> None:
    print("TinyFish Hermes plugin status")
    print(f"  notice: {INDEPENDENT_NOTICE}")
    print(f"  pricing: {PRICING_NOTICE}")
    for key in sorted(status):
        if key in {"independent_plugin_notice", "pricing_notice"}:
            continue
        value = status[key]
        if key == "credit_policy" and isinstance(value, dict):
            print("  credit_policy:")
            for feature in CREDIT_FEATURES:
                print(f"    {feature}: {value.get(feature, 'deny')}")
            continue
        if key == "retired_credit_policy_keys" and isinstance(value, list):
            ordered = [feature for feature in RETIRED_CREDIT_POLICY_KEYS if feature in value]
            print(f"  retired_credit_policy_keys: {', '.join(ordered) if ordered else 'none'}")
            if ordered:
                print(
                    "  WARNING: retired TinyFish Agent/Profile policy keys are ignored. "
                    "Run `hermes tinyfish credits reset` to remove them."
                )
            continue
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
    if getattr(args, "live_paid", False):
        paid_ok = _run_live_paid_checks(status)
        status["ok"] = bool(status["ok"] and paid_ok)
    if getattr(args, "json", False):
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        _print_status(status)
        if not status["ok"]:
            print()
            configured = bool(
                status.get("web_backend_configured")
                and (status.get("mcp_configured") or status.get("api_key_fallback_configured"))
            )
            if not configured:
                print("Recommended next step: run `hermes tinyfish setup`.")
            elif not status.get("live_search_ok", True) or not status.get("live_fetch_ok", True):
                print(
                    "Recommended next step: retry the live checks and verify TinyFish MCP OAuth "
                    "or API credentials and service availability."
                )
            else:
                print(
                    "Recommended next step: review the Browser credit policy and API key, "
                    "then retry `hermes tinyfish doctor --live-paid`."
                )
    return 0 if status["ok"] else 1


def _print_json_or_text(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def _api_key_or_error() -> str | None:
    api_key = _get_env("TINYFISH_API_KEY")
    if not api_key:
        print(
            "TINYFISH_API_KEY is required for TinyFish Fetch usage and Browser operations.",
            file=sys.stderr,
        )
        return None
    return api_key


def _run_live_paid_checks(status: dict[str, Any]) -> bool:
    policy_status = status.get("credit_policy") or {}
    browser_policy = policy_status.get("browser", "deny") if isinstance(policy_status, dict) else "deny"
    if browser_policy == "deny":
        status["live_paid_ok"] = False
        status["live_paid_browser_ok"] = False
        status["live_paid_error"] = "TinyFish Browser policy is deny."
        return False

    approved, message = request_credit_approval("browser", "doctor-live-paid", "TinyFish Browser session")
    if not approved:
        status["live_paid_ok"] = False
        status["live_paid_browser_ok"] = False
        status["live_paid_error"] = message
        return False

    api_key = _get_env("TINYFISH_API_KEY")
    if not api_key:
        status["live_paid_ok"] = False
        status["live_paid_browser_ok"] = False
        status["live_paid_error"] = "TINYFISH_API_KEY is required for paid live checks."
        return False

    session_id = ""
    try:
        session = rest_client.create_browser_session(api_key=api_key)
        session_id = str(session.get("session_id") or session.get("id") or "").strip()
        if not session_id:
            status["live_paid_error"] = "TinyFish Browser did not return a valid session ID."
    except Exception as exc:  # noqa: BLE001
        status["live_paid_error"] = f"TinyFish Browser session creation failed ({type(exc).__name__})."

    cleanup_ok = False
    if session_id:
        try:
            cleanup_ok = bool(rest_client.close_browser_session(session_id, api_key=api_key))
        except Exception:  # noqa: BLE001
            cleanup_ok = False
        if not cleanup_ok:
            status["live_paid_error"] = "TinyFish Browser session cleanup failed."

    status["live_paid_browser_cleanup_ok"] = cleanup_ok
    status["live_paid_browser_ok"] = bool(session_id and cleanup_ok)
    if not status["live_paid_browser_ok"]:
        status["live_paid_ok"] = False
        return False
    status["live_paid_ok"] = True
    return True


def cmd_credits(args: argparse.Namespace) -> int:
    subcommand = getattr(args, "credits_command", None) or "status"
    config = _load_config()
    if subcommand == "status":
        payload: dict[str, Any] = {
            "credit_policy": credit_policy_summary(config),
            "retired_credit_policy_keys": retired_credit_policy_keys(config),
        }
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("TinyFish credit policies")
            print(f"  notice: {INDEPENDENT_NOTICE}")
            print(f"  pricing: {PRICING_NOTICE}")
            for feature in CREDIT_FEATURES:
                print(f"  {feature}: {payload['credit_policy'][feature]}")
            if payload["retired_credit_policy_keys"]:
                print(
                    "  WARNING: retired TinyFish Agent/Profile policy keys are ignored. "
                    "Run `hermes tinyfish credits reset` to remove them."
                )
        return 0
    if subcommand == "set":
        feature = normalize_feature(args.feature)
        policy = normalize_policy(args.policy)
        set_credit_policy(config, feature, policy)
        _save_config(config)
        print(f"Set TinyFish {feature} credit policy to {policy}.")
        return 0
    if subcommand == "reset":
        reset_credit_policies(config)
        _save_config(config)
        print("Reset TinyFish Browser credit policy to deny and removed retired policy keys.")
        return 0
    print("Usage: hermes tinyfish credits {status,set,reset}", file=sys.stderr)
    return 2


def cmd_usage(args: argparse.Namespace) -> int:
    api_key = _api_key_or_error()
    if not api_key:
        return 1
    try:
        payload = {
            "success": True,
            "surface": "fetch",
            "data": rest_client.fetch_usage(api_key=api_key),
        }
    except Exception as exc:  # noqa: BLE001
        payload = {"success": False, "surface": "fetch", "error": str(exc)}
    _print_json_or_text(payload, as_json=bool(getattr(args, "json", False)))
    return 0 if payload["success"] else 1
