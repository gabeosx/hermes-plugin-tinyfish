"""Optional model-callable TinyFish tools."""

from __future__ import annotations

import json
from typing import Any

from . import rest_client
from .config import credit_policy
from .credit_policy import INDEPENDENT_NOTICE, PRICING_NOTICE, block_message
from .provider import _provider_env

TOOLSET = "tinyfish"


def _tool_available() -> bool:
    return bool(
        _provider_env("TINYFISH_API_KEY")
        and credit_policy("model_tools") in {"request", "allow"}
        and credit_policy("agent") in {"request", "allow"}
    )


def _blocked() -> str | None:
    if not _provider_env("TINYFISH_API_KEY"):
        return "TINYFISH_API_KEY is required for TinyFish Agent tools."
    if credit_policy("model_tools") == "deny":
        return block_message("model_tools")
    if credit_policy("agent") == "deny":
        return block_message("agent")
    return None


AGENT_RUN_SCHEMA: dict[str, Any] = {
    "name": "tinyfish_agent_run",
    "description": (
        "Run a TinyFish Agent automation in a blocking call. This may consume TinyFish "
        "credits and is controlled by TinyFish credit policies. Use only when TinyFish "
        "should decide browser actions from a natural-language goal. "
        f"{INDEPENDENT_NOTICE} {PRICING_NOTICE}"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Starting URL for the automation."},
            "goal": {"type": "string", "description": "Natural-language goal to complete on the site."},
            "use_profile": {"type": "boolean", "description": "Use a saved Browser Context Profile."},
            "profile_id": {"type": "string", "description": "Specific Browser Context Profile ID."},
        },
        "required": ["url", "goal"],
    },
}

AGENT_RUN_ASYNC_SCHEMA: dict[str, Any] = {
    **AGENT_RUN_SCHEMA,
    "name": "tinyfish_agent_run_async",
    "description": (
        "Start a TinyFish Agent automation and return a run_id. This may consume "
        "TinyFish credits and is controlled by TinyFish credit policies. "
        f"{INDEPENDENT_NOTICE} {PRICING_NOTICE}"
    ),
}

AGENT_STATUS_SCHEMA: dict[str, Any] = {
    "name": "tinyfish_agent_status",
    "description": (
        "Fetch status/results for an existing TinyFish Agent run. Does not start new "
        "automation, but the tool is exposed only when TinyFish model tools are enabled."
    ),
    "parameters": {
        "type": "object",
        "properties": {"run_id": {"type": "string", "description": "TinyFish Agent run ID."}},
        "required": ["run_id"],
    },
}

AGENT_CANCEL_SCHEMA: dict[str, Any] = {
    "name": "tinyfish_agent_cancel",
    "description": "Cancel an existing TinyFish Agent run by run_id.",
    "parameters": {
        "type": "object",
        "properties": {"run_id": {"type": "string", "description": "TinyFish Agent run ID."}},
        "required": ["run_id"],
    },
}


def _agent_body_args(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": str(args.get("url") or ""),
        "goal": str(args.get("goal") or ""),
        "use_profile": args.get("use_profile") if isinstance(args.get("use_profile"), bool) else None,
        "profile_id": str(args.get("profile_id") or "") or None,
    }


def handle_agent_run(args: dict[str, Any], **_: Any) -> str:
    blocked = _blocked()
    if blocked:
        return json.dumps({"success": False, "error": blocked})
    body = _agent_body_args(args)
    if not body["url"] or not body["goal"]:
        return json.dumps({"success": False, "error": "url and goal are required."})
    try:
        result = rest_client.agent_run(api_key=_provider_env("TINYFISH_API_KEY"), **body)
        return json.dumps({"success": True, "data": result})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"success": False, "error": str(exc)})


def handle_agent_run_async(args: dict[str, Any], **_: Any) -> str:
    blocked = _blocked()
    if blocked:
        return json.dumps({"success": False, "error": blocked})
    body = _agent_body_args(args)
    if not body["url"] or not body["goal"]:
        return json.dumps({"success": False, "error": "url and goal are required."})
    try:
        result = rest_client.agent_run_async(api_key=_provider_env("TINYFISH_API_KEY"), **body)
        return json.dumps({"success": True, "data": result})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"success": False, "error": str(exc)})


def handle_agent_status(args: dict[str, Any], **_: Any) -> str:
    blocked = _blocked()
    if blocked:
        return json.dumps({"success": False, "error": blocked})
    run_id = str(args.get("run_id") or "")
    if not run_id:
        return json.dumps({"success": False, "error": "run_id is required."})
    try:
        result = rest_client.agent_status(run_id, api_key=_provider_env("TINYFISH_API_KEY"))
        return json.dumps({"success": True, "data": result})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"success": False, "error": str(exc)})


def handle_agent_cancel(args: dict[str, Any], **_: Any) -> str:
    blocked = _blocked()
    if blocked:
        return json.dumps({"success": False, "error": blocked})
    run_id = str(args.get("run_id") or "")
    if not run_id:
        return json.dumps({"success": False, "error": "run_id is required."})
    try:
        result = rest_client.agent_cancel(run_id, api_key=_provider_env("TINYFISH_API_KEY"))
        return json.dumps({"success": True, "data": result})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"success": False, "error": str(exc)})


TOOLS: tuple[tuple[str, dict[str, Any], Any], ...] = (
    ("tinyfish_agent_run", AGENT_RUN_SCHEMA, handle_agent_run),
    ("tinyfish_agent_run_async", AGENT_RUN_ASYNC_SCHEMA, handle_agent_run_async),
    ("tinyfish_agent_status", AGENT_STATUS_SCHEMA, handle_agent_status),
    ("tinyfish_agent_cancel", AGENT_CANCEL_SCHEMA, handle_agent_cancel),
)
