"""Directory-plugin entry point for ``hermes plugins install``.

Hermes loads this file directly when the repository is installed as a user
plugin. The package entry point in ``pyproject.toml`` imports the same
``register`` function when installed from PyPI.
"""

from __future__ import annotations

try:
    from .hermes_plugin_tinyfish import register
except ImportError:  # pragma: no cover - used for pip entry-point import shape
    from hermes_plugin_tinyfish import register

__all__ = ["register"]
