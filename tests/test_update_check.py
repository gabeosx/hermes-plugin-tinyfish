from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from hermes_plugin_tinyfish import update_check as updates


@pytest.fixture(autouse=True)
def _reset_process_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updates, "_PROCESS_NOTICE_EMITTED", False)


class _Response:
    def __init__(self, payload: Any, *, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        if self.error is not None:
            raise self.error

    def json(self) -> Any:
        return self.payload


def _install(
    *,
    version: str = "1.2.3",
    channel: updates.ReleaseChannel = "github",
    command: str | None = "hermes plugins update web-tinyfish",
) -> updates.InstallInfo:
    return updates.InstallInfo(version, channel, command)


def _enable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updates, "load_config", lambda: {})
    monkeypatch.setattr(updates, "_environment_disables_check", lambda environment=None: False)


@pytest.mark.parametrize(
    ("current", "latest", "expected"),
    [
        ("1.2.3", "1.2.4", True),
        ("v1.2.3", "2.0.0", True),
        ("1.2.3", "1.2.3", False),
        ("1.3.0", "1.2.9", False),
        ("1.2.3rc1", "1.2.3", None),
        ("unknown", "1.2.3", None),
    ],
)
def test_stable_version_comparison(current: str, latest: str, expected: bool | None) -> None:
    assert updates._is_update_available(current, latest) is expected


def test_resolve_install_info_uses_source_appropriate_update_ownership(tmp_path: Path) -> None:
    git_plugin = tmp_path / "plugin"
    (git_plugin / ".git").mkdir(parents=True)

    git = updates.resolve_install_info(
        SimpleNamespace(manifest=SimpleNamespace(source="user", path=str(git_plugin), version="2.0.0")),
        "9.9.9",
    )
    pypi = updates.resolve_install_info(
        SimpleNamespace(manifest=SimpleNamespace(source="entrypoint", path="package:register", version="")),
        "3.0.0",
    )
    copied = updates.resolve_install_info(
        SimpleNamespace(manifest=SimpleNamespace(source="user", path=str(tmp_path), version="4.0.0")),
        "9.9.9",
    )

    assert git == _install(version="2.0.0")
    assert pypi == _install(
        version="3.0.0",
        channel="pypi",
        command="python -m pip install --upgrade hermes-plugin-tinyfish",
    )
    assert copied == _install(version="4.0.0", command=None)


def test_fresh_cache_prevents_a_background_refresh(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _enable(monkeypatch)
    cache = tmp_path / "cache" / "web-tinyfish-update.json"
    updates._write_cache(cache, updates.UpdateCache("github", "1.2.4", 100.0))
    checker = updates.UpdateChecker(_install(), home=tmp_path, now=lambda: 200.0)
    monkeypatch.setattr(
        updates.threading,
        "Thread",
        lambda **kwargs: pytest.fail("fresh cache must not start a thread"),
    )

    checker.start()

    assert checker.status()["latest_plugin_version"] == "1.2.4"


def test_stale_cache_starts_one_daemon_refresh_without_running_inline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _enable(monkeypatch)
    starts: list[tuple[Any, bool]] = []

    class _Thread:
        def __init__(self, *, target: Any, name: str, daemon: bool) -> None:
            assert name == "tinyfish-update-check"
            starts.append((target, daemon))

        def start(self) -> None:
            return None

    monkeypatch.setattr(updates.threading, "Thread", _Thread)
    checker = updates.UpdateChecker(_install(), home=tmp_path, now=lambda: 100_000.0)

    checker.start()
    checker.start()

    assert len(starts) == 1
    assert starts[0][1] is True
    assert not checker.cache_path.exists()


@pytest.mark.parametrize(
    ("channel", "payload", "expected_url", "expected"),
    [
        (
            "github",
            {"tag_name": "v2.0.0", "draft": False, "prerelease": False},
            updates.GITHUB_LATEST_API,
            "v2.0.0",
        ),
        ("pypi", {"info": {"version": "2.1.0"}}, updates.PYPI_PROJECT_API, "2.1.0"),
    ],
)
def test_fetch_latest_version_uses_release_channel(
    monkeypatch: pytest.MonkeyPatch,
    channel: updates.ReleaseChannel,
    payload: dict[str, Any],
    expected_url: str,
    expected: str,
) -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def get(url: str, **kwargs: Any) -> _Response:
        calls.append((url, kwargs["headers"]))
        assert kwargs["timeout"] == 5.0
        assert kwargs["follow_redirects"] is True
        return _Response(payload)

    monkeypatch.setattr(updates.httpx, "get", get)

    assert updates._fetch_latest_version(channel, "1.2.3") == expected
    assert calls[0][0] == expected_url
    assert calls[0][1]["User-Agent"] == "hermes-plugin-tinyfish/1.2.3"
    assert "Authorization" not in calls[0][1]


@pytest.mark.parametrize(
    "payload",
    [
        {"tag_name": "v2.0.0rc1", "draft": False, "prerelease": False},
        {"tag_name": "v2.0.0", "draft": True, "prerelease": False},
        {"tag_name": "v2.0.0", "draft": False, "prerelease": True},
        [],
    ],
)
def test_fetch_latest_version_rejects_nonstable_or_invalid_payloads(
    monkeypatch: pytest.MonkeyPatch, payload: Any
) -> None:
    monkeypatch.setattr(updates.httpx, "get", lambda *args, **kwargs: _Response(payload))

    assert updates._fetch_latest_version("github", "1.2.3") is None


def test_refresh_persists_success_and_notice_is_once_per_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _enable(monkeypatch)
    monkeypatch.setattr(updates, "_fetch_latest_version", lambda channel, current: "1.3.0")
    checker = updates.UpdateChecker(_install(), home=tmp_path, now=lambda: 123.0)
    checker._started = True

    assert checker.notice_context() is None
    checker._refresh()
    first = checker.notice_context()
    second = checker.notice_context()

    assert first is not None
    assert "1.2.3" in first and "1.3.0" in first
    assert "hermes plugins update web-tinyfish" in first
    assert "Do not run an update automatically" in first
    assert second is None
    payload = json.loads(checker.cache_path.read_text(encoding="utf-8"))
    assert payload == {"channel": "github", "checked_at": 123.0, "latest_version": "1.3.0"}


@pytest.mark.parametrize(
    ("channel", "command", "expected", "unexpected"),
    [
        (
            "pypi",
            "python -m pip install --upgrade hermes-plugin-tinyfish",
            "python -m pip install --upgrade",
            "installation method that manages it",
        ),
        (
            "github",
            None,
            "installation method that manages it",
            "hermes plugins update",
        ),
    ],
)
def test_pypi_and_unknown_install_notices_use_safe_instructions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    channel: updates.ReleaseChannel,
    command: str | None,
    expected: str,
    unexpected: str,
) -> None:
    _enable(monkeypatch)
    checker = updates.UpdateChecker(
        _install(channel=channel, command=command),
        home=tmp_path,
        now=lambda: 1.5,
    )
    checker._state = updates.UpdateCache(channel, "1.2.4", 1.0)

    notice = checker.notice_context() or ""

    assert expected in notice
    assert unexpected not in notice
    if channel == "github":
        assert "pip install" not in notice


def test_notice_is_shared_across_checker_instances_in_one_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _enable(monkeypatch)
    first = updates.UpdateChecker(_install(), home=tmp_path / "first", now=lambda: 1.5)
    second = updates.UpdateChecker(_install(), home=tmp_path / "second", now=lambda: 1.5)
    first._state = updates.UpdateCache("github", "1.2.4", 1.0)
    second._state = updates.UpdateCache("github", "1.2.4", 1.0)

    assert first.notice_context() is not None
    assert second.notice_context() is None


def test_failed_refresh_is_silent_and_preserves_previous_latest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _enable(monkeypatch)
    checker = updates.UpdateChecker(_install(), home=tmp_path, now=lambda: 500.0)
    checker._state = updates.UpdateCache("github", "1.2.4", 1.0)
    monkeypatch.setattr(
        updates,
        "_fetch_latest_version",
        lambda channel, current: (_ for _ in ()).throw(RuntimeError("offline secret")),
    )

    checker._refresh()

    assert checker.status()["latest_plugin_version"] == "1.2.4"
    assert "offline secret" not in checker.cache_path.read_text(encoding="utf-8")


def test_corrupt_cache_and_unwritable_cache_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache = tmp_path / "cache" / "web-tinyfish-update.json"
    cache.parent.mkdir(parents=True)
    cache.write_text("not-json", encoding="utf-8")
    checker = updates.UpdateChecker(_install(), home=tmp_path)
    assert checker.status()["latest_plugin_version"] is None
    assert checker.status()["plugin_update_available"] is None

    monkeypatch.setattr(updates.tempfile, "mkstemp", lambda **kwargs: (_ for _ in ()).throw(OSError()))
    updates._write_cache(cache, updates.UpdateCache("github", "1.2.4", 5.0))


@pytest.mark.parametrize("checked_at", ["NaN", -1])
def test_invalid_cache_timestamp_is_rejected(tmp_path: Path, checked_at: object) -> None:
    cache = tmp_path / "cache" / "web-tinyfish-update.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(
        json.dumps({"channel": "github", "latest_version": "1.2.4", "checked_at": checked_at}),
        encoding="utf-8",
    )

    checker = updates.UpdateChecker(_install(), home=tmp_path)

    assert checker.status()["latest_plugin_version"] is None


def test_concurrent_atomic_cache_writes_leave_valid_state(tmp_path: Path) -> None:
    cache = tmp_path / "cache" / "web-tinyfish-update.json"
    states = [
        updates.UpdateCache("github", "1.2.4", 10.0),
        updates.UpdateCache("github", "1.3.0", 20.0),
    ]
    threads = [threading.Thread(target=updates._write_cache, args=(cache, state)) for state in states]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    payload = json.loads(cache.read_text(encoding="utf-8"))
    assert payload in [
        {"channel": "github", "latest_version": "1.2.4", "checked_at": 10.0},
        {"channel": "github", "latest_version": "1.3.0", "checked_at": 20.0},
    ]


def test_config_and_environment_opt_outs_prevent_checks_and_notices(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert updates._environment_disables_check({"NO_UPDATE_NOTIFIER": ""}) is True
    assert updates._environment_disables_check({"CI": "1"}) is True
    assert updates._environment_disables_check({"PYTEST_CURRENT_TEST": "case"}) is True

    checker = updates.UpdateChecker(_install(), home=tmp_path)
    checker._state = updates.UpdateCache("github", "1.2.4", 1.0)
    monkeypatch.setattr(updates, "load_config", lambda: {"tinyfish": {"update_check": False}})
    monkeypatch.setattr(updates, "_environment_disables_check", lambda environment=None: False)
    assert checker.notice_context() is None

    monkeypatch.setattr(updates, "load_config", lambda: {})
    monkeypatch.setattr(updates, "_environment_disables_check", lambda environment=None: True)
    assert checker.notice_context() is None
