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
    credit_policy_summary,
    normalize_feature,
    normalize_policy,
    reset_credit_policies,
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
        help="Run credit-risking Agent/Browser checks according to TinyFish credit policies",
    )

    status = sub.add_parser("status", help="Print non-secret TinyFish configuration status")
    status.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    credits = sub.add_parser("credits", help="Inspect or update TinyFish credit-risking feature policies")
    credits_sub = credits.add_subparsers(dest="credits_command")
    credits_status = credits_sub.add_parser("status", help="Show TinyFish credit policy status")
    credits_status.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    credits_set = credits_sub.add_parser("set", help="Set a feature policy: deny, request, or allow")
    credits_set.add_argument("feature", choices=["agent", "browser", "profile-setup", "model-tools"])
    credits_set.add_argument("policy", choices=list(CREDIT_POLICIES))
    credits_sub.add_parser("reset", help="Reset all credit-risking features to deny")

    usage = sub.add_parser(
        "usage", help="Read TinyFish usage/quota information when the endpoint is available"
    )
    usage.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    agent = sub.add_parser("agent", help="Run or manage TinyFish Agent API automations")
    agent_sub = agent.add_subparsers(dest="agent_command")
    for name, help_text in (
        ("run", "Run a blocking TinyFish Agent automation"),
        ("run-async", "Start an async TinyFish Agent automation"),
    ):
        run = agent_sub.add_parser(name, help=help_text)
        run.add_argument("--url", required=True, help="Starting URL")
        run.add_argument("--goal", required=True, help="Natural-language goal")
        run.add_argument("--use-profile", action="store_true", help="Use a saved Browser Context Profile")
        run.add_argument("--profile-id", help="Specific Browser Context Profile ID")
        run.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    agent_status = agent_sub.add_parser("status", help="Fetch an Agent run by run_id")
    agent_status.add_argument("run_id")
    agent_status.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    agent_cancel = agent_sub.add_parser("cancel", help="Cancel an Agent run by run_id")
    agent_cancel.add_argument("run_id")
    agent_cancel.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    profiles = sub.add_parser("profiles", help="Manage TinyFish Browser Context Profiles")
    profiles_sub = profiles.add_subparsers(dest="profiles_command")
    profiles_list = profiles_sub.add_parser("list", help="List Browser Context Profiles")
    profiles_list.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    profiles_create = profiles_sub.add_parser("create", help="Create a Browser Context Profile")
    profiles_create.add_argument("--name", required=True)
    profiles_create.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    profiles_setup = profiles_sub.add_parser(
        "setup-session", help="Start a credit-risking profile setup browser"
    )
    profiles_setup.add_argument("profile_id")
    profiles_setup.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    profiles_save = profiles_sub.add_parser("save-setup", help="Save a profile setup session")
    profiles_save.add_argument("profile_id")
    profiles_save.add_argument("--session-id", required=True)
    profiles_save.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    profiles_cancel = profiles_sub.add_parser("cancel-setup", help="Cancel a profile setup session")
    profiles_cancel.add_argument("profile_id")
    profiles_cancel.add_argument("--session-id", required=True)
    profiles_cancel.add_argument("--json", action="store_true", help="Print machine-readable JSON")


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
    if command == "agent":
        return cmd_agent(args)
    if command == "profiles":
        return cmd_profiles(args)
    print("Usage: hermes tinyfish {setup,doctor,status,credits,usage,agent,profiles}", file=sys.stderr)
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
    print("Credit-risking TinyFish Agent, Browser, and Profile setup features remain policy-denied.")
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
        "credit_policy": credit_policy_summary(config),
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
    paid_ok = True
    if getattr(args, "live_paid", False):
        paid_ok = _run_live_paid_checks(status)
    if getattr(args, "json", False):
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        _print_status(status)
        if not status["ok"]:
            print()
            print("Recommended next step: run `hermes tinyfish setup`.")
    return 0 if status["ok"] and paid_ok else 1


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
            "TINYFISH_API_KEY is required for TinyFish REST Agent/Browser/Profile operations.",
            file=sys.stderr,
        )
        return None
    return api_key


def _run_live_paid_checks(status: dict[str, Any]) -> bool:
    browser_policy = credit_policy_summary().get("browser", "deny")
    agent_policy = credit_policy_summary().get("agent", "deny")
    if browser_policy == "deny" and agent_policy == "deny":
        status["live_paid_ok"] = False
        status["live_paid_error"] = "TinyFish Agent and Browser policies are deny."
        return False
    api_key = _get_env("TINYFISH_API_KEY")
    if not api_key:
        status["live_paid_ok"] = False
        status["live_paid_error"] = "TINYFISH_API_KEY is required for paid live checks."
        return False
    if browser_policy in {"request", "allow"}:
        approved, message = request_credit_approval("browser", "doctor-live-paid", "TinyFish Browser session")
        if not approved:
            status["live_paid_ok"] = False
            status["live_paid_error"] = message
            return False
        try:
            session = rest_client.create_browser_session(api_key=api_key)
            session_id = str(session.get("session_id") or session.get("id") or "")
            if session_id:
                rest_client.close_browser_session(session_id, api_key=api_key)
            status["live_paid_browser_ok"] = bool(session_id)
        except Exception as exc:  # noqa: BLE001
            status["live_paid_browser_ok"] = False
            status["live_paid_error"] = str(exc)
            return False
    status["live_paid_ok"] = True
    return True


def cmd_credits(args: argparse.Namespace) -> int:
    subcommand = getattr(args, "credits_command", None) or "status"
    config = _load_config()
    if subcommand == "status":
        payload: dict[str, Any] = {"credit_policy": credit_policy_summary(config)}
        if getattr(args, "json", False):
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("TinyFish credit policies")
            print(f"  notice: {INDEPENDENT_NOTICE}")
            print(f"  pricing: {PRICING_NOTICE}")
            for feature in CREDIT_FEATURES:
                print(f"  {feature}: {payload['credit_policy'][feature]}")
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
        print("Reset all TinyFish credit policies to deny.")
        return 0
    print("Usage: hermes tinyfish credits {status,set,reset}", file=sys.stderr)
    return 2


def cmd_usage(args: argparse.Namespace) -> int:
    api_key = _api_key_or_error()
    if not api_key:
        return 1
    try:
        payload = {"success": True, "data": rest_client.usage(api_key=api_key)}
    except Exception as exc:  # noqa: BLE001
        payload = {"success": False, "error": str(exc)}
    _print_json_or_text(payload, as_json=bool(getattr(args, "json", False)))
    return 0 if payload["success"] else 1


def cmd_agent(args: argparse.Namespace) -> int:
    command = getattr(args, "agent_command", None)
    api_key = _api_key_or_error()
    if not api_key:
        return 1
    try:
        if command in {"run", "run-async"}:
            approved, message = request_credit_approval("agent", command, getattr(args, "url", ""))
            if not approved:
                print(message, file=sys.stderr)
                return 1
            url = str(args.url)
            goal = str(args.goal)
            use_profile = bool(getattr(args, "use_profile", False)) or None
            profile_id = getattr(args, "profile_id", None)
            if command == "run":
                data = rest_client.agent_run(
                    api_key=api_key,
                    url=url,
                    goal=goal,
                    use_profile=use_profile,
                    profile_id=profile_id,
                )
            else:
                data = rest_client.agent_run_async(
                    api_key=api_key,
                    url=url,
                    goal=goal,
                    use_profile=use_profile,
                    profile_id=profile_id,
                )
        elif command == "status":
            data = rest_client.agent_status(str(args.run_id), api_key=api_key)
        elif command == "cancel":
            data = rest_client.agent_cancel(str(args.run_id), api_key=api_key)
        else:
            print("Usage: hermes tinyfish agent {run,run-async,status,cancel}", file=sys.stderr)
            return 2
    except Exception as exc:  # noqa: BLE001
        print(f"TinyFish Agent failed: {exc}", file=sys.stderr)
        return 1
    _print_json_or_text({"success": True, "data": data}, as_json=bool(getattr(args, "json", False)))
    return 0


def cmd_profiles(args: argparse.Namespace) -> int:
    command = getattr(args, "profiles_command", None)
    api_key = _api_key_or_error()
    if not api_key:
        return 1
    try:
        if command == "list":
            data = rest_client.profiles_list(api_key=api_key)
        elif command == "create":
            data = rest_client.profile_create(api_key=api_key, name=str(args.name))
        elif command == "setup-session":
            profile_id = str(args.profile_id)
            approved, message = request_credit_approval("profile_setup", command, profile_id)
            if not approved:
                print(message, file=sys.stderr)
                return 1
            data = rest_client.profile_setup_session(profile_id, api_key=api_key)
        elif command == "save-setup":
            data = rest_client.profile_save_setup(
                str(args.profile_id),
                str(args.session_id),
                api_key=api_key,
            )
        elif command == "cancel-setup":
            data = rest_client.profile_cancel_setup(
                str(args.profile_id),
                str(args.session_id),
                api_key=api_key,
            )
        else:
            print(
                "Usage: hermes tinyfish profiles {list,create,setup-session,save-setup,cancel-setup}",
                file=sys.stderr,
            )
            return 2
    except Exception as exc:  # noqa: BLE001
        print(f"TinyFish Profiles failed: {exc}", file=sys.stderr)
        return 1
    _print_json_or_text({"success": True, "data": data}, as_json=bool(getattr(args, "json", False)))
    return 0
