from __future__ import annotations

import hermes_plugin_tinyfish


class FakeContext:
    def __init__(self) -> None:
        self.providers = []
        self.cli_commands = []

    def dispatch_tool(self, name, args):
        return "{}"

    def register_web_search_provider(self, provider) -> None:
        self.providers.append(provider)

    def register_cli_command(self, **kwargs) -> None:
        self.cli_commands.append(kwargs)


def test_register_adds_provider_and_cli_command() -> None:
    ctx = FakeContext()

    hermes_plugin_tinyfish.register(ctx)

    assert ctx.providers[0].name == "tinyfish"
    assert ctx.cli_commands[0]["name"] == "tinyfish"
    assert callable(ctx.cli_commands[0]["setup_fn"])
    assert callable(ctx.cli_commands[0]["handler_fn"])
