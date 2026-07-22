from __future__ import annotations

import pytest

import hermes_plugin_tinyfish
from hermes_plugin_tinyfish import setup_cli


class FakeContext:
    def __init__(self) -> None:
        self.providers = []
        self.browser_providers = []
        self.cli_commands = []
        self.commands = []
        self.hooks = []
        self.tools = []

    def dispatch_tool(self, name, args):
        return "{}"

    def register_web_search_provider(self, provider) -> None:
        self.providers.append(provider)

    def register_browser_provider(self, provider) -> None:
        self.browser_providers.append(provider)

    def register_hook(self, name, handler) -> None:
        self.hooks.append((name, handler))

    def register_tool(self, **kwargs) -> None:
        self.tools.append(kwargs)

    def register_cli_command(self, **kwargs) -> None:
        self.cli_commands.append(kwargs)

    def register_command(self, **kwargs) -> None:
        self.commands.append(kwargs)


def test_register_adds_provider_and_cli_command() -> None:
    ctx = FakeContext()

    hermes_plugin_tinyfish.register(ctx)

    assert ctx.providers[0].name == "tinyfish"
    assert ctx.browser_providers[0].name == "tinyfish"
    assert ctx.hooks[0][0] == "pre_tool_call"
    assert ctx.tools == []
    assert ctx.cli_commands[0]["name"] == "tinyfish"
    assert callable(ctx.cli_commands[0]["setup_fn"])
    assert callable(ctx.cli_commands[0]["handler_fn"])
    assert ctx.commands[0]["name"] == "tinyfish-status"
    assert ctx.commands[0]["args_hint"] == "[live]"
    assert ctx.commands[0]["handler"]("unexpected") == "Usage: /tinyfish-status [live]"


def test_register_never_adds_retired_model_tools(monkeypatch) -> None:
    monkeypatch.setattr(
        "hermes_plugin_tinyfish.config.load_config",
        lambda: {"tinyfish": {"credit_policy": {"model_tools": "request", "agent": "request"}}},
    )
    ctx = FakeContext()

    hermes_plugin_tinyfish.register(ctx)

    assert ctx.tools == []


def test_registered_cli_handler_propagates_nonzero_exit_status(monkeypatch) -> None:
    monkeypatch.setattr(setup_cli, "dispatch_tinyfish_cli", lambda args, provider: 7)
    ctx = FakeContext()
    hermes_plugin_tinyfish.register(ctx)

    with pytest.raises(SystemExit) as exc_info:
        ctx.cli_commands[0]["handler_fn"](object())

    assert exc_info.value.code == 7
