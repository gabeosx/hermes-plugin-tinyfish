"""Prepare a Hermes TinyFish release PR.

This script promotes the current CHANGELOG.md "Unreleased" section into a
dated version section and keeps pyproject.toml and plugin.yaml aligned.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
from datetime import date

SEMVER_RE = re.compile(r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$")
PYPROJECT_VERSION_RE = re.compile(r'(?m)^version = "([^"]+)"')
PLUGIN_VERSION_RE = re.compile(r"(?m)^version:\s*['\"]?([^'\"\s#]+)")
UNRELEASED_RE = re.compile(r"(?ms)^## Unreleased\n(?P<body>.*?)(?=^## \[|\Z)")


class ReleasePrepError(RuntimeError):
    """Raised when release metadata cannot be prepared safely."""


def parse_version(version: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(version)
    if not match:
        raise ReleasePrepError(f"Unsupported version {version!r}; expected MAJOR.MINOR.PATCH")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def bump_version(current: str, bump: str) -> str:
    major, minor, patch = parse_version(current)
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ReleasePrepError(f"Unsupported bump {bump!r}")


def read_current_version(pyproject_text: str) -> str:
    match = PYPROJECT_VERSION_RE.search(pyproject_text)
    if not match:
        raise ReleasePrepError("pyproject.toml is missing project version")
    return match.group(1)


def update_pyproject(pyproject_text: str, version: str) -> str:
    return PYPROJECT_VERSION_RE.sub(f'version = "{version}"', pyproject_text, count=1)


def update_plugin_yaml(plugin_text: str, version: str) -> str:
    if not PLUGIN_VERSION_RE.search(plugin_text):
        raise ReleasePrepError("plugin.yaml is missing top-level version")
    return PLUGIN_VERSION_RE.sub(f"version: {version}", plugin_text, count=1)


def promote_changelog(changelog_text: str, version: str, release_date: str) -> str:
    if re.search(rf"(?m)^## \[{re.escape(version)}\] - ", changelog_text):
        raise ReleasePrepError(f"CHANGELOG.md already contains a {version} section")

    match = UNRELEASED_RE.search(changelog_text)
    if not match:
        raise ReleasePrepError("CHANGELOG.md is missing an Unreleased section")

    body = match.group("body").strip()
    if not body:
        raise ReleasePrepError("CHANGELOG.md Unreleased section is empty")

    replacement = f"## Unreleased\n\n## [{version}] - {release_date}\n\n{body}\n\n"
    return changelog_text[: match.start()] + replacement + changelog_text[match.end() :]


def prepare_release(root: pathlib.Path, *, bump: str, version: str | None, release_date: str) -> str:
    pyproject_path = root / "pyproject.toml"
    plugin_path = root / "plugin.yaml"
    changelog_path = root / "CHANGELOG.md"

    pyproject_text = pyproject_path.read_text()
    current_version = read_current_version(pyproject_text)
    next_version = version or bump_version(current_version, bump)
    parse_version(next_version)

    pyproject_path.write_text(update_pyproject(pyproject_text, next_version))
    plugin_path.write_text(update_plugin_yaml(plugin_path.read_text(), next_version))
    changelog_path.write_text(promote_changelog(changelog_path.read_text(), next_version, release_date))
    return next_version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare release metadata and changelog")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")
    parser.add_argument("--version", help="Explicit MAJOR.MINOR.PATCH version. Overrides --bump.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Release date, YYYY-MM-DD")
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="Write version/tag outputs to the path in GITHUB_OUTPUT",
    )
    args = parser.parse_args(argv)

    try:
        version = prepare_release(
            pathlib.Path(args.root),
            bump=args.bump,
            version=args.version,
            release_date=args.date,
        )
    except (OSError, ReleasePrepError) as exc:
        print(f"release prep failed: {exc}", file=sys.stderr)
        return 1

    print(f"Prepared release v{version}")
    if args.github_output:
        output_path = os.environ.get("GITHUB_OUTPUT")
        if output_path:
            with open(output_path, "a") as fh:
                fh.write(f"version={version}\n")
                fh.write(f"tag=v{version}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
