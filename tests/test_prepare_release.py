from __future__ import annotations

from pathlib import Path

import pytest

from scripts.prepare_release import ReleasePrepError, prepare_release


def write_release_files(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "hermes-plugin-tinyfish"',
                'version = "0.1.4"',
                "",
            ]
        )
    )
    (root / "plugin.yaml").write_text("name: web-tinyfish\nversion: 0.1.4\n")
    (root / "CHANGELOG.md").write_text(
        "\n".join(
            [
                "# Changelog",
                "",
                "## Unreleased",
                "",
                "### Added",
                "",
                "- Added a feature.",
                "",
                "## [0.1.4] - 2026-07-07",
                "",
                "### Changed",
                "",
                "- Previous release.",
                "",
            ]
        )
    )


def test_prepare_release_bumps_metadata_and_promotes_unreleased(tmp_path: Path) -> None:
    write_release_files(tmp_path)

    version = prepare_release(tmp_path, bump="minor", version=None, release_date="2026-07-08")

    assert version == "0.2.0"
    assert 'version = "0.2.0"' in (tmp_path / "pyproject.toml").read_text()
    assert "version: 0.2.0" in (tmp_path / "plugin.yaml").read_text()
    changelog = (tmp_path / "CHANGELOG.md").read_text()
    assert "## Unreleased\n\n## [0.2.0] - 2026-07-08" in changelog
    assert "- Added a feature." in changelog


def test_prepare_release_rejects_empty_unreleased(tmp_path: Path) -> None:
    write_release_files(tmp_path)
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n## [0.1.4] - 2026-07-07\n")

    with pytest.raises(ReleasePrepError, match="Unreleased section is empty"):
        prepare_release(tmp_path, bump="patch", version=None, release_date="2026-07-08")
