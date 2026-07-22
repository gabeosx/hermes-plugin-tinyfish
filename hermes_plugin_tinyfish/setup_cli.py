"""CLI helpers for ``hermes tinyfish``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

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
from .health import VALID_TRANSPORTS, TinyFishProviderHealth, Transport
from .provider import (
    MCP_FETCH_TOOLS,
    MCP_SEARCH_TOOLS,
    TinyFishWebSearchProvider,
)

TINYFISH_MCP_URL = "https://agent.tinyfish.ai/mcp"
MCP_LOGIN_COMMAND = ("hermes", "mcp", "login", "tinyfish")


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
        "--transport",
        choices=VALID_TRANSPORTS,
        default="auto",
        help="Live-check transport: auto (MCP-first), mcp, or rest",
    )
    doctor.add_argument(
        "--live-paid",
        action="store_true",
        help="Create and close a TinyFish Browser session according to its credit policy",
    )

    status = sub.add_parser("status", help="Print non-secret TinyFish configuration status")
    status.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    sub.add_parser("reauth", help="Renew TinyFish MCP OAuth in an interactive browser")

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


def dispatch_tinyfish_cli(
    args: argparse.Namespace,
    *,
    provider: TinyFishWebSearchProvider | None = None,
) -> int:
    command = getattr(args, "tinyfish_command", None) or "status"
    if command == "setup":
        return cmd_setup(args, provider=provider)
    if command == "doctor":
        return cmd_doctor(args, provider=provider)
    if command == "status":
        return cmd_status(args, provider=provider)
    if command == "reauth":
        return cmd_reauth(args)
    if command == "credits":
        return cmd_credits(args)
    if command == "usage":
        return cmd_usage(args)
    print("Usage: hermes tinyfish {setup,doctor,status,reauth,credits,usage}", file=sys.stderr)
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


def cmd_setup(
    args: argparse.Namespace,
    *,
    provider: TinyFishWebSearchProvider | None = None,
) -> int:
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
        if getattr(args, "live", False):
            print(
                "The interactive OAuth handoff replaces this setup process. After it exits, "
                "run `hermes tinyfish doctor --live --transport mcp` separately."
            )
        return _handoff_to_mcp_login()

    if getattr(args, "live", False):
        doctor_args = argparse.Namespace(json=False, live=True, live_paid=False, transport="auto")
        return cmd_doctor(doctor_args, provider=provider)

    print("Run `hermes tinyfish doctor --live` to verify the setup.")
    browser_policy = credit_policy_summary(config)["browser"]
    print(
        "Credit-risking TinyFish Browser sessions are governed by the browser policy "
        f"(current: {browser_policy}; default: deny)."
    )
    return 0


def cmd_reauth(args: argparse.Namespace) -> int:
    """Replace this process with Hermes's supported interactive MCP login."""

    del args
    return _handoff_to_mcp_login()


def _handoff_to_mcp_login() -> int:
    """Exec Hermes MCP login without leaving a competing parent process.

    A subprocess is unsafe here because the current Hermes process may already
    have initialized MCP OAuth state or reserved the cached callback port. An
    exec-style handoff retains the terminal but closes process-local resources
    before the supported core command starts.
    """

    print("Handing this terminal directly to `hermes mcp login tinyfish`.")
    print(
        "If another Hermes process shares this Hermes home (for example, a gateway), "
        "pause it and any supervisor or watchdog during OAuth maintenance."
    )
    print("The TinyFish plugin does not stop or restart external processes automatically.")
    print(
        "Complete one browser flow at a time. Do not manually edit OAuth URL characters; "
        "if terminal copying inserts line breaks, remove only whitespace."
    )
    print(
        "If Hermes prints another authorization URL before reporting success, stop rather "
        "than mixing callback URLs from different attempts."
    )
    print(
        "After authorization, reload or restart affected Hermes processes and verify with "
        "`hermes tinyfish doctor --live --transport mcp`."
    )
    print(
        "The MCP-only doctor is authoritative because some Hermes versions may return shell "
        "status 0 even when their login output reports failure."
    )
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        os.execvp(MCP_LOGIN_COMMAND[0], list(MCP_LOGIN_COMMAND))
    except OSError as exc:
        print(
            f"Could not hand off to the Hermes CLI ({type(exc).__name__}). Run "
            "`hermes mcp login tinyfish` from an interactive terminal.",
            file=sys.stderr,
        )
        return 1

    # os.execvp() does not return after a successful process replacement. Keep
    # this defensive fallback for unusual runtimes and test doubles.
    print("Hermes MCP login handoff returned unexpectedly.", file=sys.stderr)
    return 1


def _tool_names() -> set[str]:
    try:
        from tools.registry import registry

        return set(registry.get_all_tool_names())
    except Exception:
        return set()


def _health_status(provider: Any) -> dict[str, Any]:
    health = getattr(provider, "health", None)
    snapshot_fn = getattr(health, "snapshot", None)
    if callable(snapshot_fn):
        snapshot = snapshot_fn()
        as_dict = getattr(snapshot, "as_dict", None)
        if callable(as_dict):
            return dict(as_dict())
    return TinyFishProviderHealth().snapshot().as_dict()


def collect_status(
    *,
    live: bool = False,
    transport: Transport = "auto",
    provider: TinyFishWebSearchProvider | None = None,
) -> dict[str, Any]:
    config = _load_config()
    mcp_cfg = (config.get("mcp_servers") or {}).get("tinyfish") or {}
    web_cfg = config.get("web") or {}
    # Do not start a separate discovery pass merely to populate status. In a
    # live check, Search gets the one lazy-discovery opportunity and Fetch is
    # prevented from immediately repeating it if registration still failed.
    names = _tool_names()
    token_path = _hermes_home() / "mcp-tokens" / "tinyfish.json"
    api_key_configured = bool(_get_env("TINYFISH_API_KEY"))
    provider = provider or TinyFishWebSearchProvider()
    health = _health_status(provider)

    checks: dict[str, Any] = {
        "diagnostics_schema_version": 2,
        "plugin_loaded": True,
        "provider_available": provider.is_available(),
        "mcp_configured": bool(mcp_cfg.get("url") == TINYFISH_MCP_URL and mcp_cfg.get("auth") == "oauth"),
        "mcp_search_tool_registered": any(name in names for name in MCP_SEARCH_TOOLS),
        "mcp_fetch_tool_registered": any(name in names for name in MCP_FETCH_TOOLS),
        "mcp_token_cached": token_path.exists(),
        "mcp_token_cache_note": "presence only; OAuth validity is not checked",
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
        **health,
    }

    checks["web_backend_configured"] = (
        checks["web_search_backend"] == "tinyfish" and checks["web_extract_backend"] == "tinyfish"
    )

    if transport == "mcp":
        selected_transport_configured = checks["mcp_configured"]
    elif transport == "rest":
        selected_transport_configured = checks["api_key_fallback_configured"]
    else:
        selected_transport_configured = bool(
            checks["mcp_configured"] or checks["api_key_fallback_configured"]
        )
    configured_ok = bool(checks["web_backend_configured"] and selected_transport_configured)
    checks["ok"] = configured_ok

    if live:
        checks["live_transport_requested"] = transport
        try:
            search = provider.search("TinyFish web agent", limit=1, transport=transport)
            checks["live_search_ok"] = bool(search.get("success") and search.get("data", {}).get("web"))
            if not checks["live_search_ok"]:
                checks["live_search_error"] = str(
                    search.get("error") or "TinyFish Search returned no web results."
                )
        except Exception as exc:  # noqa: BLE001
            checks["live_search_ok"] = False
            checks["live_search_error"] = f"TinyFish Search check failed ({type(exc).__name__})."
        search_health = _health_status(provider)
        checks["live_search_transport"] = search_health["search_transport"]

        try:
            fetch = provider.extract(
                ["https://docs.tinyfish.ai/"],
                format="markdown",
                transport=transport,
                _skip_mcp_discovery=transport != "rest",
            )
            extracted_content = ""
            if fetch:
                extracted_content = str(fetch[0].get("content") or fetch[0].get("raw_content") or "").strip()
            checks["live_fetch_ok"] = bool(fetch and not fetch[0].get("error") and extracted_content)
            if not checks["live_fetch_ok"]:
                error = fetch[0].get("error") if fetch else None
                checks["live_fetch_error"] = str(error or "TinyFish Fetch returned no extracted content.")
        except Exception as exc:  # noqa: BLE001
            checks["live_fetch_ok"] = False
            checks["live_fetch_error"] = f"TinyFish Fetch check failed ({type(exc).__name__})."

        final_health = _health_status(provider)
        checks.update(final_health)
        checks["live_fetch_transport"] = final_health["fetch_transport"]

        # Report the registry state produced by the provider's single
        # discovery opportunity, without initiating another connection.
        names = _tool_names()
        checks["mcp_search_tool_registered"] = any(name in names for name in MCP_SEARCH_TOOLS)
        checks["mcp_fetch_tool_registered"] = any(name in names for name in MCP_FETCH_TOOLS)

        checks["ok"] = bool(configured_ok and checks["live_search_ok"] and checks["live_fetch_ok"])
    return checks


def _status_lines(status: dict[str, Any]) -> list[str]:
    lines = [
        "TinyFish Hermes plugin status",
        f"  notice: {INDEPENDENT_NOTICE}",
        f"  pricing: {PRICING_NOTICE}",
    ]
    for key in sorted(status):
        if key in {"independent_plugin_notice", "pricing_notice"}:
            continue
        value = status[key]
        if key == "credit_policy" and isinstance(value, dict):
            lines.append("  credit_policy:")
            for feature in CREDIT_FEATURES:
                lines.append(f"    {feature}: {value.get(feature, 'deny')}")
            continue
        if key == "retired_credit_policy_keys" and isinstance(value, list):
            ordered = [feature for feature in RETIRED_CREDIT_POLICY_KEYS if feature in value]
            lines.append(f"  retired_credit_policy_keys: {', '.join(ordered) if ordered else 'none'}")
            if ordered:
                lines.append(
                    "  WARNING: retired TinyFish Agent/Profile policy keys are ignored. "
                    "Run `hermes tinyfish credits reset` to remove them."
                )
            continue
        if isinstance(value, bool):
            value = "yes" if value else "no"
        if value is None:
            value = "none"
        lines.append(f"  {key}: {value}")
    return lines


def _print_status(status: dict[str, Any]) -> None:
    print("\n".join(_status_lines(status)))


def cmd_status(
    args: argparse.Namespace,
    *,
    provider: TinyFishWebSearchProvider | None = None,
) -> int:
    status = collect_status(live=False, provider=provider)
    if getattr(args, "json", False):
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        _print_status(status)
    return 0


def cmd_doctor(
    args: argparse.Namespace,
    *,
    provider: TinyFishWebSearchProvider | None = None,
) -> int:
    live = bool(getattr(args, "live", False))
    transport = str(getattr(args, "transport", "auto") or "auto")
    if transport not in VALID_TRANSPORTS:
        print(f"Unknown TinyFish diagnostic transport: {transport}", file=sys.stderr)
        return 2
    if not live and transport != "auto":
        print("`--transport` requires `--live`.", file=sys.stderr)
        return 2

    status = collect_status(
        live=live,
        transport=cast(Transport, transport),
        provider=provider,
    )
    if getattr(args, "live_paid", False):
        paid_ok = _run_live_paid_checks(status)
        status["ok"] = bool(status["ok"] and paid_ok)
    if getattr(args, "json", False):
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        _print_status(status)
        if not status["ok"]:
            print()
            if transport == "mcp":
                credential_path_configured = status.get("mcp_configured")
            elif transport == "rest":
                credential_path_configured = status.get("api_key_fallback_configured")
            else:
                credential_path_configured = bool(
                    status.get("mcp_configured") or status.get("api_key_fallback_configured")
                )
            configured = bool(status.get("web_backend_configured") and credential_path_configured)
            if not configured:
                if transport == "rest" and not status.get("api_key_fallback_configured"):
                    print(
                        "Recommended next step: configure TINYFISH_API_KEY, then retry the "
                        "REST-only live check."
                    )
                else:
                    print("Recommended next step: run `hermes tinyfish setup`.")
            elif not status.get("live_search_ok", True) or not status.get("live_fetch_ok", True):
                failure_kind = status.get("last_failure_kind")
                if failure_kind == "reauth_required":
                    print(
                        "Recommended next step: run `hermes tinyfish reauth` interactively, then "
                        "run `/reload-mcp` or restart Hermes."
                    )
                elif failure_kind == "mcp_unavailable":
                    print(
                        "Recommended next step: run `/reload-mcp` or restart Hermes; if prompted, "
                        "run `hermes tinyfish reauth` first."
                    )
                else:
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


def tinyfish_status_command(
    raw_args: str,
    *,
    provider: TinyFishWebSearchProvider,
) -> str:
    """Serve the in-session ``/tinyfish-status`` command."""

    option = (raw_args or "").strip().lower()
    if option not in {"", "live"}:
        return "Usage: /tinyfish-status [live]"
    status = collect_status(live=option == "live", transport="auto", provider=provider)
    return "\n".join(_status_lines(status))


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
