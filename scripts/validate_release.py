"""Validate release metadata and extract release notes."""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


class ReleaseValidationError(RuntimeError):
    """Raised when release metadata is inconsistent."""


def validate_release(root: pathlib.Path, *, tag: str, notes_path: pathlib.Path) -> str:
    with (root / "pyproject.toml").open("rb") as fh:
        version = tomllib.load(fh)["project"]["version"]

    expected_tag = f"v{version}"
    if tag != expected_tag:
        raise ReleaseValidationError(
            f"Tag {tag!r} does not match pyproject version {version!r}; expected {expected_tag!r}"
        )

    plugin_yaml = (root / "plugin.yaml").read_text()
    plugin_match = re.search(r"^version:\s*['\"]?([^'\"\s#]+)", plugin_yaml, re.MULTILINE)
    if not plugin_match:
        raise ReleaseValidationError("plugin.yaml is missing a top-level version")
    plugin_version = plugin_match.group(1)
    if plugin_version != version:
        raise ReleaseValidationError(
            f"plugin.yaml version {plugin_version!r} does not match pyproject version {version!r}"
        )

    changelog = (root / "CHANGELOG.md").read_text()
    pattern = (
        rf"^## \[{re.escape(version)}\] - "
        rf"\d{{4}}-\d{{2}}-\d{{2}}\n"
        rf"(?P<body>.*?)(?=^## \[|\Z)"
    )
    match = re.search(pattern, changelog, re.MULTILINE | re.DOTALL)
    if not match:
        raise ReleaseValidationError(
            "CHANGELOG.md must contain a dated section for this release, "
            f"for example: ## [{version}] - YYYY-MM-DD"
        )

    heading_match = re.search(
        rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})",
        changelog,
        re.MULTILINE,
    )
    release_notes = f"## [{version}] - {heading_match.group(1)}\n"
    release_notes += match.group("body").strip() + "\n"
    notes_path.write_text(release_notes)
    return version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate release metadata and write release notes")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--tag", default=os.getenv("GITHUB_REF_NAME", ""), help="Release tag, e.g. v0.2.0")
    parser.add_argument("--notes-path", default="release-notes.md", help="Path to write release notes")
    args = parser.parse_args(argv)

    try:
        version = validate_release(
            pathlib.Path(args.root),
            tag=args.tag,
            notes_path=pathlib.Path(args.notes_path),
        )
    except (OSError, ReleaseValidationError) as exc:
        print(f"release validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Validated release v{version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
