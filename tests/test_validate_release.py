from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_release import ReleaseValidationError, validate_release


def write_release_files(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "hermes-plugin-tinyfish"',
                'version = "0.2.0"',
                "",
            ]
        )
    )
    (root / "plugin.yaml").write_text("name: web-tinyfish\nversion: 0.2.0\n")
    (root / "CHANGELOG.md").write_text(
        "\n".join(
            [
                "# Changelog",
                "",
                "## Unreleased",
                "",
                "## [0.2.0] - 2026-07-08",
                "",
                "### Added",
                "",
                "- Added a feature.",
                "",
                "## [0.1.4] - 2026-07-07",
                "",
            ]
        )
    )


def test_validate_release_writes_only_matching_section(tmp_path: Path) -> None:
    write_release_files(tmp_path)
    notes = tmp_path / "notes.md"

    version = validate_release(tmp_path, tag="v0.2.0", notes_path=notes)

    assert version == "0.2.0"
    assert notes.read_text() == "## [0.2.0] - 2026-07-08\n### Added\n\n- Added a feature.\n"


def test_validate_release_rejects_wrong_tag(tmp_path: Path) -> None:
    write_release_files(tmp_path)

    with pytest.raises(ReleaseValidationError, match="does not match pyproject version"):
        validate_release(tmp_path, tag="v0.2.1", notes_path=tmp_path / "notes.md")
