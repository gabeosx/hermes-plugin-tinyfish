from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import pytest

from hermes_plugin_tinyfish import setup_cli as cli
from hermes_plugin_tinyfish.config import credit_policy_summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    cli.setup_tinyfish_cli(parser)
    return parser


def _configured_config(*, browser_policy: str = "deny", retired: bool = False) -> dict[str, Any]:
    policies = {"browser": browser_policy}
    if retired:
        policies.update(
            {
                "agent": "allow",
                "profile_setup": "request",
                "model_tools": "allow",
            }
        )
    return {
        "mcp_servers": {"tinyfish": {"url": cli.TINYFISH_MCP_URL, "auth": "oauth"}},
        "web": {"search_backend": "tinyfish", "extract_backend": "tinyfish"},
        "tinyfish": {"credit_policy": policies},
    }


class _FakeProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.search_result: dict[str, Any] = {
            "success": True,
            "data": {"web": [{"url": "https://example.com"}]},
        }
        self.fetch_result: list[dict[str, Any]] = [{"content": "ok"}]
        self.search_exception: Exception | None = None
        self.fetch_exception: Exception | None = None

    def is_available(self) -> bool:
        return True

    def search(self, query: str, *, limit: int) -> dict[str, Any]:
        assert query
        assert limit == 1
        self.calls.append("search")
        if self.search_exception is not None:
            raise self.search_exception
        return self.search_result

    def extract(self, urls: list[str], *, format: str) -> list[dict[str, Any]]:
        assert urls == ["https://docs.tinyfish.ai/"]
        assert format == "markdown"
        self.calls.append("fetch")
        if self.fetch_exception is not None:
            raise self.fetch_exception
        return self.fetch_result


def _install_status_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    provider: _FakeProvider,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    installed_config = config or _configured_config()
    monkeypatch.setattr(cli, "_load_config", lambda: installed_config)
    monkeypatch.setattr(cli, "_get_env", lambda name: "tf_test" if name == "TINYFISH_API_KEY" else "")
    monkeypatch.setattr(cli, "_hermes_home", lambda: tmp_path)
    monkeypatch.setattr(cli, "_tool_names", lambda *, discover_mcp=False: set())
    monkeypatch.setattr(cli, "TinyFishWebSearchProvider", lambda: provider)
    return installed_config


def test_apply_mcp_config() -> None:
    config: dict[str, Any] = {}

    cli._apply_mcp_config(config)

    assert config["mcp_servers"]["tinyfish"]["url"] == "https://agent.tinyfish.ai/mcp"
    assert config["mcp_servers"]["tinyfish"]["auth"] == "oauth"
    assert config["mcp_servers"]["tinyfish"]["tools"]["include"] == [
        "search",
        "fetch_content",
    ]


def test_apply_web_backend_config_preserves_existing_shared_backend() -> None:
    config = {"web": {"backend": "tavily"}}

    cli._apply_web_backend_config(config)

    assert config["web"]["backend"] == "tavily"
    assert config["web"]["search_backend"] == "tinyfish"
    assert config["web"]["extract_backend"] == "tinyfish"


def test_apply_default_credit_policy_defaults_only_browser_to_deny() -> None:
    config: dict[str, Any] = {}

    cli._apply_default_credit_policy(config)

    assert config["tinyfish"]["credit_policy"] == {"browser": "deny"}
    assert credit_policy_summary(config) == {"browser": "deny"}


def test_apply_default_credit_policy_preserves_browser_and_retired_keys() -> None:
    config = _configured_config(browser_policy="request", retired=True)
    before = copy.deepcopy(config["tinyfish"]["credit_policy"])

    cli._apply_default_credit_policy(config)

    assert config["tinyfish"]["credit_policy"] == before
    assert credit_policy_summary(config) == {"browser": "request"}


def test_setup_configures_core_only_defaults_without_removing_retired_keys(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _configured_config(browser_policy="request", retired=True)
    config.pop("mcp_servers")
    config.pop("web")
    saved_configs: list[dict[str, Any]] = []
    saved_env: list[tuple[str, str]] = []
    monkeypatch.setattr(cli, "_load_config", lambda: config)
    monkeypatch.setattr(cli, "_save_config", lambda value: saved_configs.append(copy.deepcopy(value)))
    monkeypatch.setattr(cli, "_get_env", lambda name: "")
    monkeypatch.setattr(cli, "_save_env", lambda name, value: saved_env.append((name, value)))

    args = _parser().parse_args(["setup", "--yes", "--skip-login", "--api-key", "tf_secret"])
    result = cli.dispatch_tinyfish_cli(args)
    output = capsys.readouterr().out

    assert result == 0
    assert saved_configs[-1]["mcp_servers"]["tinyfish"]["tools"]["include"] == [
        "search",
        "fetch_content",
    ]
    assert saved_configs[-1]["web"] == {
        "search_backend": "tinyfish",
        "extract_backend": "tinyfish",
        "backend": "tinyfish",
    }
    assert saved_configs[-1]["tinyfish"]["credit_policy"] == {
        "browser": "request",
        "agent": "allow",
        "profile_setup": "request",
        "model_tools": "allow",
    }
    assert saved_env == [("TINYFISH_API_KEY", "tf_secret")]
    assert "browser policy (current: request; default: deny)" in output
    assert "Agent" not in output
    assert "tf_secret" not in output


def test_setup_live_delegates_to_authoritative_doctor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_load_config", lambda: {})
    monkeypatch.setattr(cli, "_save_config", lambda config: None)
    monkeypatch.setattr(cli, "_get_env", lambda name: "already-configured")
    received: list[argparse.Namespace] = []

    def doctor(args: argparse.Namespace) -> int:
        received.append(args)
        return 1

    monkeypatch.setattr(cli, "cmd_doctor", doctor)

    args = _parser().parse_args(["setup", "--yes", "--skip-mcp", "--skip-login", "--live"])

    assert cli.dispatch_tinyfish_cli(args) == 1
    assert len(received) == 1
    assert received[0].live is True
    assert received[0].json is False


@pytest.mark.parametrize(
    ("command", "handler_name"),
    [
        ("doctor", "cmd_doctor"),
        ("status", "cmd_status"),
        ("credits", "cmd_credits"),
        ("usage", "cmd_usage"),
    ],
)
def test_dispatch_routes_core_commands(
    monkeypatch: pytest.MonkeyPatch, command: str, handler_name: str
) -> None:
    received: list[argparse.Namespace] = []

    def handler(args: argparse.Namespace) -> int:
        received.append(args)
        return 7

    monkeypatch.setattr(cli, handler_name, handler)

    assert cli.dispatch_tinyfish_cli(argparse.Namespace(tinyfish_command=command)) == 7
    assert len(received) == 1


def test_dispatch_rejects_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    result = cli.dispatch_tinyfish_cli(argparse.Namespace(tinyfish_command="unknown"))

    assert result == 2
    assert "{setup,doctor,status,credits,usage}" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["agent", "profiles"])
def test_removed_top_level_commands_are_rejected(command: str) -> None:
    with pytest.raises(SystemExit) as exc_info:
        _parser().parse_args([command])

    assert exc_info.value.code == 2


@pytest.mark.parametrize("feature", ["agent", "profile-setup", "model-tools"])
def test_retired_credit_features_are_rejected(feature: str) -> None:
    with pytest.raises(SystemExit) as exc_info:
        _parser().parse_args(["credits", "set", feature, "deny"])

    assert exc_info.value.code == 2


def test_collect_status_always_reports_empty_retired_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    provider = _FakeProvider()
    config = _install_status_environment(monkeypatch, tmp_path, provider)
    before = copy.deepcopy(config)

    status = cli.collect_status()

    assert status["ok"] is True
    assert status["credit_policy"] == {"browser": "deny"}
    assert status["retired_credit_policy_keys"] == []
    assert config == before


def test_status_json_reports_retired_keys_without_mutating_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = _FakeProvider()
    config = _configured_config(retired=True)
    _install_status_environment(monkeypatch, tmp_path, provider, config)
    before = copy.deepcopy(config)

    result = cli.cmd_status(argparse.Namespace(json=True))
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["credit_policy"] == {"browser": "deny"}
    assert payload["retired_credit_policy_keys"] == [
        "agent",
        "profile_setup",
        "model_tools",
    ]
    assert config == before


def test_human_status_warns_that_retired_keys_are_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = _FakeProvider()
    _install_status_environment(monkeypatch, tmp_path, provider, _configured_config(retired=True))

    assert cli.cmd_status(argparse.Namespace(json=False)) == 0
    output = capsys.readouterr().out

    assert "retired_credit_policy_keys: agent, profile_setup, model_tools" in output
    assert "WARNING" in output
    assert "are ignored" in output
    assert "credits reset" in output


def test_live_doctor_runs_search_and_fetch_and_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = _FakeProvider()
    _install_status_environment(monkeypatch, tmp_path, provider)

    result = cli.cmd_doctor(argparse.Namespace(json=True, live=True, live_paid=False))
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert provider.calls == ["search", "fetch"]
    assert payload["live_search_ok"] is True
    assert payload["live_fetch_ok"] is True
    assert payload["ok"] is True


def test_live_doctor_runs_fetch_after_search_exception_and_fails_authoritatively(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = _FakeProvider()
    provider.search_exception = RuntimeError("search unavailable")
    _install_status_environment(monkeypatch, tmp_path, provider)

    result = cli.cmd_doctor(argparse.Namespace(json=True, live=True, live_paid=False))
    payload = json.loads(capsys.readouterr().out)

    assert result == 1
    assert provider.calls == ["search", "fetch"]
    assert payload["live_search_ok"] is False
    assert payload["live_fetch_ok"] is True
    assert payload["ok"] is False
    assert "search unavailable" in payload["live_search_error"]


def test_live_doctor_records_fetch_exception_and_recommends_retry_not_setup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = _FakeProvider()
    provider.fetch_exception = RuntimeError("fetch unavailable")
    _install_status_environment(monkeypatch, tmp_path, provider)

    result = cli.cmd_doctor(argparse.Namespace(json=False, live=True, live_paid=False))
    output = capsys.readouterr().out

    assert result == 1
    assert provider.calls == ["search", "fetch"]
    assert "live_fetch_ok: no" in output
    assert "retry the live checks" in output
    assert "Recommended next step: run `hermes tinyfish setup`" not in output


def test_live_doctor_rejects_fetch_result_without_extracted_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = _FakeProvider()
    provider.fetch_result = [{"content": "", "raw_content": ""}]
    _install_status_environment(monkeypatch, tmp_path, provider)

    result = cli.cmd_doctor(argparse.Namespace(json=True, live=True, live_paid=False))
    payload = json.loads(capsys.readouterr().out)

    assert result == 1
    assert payload["live_fetch_ok"] is False
    assert payload["live_fetch_error"] == "TinyFish Fetch returned no extracted content."
    assert payload["ok"] is False


def test_tool_discovery_failure_is_treated_as_no_registered_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_discovery() -> None:
        raise RuntimeError("discovery failed")

    monkeypatch.setattr(cli, "_discover_tinyfish_mcp_tools", fail_discovery)

    assert cli._tool_names(discover_mcp=True) == set()


def test_live_paid_refuses_denied_browser_without_approval_or_api_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "request_credit_approval",
        lambda *args, **kwargs: pytest.fail("approval must not be requested"),
    )
    monkeypatch.setattr(
        cli.rest_client,
        "create_browser_session",
        lambda **kwargs: pytest.fail("Browser must not be called"),
    )
    status: dict[str, Any] = {"credit_policy": {"browser": "deny"}}

    assert cli._run_live_paid_checks(status) is False
    assert status["live_paid_ok"] is False
    assert status["live_paid_browser_ok"] is False
    assert status["live_paid_error"] == "TinyFish Browser policy is deny."


def test_live_paid_honors_request_approval_denial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "request_credit_approval", lambda *args: (False, "not approved"))
    monkeypatch.setattr(
        cli.rest_client,
        "create_browser_session",
        lambda **kwargs: pytest.fail("Browser must not be called"),
    )
    status: dict[str, Any] = {"credit_policy": {"browser": "request"}}

    assert cli._run_live_paid_checks(status) is False
    assert status["live_paid_error"] == "not approved"


def test_live_paid_requires_api_key_after_approval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "request_credit_approval", lambda *args: (True, ""))
    monkeypatch.setattr(cli, "_get_env", lambda name: "")
    monkeypatch.setattr(
        cli.rest_client,
        "create_browser_session",
        lambda **kwargs: pytest.fail("Browser must not be called"),
    )
    status: dict[str, Any] = {"credit_policy": {"browser": "request"}}

    assert cli._run_live_paid_checks(status) is False
    assert status["live_paid_error"] == "TINYFISH_API_KEY is required for paid live checks."


def test_live_paid_creates_and_always_closes_browser_without_exposing_session_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[tuple[str, str]] = []
    monkeypatch.setattr(cli, "request_credit_approval", lambda *args: (True, ""))
    monkeypatch.setattr(cli, "_get_env", lambda name: "tf_secret")
    monkeypatch.setattr(
        cli.rest_client,
        "create_browser_session",
        lambda **kwargs: {
            "session_id": "session-secret",
            "cdp_url": "wss://signed-secret.example",
        },
    )

    def close(session_id: str, *, api_key: str) -> bool:
        closed.append((session_id, api_key))
        return True

    monkeypatch.setattr(cli.rest_client, "close_browser_session", close)
    status: dict[str, Any] = {"credit_policy": {"browser": "allow"}}

    assert cli._run_live_paid_checks(status) is True
    assert closed == [("session-secret", "tf_secret")]
    assert status["live_paid_browser_cleanup_ok"] is True
    assert status["live_paid_browser_ok"] is True
    assert status["live_paid_ok"] is True
    serialized = json.dumps(status)
    assert "session-secret" not in serialized
    assert "signed-secret" not in serialized
    assert "tf_secret" not in serialized


@pytest.mark.parametrize("cleanup_result", [False, RuntimeError("close failed")])
def test_live_paid_cleanup_failure_fails_diagnostic(
    monkeypatch: pytest.MonkeyPatch, cleanup_result: bool | Exception
) -> None:
    monkeypatch.setattr(cli, "request_credit_approval", lambda *args: (True, ""))
    monkeypatch.setattr(cli, "_get_env", lambda name: "tf_secret")
    monkeypatch.setattr(
        cli.rest_client,
        "create_browser_session",
        lambda **kwargs: {"session_id": "session-id"},
    )

    def close(session_id: str, *, api_key: str) -> bool:
        if isinstance(cleanup_result, Exception):
            raise cleanup_result
        return cleanup_result

    monkeypatch.setattr(cli.rest_client, "close_browser_session", close)
    status: dict[str, Any] = {"credit_policy": {"browser": "allow"}}

    assert cli._run_live_paid_checks(status) is False
    assert status["live_paid_browser_cleanup_ok"] is False
    assert status["live_paid_browser_ok"] is False
    assert status["live_paid_ok"] is False
    assert status["live_paid_error"] == "TinyFish Browser session cleanup failed."


def test_live_paid_creation_failure_does_not_expose_exception_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "request_credit_approval", lambda *args: (True, ""))
    monkeypatch.setattr(cli, "_get_env", lambda name: "tf_secret")

    def fail_create(**kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("cdp_url=wss://signed-secret session_id=session-secret")

    monkeypatch.setattr(cli.rest_client, "create_browser_session", fail_create)
    status: dict[str, Any] = {"credit_policy": {"browser": "allow"}}

    assert cli._run_live_paid_checks(status) is False
    serialized = json.dumps(status)
    assert "signed-secret" not in serialized
    assert "session-secret" not in serialized
    assert "RuntimeError" in status["live_paid_error"]


def test_doctor_live_paid_failure_updates_json_ok_and_exit_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "collect_status",
        lambda *, live=False: {
            "ok": True,
            "web_backend_configured": True,
            "mcp_configured": True,
            "api_key_fallback_configured": False,
            "credit_policy": {"browser": "deny"},
            "retired_credit_policy_keys": [],
        },
    )

    result = cli.cmd_doctor(argparse.Namespace(json=True, live=False, live_paid=True))
    payload = json.loads(capsys.readouterr().out)

    assert result == 1
    assert payload["ok"] is False
    assert payload["live_paid_ok"] is False


def test_credits_set_accepts_only_browser_and_saves_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _configured_config()
    saved: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_load_config", lambda: config)
    monkeypatch.setattr(cli, "_save_config", lambda value: saved.append(copy.deepcopy(value)))

    args = _parser().parse_args(["credits", "set", "browser", "request"])
    assert cli.dispatch_tinyfish_cli(args) == 0

    assert saved[-1]["tinyfish"]["credit_policy"] == {"browser": "request"}


def test_credits_status_json_includes_retired_keys(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_load_config", lambda: _configured_config(retired=True))

    assert cli.cmd_credits(argparse.Namespace(credits_command="status", json=True)) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload == {
        "credit_policy": {"browser": "deny"},
        "retired_credit_policy_keys": ["agent", "profile_setup", "model_tools"],
    }


def test_credits_reset_removes_retired_keys_and_leaves_browser_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _configured_config(browser_policy="allow", retired=True)
    saved: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "_load_config", lambda: config)
    monkeypatch.setattr(cli, "_save_config", lambda value: saved.append(copy.deepcopy(value)))

    result = cli.cmd_credits(argparse.Namespace(credits_command="reset", json=False))

    assert result == 0
    assert config["tinyfish"]["credit_policy"] == {"browser": "deny"}
    assert saved[-1]["tinyfish"]["credit_policy"] == {"browser": "deny"}


def test_usage_calls_fetch_usage_and_labels_surface(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(cli, "_get_env", lambda name: "tf_secret")

    def fetch_usage(*, api_key: str) -> dict[str, Any]:
        calls.append(api_key)
        return {"operations": [{"status": "completed"}]}

    monkeypatch.setattr(cli.rest_client, "fetch_usage", fetch_usage)

    result = cli.cmd_usage(argparse.Namespace(json=True))
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert calls == ["tf_secret"]
    assert payload == {
        "success": True,
        "surface": "fetch",
        "data": {"operations": [{"status": "completed"}]},
    }
    assert "tf_secret" not in json.dumps(payload)


def test_usage_failure_keeps_fetch_surface_and_returns_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_get_env", lambda name: "tf_secret")

    def fail_usage(*, api_key: str) -> dict[str, Any]:
        raise RuntimeError("usage unavailable")

    monkeypatch.setattr(cli.rest_client, "fetch_usage", fail_usage)

    result = cli.cmd_usage(argparse.Namespace(json=True))
    payload = json.loads(capsys.readouterr().out)

    assert result == 1
    assert payload["success"] is False
    assert payload["surface"] == "fetch"
    assert payload["error"] == "usage unavailable"


def test_usage_without_api_key_fails_before_calling_fetch_usage(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "_get_env", lambda name: "")
    monkeypatch.setattr(
        cli.rest_client,
        "fetch_usage",
        lambda **kwargs: pytest.fail("Fetch usage must not be called"),
    )

    result = cli.cmd_usage(argparse.Namespace(json=True))
    captured = capsys.readouterr()

    assert result == 1
    assert captured.out == ""
    assert "TINYFISH_API_KEY is required" in captured.err
    assert "Agent" not in captured.err
    assert "Profile" not in captured.err
