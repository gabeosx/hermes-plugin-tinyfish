from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class WebSearchProvider:
    pass


def get_provider_env(name: str) -> str:
    return os.getenv(name, "")


agent_pkg = types.ModuleType("agent")
web_provider_mod = types.ModuleType("agent.web_search_provider")
web_provider_mod.WebSearchProvider = WebSearchProvider
web_provider_mod.get_provider_env = get_provider_env
sys.modules.setdefault("agent", agent_pkg)
sys.modules["agent.web_search_provider"] = web_provider_mod


class FakeRegistry:
    def __init__(self) -> None:
        self.names: set[str] = set()
        self.responses: dict[str, Any] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get_all_tool_names(self) -> list[str]:
        return sorted(self.names)

    def dispatch(self, name: str, args: dict[str, Any], **kwargs: Any) -> str:
        del kwargs
        self.calls.append((name, args))
        result = self.responses[name]
        return result if isinstance(result, str) else result


fake_registry = FakeRegistry()
tools_pkg = types.ModuleType("tools")
registry_mod = types.ModuleType("tools.registry")
registry_mod.registry = fake_registry
interrupt_mod = types.ModuleType("tools.interrupt")
interrupt_mod.is_interrupted = lambda: False
sys.modules.setdefault("tools", tools_pkg)
sys.modules["tools.registry"] = registry_mod
sys.modules["tools.interrupt"] = interrupt_mod
