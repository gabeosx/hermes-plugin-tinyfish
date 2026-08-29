"""Compatibility entry point for pre-0.4 root-directory Git installs.

New Hermes installations use the scanner-friendly ``hermes/`` subdirectory.
Existing root-directory installations still load this shim after an update.
"""

from __future__ import annotations

import sys
from pathlib import Path

_INSTALL_ROOT = Path(__file__).resolve().parent / "hermes"
_install_root_text = str(_INSTALL_ROOT)
if _install_root_text not in sys.path:
    sys.path.insert(0, _install_root_text)

from hermes_plugin_tinyfish import register  # noqa: E402

__all__ = ["register"]
