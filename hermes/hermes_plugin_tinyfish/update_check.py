"""Non-blocking, source-aware TinyFish plugin update checks."""

from __future__ import annotations

import json
import logging
import math
import os
import re
import tempfile
import threading
import time
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

from .config import load_config, update_check_enabled

ReleaseChannel = Literal["github", "pypi"]

CACHE_TTL_SECONDS = 24 * 60 * 60
GITHUB_LATEST_API = "https://api.github.com/repos/gabeosx/hermes-plugin-tinyfish/releases/latest"
GITHUB_RELEASES_URL = "https://github.com/gabeosx/hermes-plugin-tinyfish/releases/latest"
PYPI_PROJECT_API = "https://pypi.org/pypi/hermes-plugin-tinyfish/json"
PYPI_PROJECT_URL = "https://pypi.org/project/hermes-plugin-tinyfish/"

_CACHE_FILE = "web-tinyfish-update.json"
_STABLE_VERSION_RE = re.compile(r"^[vV]?(\d+)\.(\d+)\.(\d+)$")
logger = logging.getLogger(__name__)
_PROCESS_NOTICE_LOCK = threading.Lock()
_PROCESS_NOTICE_EMITTED = False


@dataclass(frozen=True)
class InstallInfo:
    current_version: str
    channel: ReleaseChannel
    update_command: str | None


@dataclass(frozen=True)
class UpdateCache:
    channel: ReleaseChannel
    latest_version: str | None
    checked_at: float


def _hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return Path(get_hermes_home())
    except Exception:
        return Path(os.getenv("HERMES_HOME") or Path.home() / ".hermes")


def _stable_version(value: object) -> tuple[int, int, int] | None:
    match = _STABLE_VERSION_RE.fullmatch(str(value or "").strip())
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def _is_update_available(current: object, latest: object) -> bool | None:
    current_version = _stable_version(current)
    latest_version = _stable_version(latest)
    if current_version is None or latest_version is None:
        return None
    return latest_version > current_version


def resolve_install_info(ctx: Any, fallback_version: str) -> InstallInfo:
    """Resolve update ownership from public Hermes manifest metadata."""

    manifest = getattr(ctx, "manifest", None)
    source = str(getattr(manifest, "source", "") or "")
    manifest_version = str(getattr(manifest, "version", "") or "")
    current_version = manifest_version or fallback_version
    plugin_path = str(getattr(manifest, "path", "") or "")

    if source == "entrypoint":
        return InstallInfo(
            current_version=fallback_version,
            channel="pypi",
            update_command="python -m pip install --upgrade hermes-plugin-tinyfish",
        )

    if source == "user" and plugin_path and (Path(plugin_path) / ".git").is_dir():
        return InstallInfo(
            current_version=current_version,
            channel="github",
            update_command="hermes plugins update web-tinyfish",
        )

    return InstallInfo(
        current_version=current_version,
        channel="github",
        update_command=None,
    )


def _read_cache(path: Path, channel: ReleaseChannel) -> UpdateCache | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("channel") != channel:
            return None
        checked_at = float(payload["checked_at"])
        if not math.isfinite(checked_at) or checked_at < 0:
            return None
        raw_latest = payload.get("latest_version")
        latest = str(raw_latest).strip() if raw_latest not in (None, "") else None
        if latest is not None and _stable_version(latest) is None:
            return None
        return UpdateCache(channel=channel, latest_version=latest, checked_at=checked_at)
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _write_cache(path: Path, state: UpdateCache) -> None:
    temporary_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "channel": state.channel,
                    "latest_version": state.latest_version or "",
                    "checked_at": state.checked_at,
                },
                handle,
                sort_keys=True,
                separators=(",", ":"),
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError:
        logger.debug("TinyFish update cache could not be written")
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)


def _fetch_latest_version(channel: ReleaseChannel, current_version: str) -> str | None:
    headers = {
        "Accept": "application/vnd.github+json" if channel == "github" else "application/json",
        "User-Agent": f"hermes-plugin-tinyfish/{current_version}",
    }
    if channel == "github":
        headers["X-GitHub-Api-Version"] = "2022-11-28"
        url = GITHUB_LATEST_API
    else:
        url = PYPI_PROJECT_API

    response = httpx.get(url, headers=headers, timeout=5.0, follow_redirects=True)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        return None
    if channel == "github":
        if payload.get("draft") is True or payload.get("prerelease") is True:
            return None
        latest = payload.get("tag_name")
    else:
        info = payload.get("info")
        latest = info.get("version") if isinstance(info, dict) else None
    normalized = str(latest or "").strip()
    return normalized if _stable_version(normalized) is not None else None


def _environment_disables_check(environment: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environment is None else environment
    return "NO_UPDATE_NOTIFIER" in env or bool(env.get("CI")) or bool(env.get("PYTEST_CURRENT_TEST"))


class UpdateChecker:
    """Own one process's background check, cached status, and one-time notice."""

    def __init__(
        self,
        install: InstallInfo,
        *,
        home: Path | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.install = install
        self._cache_path = (home or _hermes_home()) / "cache" / _CACHE_FILE
        self._now = now
        self._state = _read_cache(self._cache_path, install.channel)
        self._lock = threading.Lock()
        self._started = False

    @property
    def cache_path(self) -> Path:
        return self._cache_path

    def _enabled(self) -> bool:
        return update_check_enabled(load_config()) and not _environment_disables_check()

    def start(self) -> None:
        """Start at most one stale-cache refresh without waiting for it."""

        if not self._enabled():
            return
        with self._lock:
            if self._started:
                return
            self._started = True
            state = self._state
            now = float(self._now())
            if state is not None and 0 <= now - state.checked_at < CACHE_TTL_SECONDS:
                return
        thread = threading.Thread(
            target=self._refresh,
            name="tinyfish-update-check",
            daemon=True,
        )
        thread.start()

    def _refresh(self) -> None:
        with self._lock:
            previous_latest = self._state.latest_version if self._state is not None else None
        try:
            latest = _fetch_latest_version(self.install.channel, self.install.current_version)
        except Exception as exc:  # noqa: BLE001 - update checks are always best-effort.
            logger.debug("TinyFish update check failed (%s)", type(exc).__name__)
            latest = previous_latest
        state = UpdateCache(
            channel=self.install.channel,
            latest_version=latest,
            checked_at=float(self._now()),
        )
        with self._lock:
            self._state = state
        _write_cache(self._cache_path, state)

    def notice_context(self) -> str | None:
        """Return one model instruction when a newer stable version is cached."""

        global _PROCESS_NOTICE_EMITTED

        if not self._enabled():
            return None
        self.start()
        with self._lock:
            if self._state is None:
                return None
            latest = self._state.latest_version
            if _is_update_available(self.install.current_version, latest) is not True:
                return None
        with _PROCESS_NOTICE_LOCK:
            if _PROCESS_NOTICE_EMITTED:
                return None
            _PROCESS_NOTICE_EMITTED = True

        release_url = GITHUB_RELEASES_URL if self.install.channel == "github" else PYPI_PROJECT_URL
        if self.install.update_command:
            action = f"run `{self.install.update_command}` and then restart Hermes"
        else:
            action = f"update it using the installation method that manages it; see {release_url}"
        return (
            "TinyFish plugin maintenance notice: "
            f"version {self.install.current_version} is installed and stable version {latest} is available. "
            f"Briefly tell the user to {action}. Do not run an update automatically."
        )

    def status(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return cached, non-networked update diagnostics."""

        with self._lock:
            state = self._state
        latest = state.latest_version if state is not None else None
        return {
            "update_check_enabled": update_check_enabled(config),
            "update_check_active": bool(update_check_enabled(config) and not _environment_disables_check()),
            "installed_plugin_version": self.install.current_version,
            "update_release_channel": self.install.channel,
            "latest_plugin_version": latest,
            "plugin_update_available": _is_update_available(self.install.current_version, latest),
            "update_checked_at": state.checked_at if state is not None else None,
        }
