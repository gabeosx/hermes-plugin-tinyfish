from __future__ import annotations

import importlib.util
from pathlib import Path

import hermes_plugin_tinyfish


def test_legacy_root_entrypoint_loads_canonical_runtime() -> None:
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("legacy_tinyfish_entrypoint", root / "__init__.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert module.register is hermes_plugin_tinyfish.register


def test_scanner_friendly_distribution_contains_only_runtime_surface() -> None:
    root = Path(__file__).resolve().parents[1]
    distribution = root / "hermes"

    assert (distribution / "plugin.yaml").is_file()
    assert (distribution / "after-install.md").is_file()
    assert (distribution / "__init__.py").is_file()
    assert (distribution / "hermes_plugin_tinyfish").is_dir()
    assert not (distribution / ".github").exists()
    assert not (distribution / ".agents").exists()
