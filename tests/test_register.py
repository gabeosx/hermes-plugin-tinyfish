from __future__ import annotations

import hermes_plugin_tinyfish


class FakeContext:
    def __init__(self) -> None:
        self.providers = []
        self.browser_providers = []
        self.cli_commands = []
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


def test_register_adds_model_tools_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "hermes_plugin_tinyfish.config.load_config",
        lambda: {"tinyfish": {"credit_policy": {"model_tools": "request", "agent": "request"}}},
    )
    ctx = FakeContext()

    hermes_plugin_tinyfish.register(ctx)

    assert {tool["name"] for tool in ctx.tools} == {
        "tinyfish_agent_run",
        "tinyfish_agent_run_async",
        "tinyfish_agent_status",
        "tinyfish_agent_cancel",
    }
