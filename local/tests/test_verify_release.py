from __future__ import annotations

import io
import tarfile
import zipfile
from typing import TYPE_CHECKING

import pytest

from local.verify_release import (
    DEFAULT_CHANGELOG_PATH,
    DEFAULT_PYPROJECT_PATH,
    expected_sdist_members,
    expected_wheel_members,
    main,
    read_project_version,
    verify_and_extract_release_notes,
    verify_dist_archives,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def _write_changelog(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _build_wheel(path: Path, members: Iterable[str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for member in members:
            zf.writestr(member, b"data")


def _build_sdist(path: Path, members: Iterable[str]) -> None:
    with tarfile.open(path, "w:gz") as tf:
        for member in members:
            payload = b"data"
            info = tarfile.TarInfo(name=member)
            info.size = len(payload)
            tf.addfile(info, io.BytesIO(payload))


class TestVerifyRelease:
    def test_live_repository_changelog_matches_pyproject(self) -> None:
        version = read_project_version(DEFAULT_PYPROJECT_PATH)
        notes = verify_and_extract_release_notes(DEFAULT_CHANGELOG_PATH, version=version)
        assert notes.startswith("### ")
        assert notes.endswith("\n")

    @pytest.mark.parametrize("bad_version", ["", "2.1", "v2.1.0", "2.1.0rc1", "abc"])
    def test_read_project_version_rejects_invalid_semver(self, tmp_path: Path, bad_version: str) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(f'[project]\nversion = "{bad_version}"\n', encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid version"):
            read_project_version(pyproject)

    def test_verify_and_extract_preserves_paragraphs_and_upgrade_notes(self, tmp_path: Path) -> None:
        changelog = _write_changelog(
            tmp_path / "CHANGELOG.md",
            """# Changelog

## [Unreleased]

## [2.1.0] - 2026-10-25

Intro paragraph before categories.

### Added

- Feature A.

**Upgrade note:** Important migration note.

## [2.0.4] - 2026-10-24

### Changed

- Prior release.

[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0
[2.0.4]: https://github.com/gordon-code/cuid2/releases/tag/v2.0.4
""",
        )
        notes = verify_and_extract_release_notes(changelog, version="2.1.0")
        assert notes == (
            "Intro paragraph before categories.\n\n"
            "### Added\n\n"
            "- Feature A.\n\n"
            "**Upgrade note:** Important migration note.\n"
        )

    @pytest.mark.parametrize(
        ("content", "match"),
        [
            (
                (
                    "## [2.1.0] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0\n"
                ),
                r"Expected '## \[Unreleased\]' followed by '## \[2\.1\.0\] - YYYY-MM-DD'",
            ),
            (
                (
                    "## [Unreleased]\n\n## [2.0.9] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0\n"
                ),
                r"Expected '## \[Unreleased\]' followed by '## \[2\.1\.0\] - YYYY-MM-DD'",
            ),
            (
                (
                    "## [Unreleased]\n\n## [2.1.0] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.0.4...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0\n"
                ),
                "Missing or stale compare links for 2.1.0",
            ),
            (
                (
                    "## [Unreleased]\n\n## [2.1.0] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                ),
                "Missing or stale compare links for 2.1.0",
            ),
            (
                (
                    "## [Unreleased]\n\n## [2.1.0] - 2026-10-25\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0\n"
                ),
                r"Missing or empty CHANGELOG\.md section for version 2\.1\.0",
            ),
            (
                (
                    "## [Unreleased]\n\n## [2.1.0] - 2026-10-25\n\n### Added\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0\n"
                ),
                r"Missing or empty CHANGELOG\.md section for version 2\.1\.0",
            ),
        ],
    )
    def test_verify_and_extract_rejects_invalid_changelog(
        self,
        tmp_path: Path,
        content: str,
        match: str,
    ) -> None:
        changelog = _write_changelog(tmp_path / "CHANGELOG.md", content)
        with pytest.raises(ValueError, match=match):
            verify_and_extract_release_notes(changelog, version="2.1.0")

    def test_verify_dist_archives_accepts_exact_allowlist(self, tmp_path: Path) -> None:
        version = "2.1.0"
        _build_wheel(tmp_path / f"cuid2-{version}-py3-none-any.whl", expected_wheel_members(version))
        _build_sdist(tmp_path / f"cuid2-{version}.tar.gz", expected_sdist_members(version))
        verify_dist_archives(tmp_path, version=version)

    def test_verify_dist_archives_rejects_missing_or_extra_files(self, tmp_path: Path) -> None:
        version = "2.1.0"
        with pytest.raises(ValueError, match="Expected 1 wheel"):
            verify_dist_archives(tmp_path, version=version)

        _build_wheel(tmp_path / f"cuid2-{version}-py3-none-any.whl", expected_wheel_members(version))
        with pytest.raises(ValueError, match="Expected 1 sdist"):
            verify_dist_archives(tmp_path, version=version)

        _build_sdist(
            tmp_path / f"cuid2-{version}.tar.gz",
            [*expected_sdist_members(version), f"cuid2-{version}/uv.lock"],
        )
        with pytest.raises(ValueError, match="Sdist mismatch"):
            verify_dist_archives(tmp_path, version=version)

        _build_wheel(
            tmp_path / f"cuid2-{version}-py3-none-any.whl",
            [*expected_wheel_members(version), "cuid2/unexpected.py"],
        )
        with pytest.raises(ValueError, match="Wheel mismatch"):
            verify_dist_archives(tmp_path, version=version)

    def test_cli_main_changelog_and_dist(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        notes_out = tmp_path / "release-notes.md"
        gh_out = tmp_path / "github-output.txt"
        assert (
            main(
                [
                    "changelog",
                    "--pyproject",
                    str(DEFAULT_PYPROJECT_PATH),
                    "--changelog",
                    str(DEFAULT_CHANGELOG_PATH),
                    "--notes-out",
                    str(notes_out),
                    "--github-output",
                    str(gh_out),
                ]
            )
            == 0
        )
        assert notes_out.read_text(encoding="utf-8").startswith("### ")
        assert gh_out.read_text(encoding="utf-8") == "version=2.1.0\n"

        version = read_project_version(DEFAULT_PYPROJECT_PATH)
        _build_wheel(tmp_path / f"cuid2-{version}-py3-none-any.whl", expected_wheel_members(version))
        _build_sdist(tmp_path / f"cuid2-{version}.tar.gz", expected_sdist_members(version))
        assert main(["dist", "--pyproject", str(DEFAULT_PYPROJECT_PATH), "--dist-dir", str(tmp_path)]) == 0

        bad_pyproject = tmp_path / "bad.toml"
        bad_pyproject.write_text('[project]\nversion = "invalid"\n', encoding="utf-8")
        assert main(["changelog", "--pyproject", str(bad_pyproject)]) == 1
        assert "Invalid version" in capsys.readouterr().err
