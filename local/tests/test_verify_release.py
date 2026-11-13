from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
import zipfile
from typing import TYPE_CHECKING

import pytest

from local.verify_release import (
    DEFAULT_CHANGELOG_PATH,
    DEFAULT_PYPROJECT_PATH,
    _check_version_vs_tags,
    _is_latest_version,
    expected_sdist_members,
    expected_wheel_members,
    main,
    read_project_version,
    resolve_release_commit,
    verify_and_extract_release_notes,
    verify_dist_archives,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def _write_lf(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _write_changelog(path: Path, content: str) -> Path:
    _write_lf(path, content)
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

    @pytest.mark.parametrize(
        "bad_version",
        ["", "2.1", "v2.1.0", "2.1.0rc1", "abc", "01.0.0", "1.01.0", "1.0.01"],
    )
    def test_read_project_version_rejects_invalid_semver(self, tmp_path: Path, bad_version: str) -> None:
        pyproject = tmp_path / "pyproject.toml"
        _write_lf(pyproject, f'[project]\nversion = "{bad_version}"\n')
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
            (
                (
                    "## [Unreleased]\n\n"
                    "## [2.1.0] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "## [2.1.0] - 2026-10-24\n\n### Added\n\n- B\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/releases/tag/v2.1.0\n"
                ),
                "duplicate release headings",
            ),
            (
                (
                    "## [Unreleased]\n\n"
                    "## [2.1.0] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "## [2.0.4] - 2026-10-24\n\n### Changed\n\n- B\n\n"
                    "## [2.0.4] - 2026-10-23\n\n### Fixed\n\n- C\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0\n"
                    "[2.0.4]: https://github.com/gordon-code/cuid2/releases/tag/v2.0.4\n"
                ),
                "duplicate release headings",
            ),
            (
                (
                    "## [Unreleased]\n\n"
                    "## [2.1.0] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "## [2.0.3] - 2026-10-23\n\n### Changed\n\n- B\n\n"
                    "## [2.0.4] - 2026-10-24\n\n### Changed\n\n- C\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.3...v2.1.0\n"
                    "[2.0.3]: https://github.com/gordon-code/cuid2/compare/v2.0.2...v2.0.3\n"
                    "[2.0.4]: https://github.com/gordon-code/cuid2/releases/tag/v2.0.4\n"
                ),
                r"Release versions must be strictly decreasing: 2\.0\.3 is listed above 2\.0\.4",
            ),
            (
                (
                    "## [Unreleased]\n\n"
                    "## [2.1.0] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "## [2.0.4] - 2026-10-24\n\n### Changed\n\n- B\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.3...v2.1.0\n"
                    "[2.0.4]: https://github.com/gordon-code/cuid2/releases/tag/v2.0.4\n"
                ),
                "Missing or stale compare links for 2.1.0",
            ),
            (
                (
                    "## [Unreleased]\n\n"
                    "## [2.1.0] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "## [2.1.0] - 2026-10-25\n\n### Fixed\n\n- B\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0\n"
                    "[2.0.4]: https://github.com/gordon-code/cuid2/releases/tag/v2.0.4\n"
                ),
                "duplicate release headings",
            ),
            (
                (
                    "## [Unreleased]\n\n"
                    "## [2.1.0] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "## [2.0.4] - 2026-10-24\n\n### Changed\n\n- B\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0\n"
                    "[2.0.4]: https://github.com/gordon-code/cuid2/compare/v2.0.3...v2.0.4\n"
                    "[2.0.3]: https://github.com/gordon-code/cuid2/releases/tag/v2.0.3\n"
                ),
                "footer links do not match release headings",
            ),
            (
                (
                    "## [Unreleased]\n\n"
                    "## [2.1.0] - 2026-10-25\n\n### Added\n\n- A\n\n"
                    "## [2.0.4]\n\n### Changed\n\n- B\n\n"
                    "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
                    "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0\n"
                    "[2.0.4]: https://github.com/gordon-code/cuid2/releases/tag/v2.0.4\n"
                ),
                "Invalid release heading",
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
        assert gh_out.read_text(encoding="utf-8") == "version=3.0.0\n"

        version = read_project_version(DEFAULT_PYPROJECT_PATH)
        _build_wheel(tmp_path / f"cuid2-{version}-py3-none-any.whl", expected_wheel_members(version))
        _build_sdist(tmp_path / f"cuid2-{version}.tar.gz", expected_sdist_members(version))
        assert main(["dist", "--pyproject", str(DEFAULT_PYPROJECT_PATH), "--dist-dir", str(tmp_path)]) == 0

        bad_pyproject = tmp_path / "bad.toml"
        _write_lf(bad_pyproject, '[project]\nversion = "invalid"\n')
        assert main(["changelog", "--pyproject", str(bad_pyproject)]) == 1
        assert "Invalid version" in capsys.readouterr().err

    @pytest.mark.parametrize(
        ("version", "tag_names", "expected_match"),
        [
            ("3.1.0", ["v3.0.0"], None),
            ("2.3.1", ["v3.0.0", "v2.3.0"], None),
            ("0.4.0", ["v0.3.0", "v1.0.0"], None),
            ("2.3.1", ["v2.4.0-rc.1", "v2.x", "v02.9.0", "vNext"], None),
            ("2.3.1", ["v3.0.0", "v2.4.0"], r"not greater than existing tag v2\.4\.0 on major 2"),
            ("2.3.0", ["v2.3.0"], r"not greater than existing tag v2\.3\.0 on major 2"),
            ("0.2.1", ["v0.3.0"], "on major 0"),
        ],
    )
    def test_check_version_vs_tags(
        self,
        version: str,
        tag_names: list[str],
        expected_match: str | None,
    ) -> None:
        if expected_match is None:
            _check_version_vs_tags(version, tag_names)
        else:
            with pytest.raises(ValueError, match=expected_match):
                _check_version_vs_tags(version, tag_names)

    @pytest.mark.parametrize(
        ("version", "tag_names", "expected"),
        [
            ("3.1.0", ["v3.0.0", "v2.3.0"], True),
            ("2.3.1", ["v3.0.0", "v2.3.0"], False),
            ("3.0.0", [], True),
            ("3.0.0", ["v3.0.0"], False),
            ("2.3.1", ["v2.4.0-rc.1", "vNext"], True),
        ],
    )
    def test_is_latest_version(self, version: str, tag_names: list[str], expected: bool) -> None:
        assert _is_latest_version(version, tag_names) is expected


@pytest.fixture
def isolated_git_env(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    git_keys = [k for k in os.environ if k.upper().startswith("GIT_")]
    for key in git_keys:
        monkeypatch.delenv(key)
    cfg = tmp_path_factory.mktemp("gitcfg") / "gitconfig"
    cfg.write_text(
        "[user]\n\tname = Test\n\temail = test@example.invalid\n"
        "[init]\n\tdefaultBranch = main\n"
        "[commit]\n\tgpgsign = false\n"
        "[tag]\n\tgpgsign = false\n"
        "[core]\n\tautocrlf = false\n",
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(cfg))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")


def _git(repo: Path, *args: str) -> str:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git not available")
    return subprocess.run(  # noqa: S603
        [git, *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _make_release_repo(repo: Path) -> str:
    _git(repo, "init", "-b", "main")
    _write_lf(repo / "pyproject.toml", '[project]\nname = "cuid2"\nversion = "2.0.4"\n')
    _write_lf(
        repo / "CHANGELOG.md",
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [2.0.4] - 2026-10-24\n\n"
        "### Changed\n\n"
        "- Initial tracked release.\n\n"
        "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.0.4...HEAD\n"
        "[2.0.4]: https://github.com/gordon-code/cuid2/releases/tag/v2.0.4\n",
    )
    _write_lf(repo / "src" / "cuid2" / "__init__.py", '"""Stub package."""\n')
    _write_lf(repo / "uv.lock", "version = 1\n")
    _write_lf(repo / "README.md", "# cuid2\n")
    _write_lf(repo / "LICENSE", "MIT\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "chore: release 2.0.4")
    _git(repo, "tag", "v2.0.4")

    _write_lf(repo / "pyproject.toml", '[project]\nname = "cuid2"\nversion = "2.1.0"\n')
    _write_lf(
        repo / "CHANGELOG.md",
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [2.1.0] - 2026-10-25\n\n"
        "### Added\n\n"
        "- New feature in 2.1.0.\n\n"
        "## [2.0.4] - 2026-10-24\n\n"
        "### Changed\n\n"
        "- Initial tracked release.\n\n"
        "[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD\n"
        "[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0\n"
        "[2.0.4]: https://github.com/gordon-code/cuid2/releases/tag/v2.0.4\n",
    )
    _git(repo, "add", "pyproject.toml", "CHANGELOG.md")
    _git(repo, "commit", "-q", "-m", "chore: release 2.1.0")
    return _git(repo, "rev-parse", "HEAD")


@pytest.mark.usefixtures("isolated_git_env")
class TestResolveReleaseCommit:
    def test_resolve_release_commit_selects_bump_commit(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        release_sha = _make_release_repo(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        changelog = tmp_path / "CHANGELOG.md"
        assert (
            resolve_release_commit(tmp_path, pyproject_path=pyproject, version="2.1.0", prev_version="2.0.4")
            == release_sha
        )

        _write_lf(pyproject, '[project]\nname = "cuid2"\nversion = "2.1.0"\n\n[tool.ruff]\nline-length = 120\n')
        _git(tmp_path, "add", "pyproject.toml")
        _git(tmp_path, "commit", "-q", "-m", "chore: update ruff config")

        _write_lf(tmp_path / "uv.lock", "version = 1\nrevision = 2\n")
        _git(tmp_path, "add", "uv.lock")
        _git(tmp_path, "commit", "-q", "-m", "chore: update lockfile")

        _write_lf(tmp_path / "prek.toml", "fail_fast = false\n")
        _git(tmp_path, "add", "prek.toml")
        _git(tmp_path, "commit", "-q", "-m", "chore: add prek config")

        assert (
            resolve_release_commit(tmp_path, pyproject_path=pyproject, version="2.1.0", prev_version="2.0.4")
            == release_sha
        )

        gh_out = tmp_path / "github-output.txt"
        rc = main(
            [
                "changelog",
                "--pyproject",
                str(pyproject),
                "--changelog",
                str(changelog),
                "--resolve-commit",
                "--github-output",
                str(gh_out),
            ],
        )
        assert rc == 0
        captured = capsys.readouterr()
        assert captured.out == f"{release_sha}\n"
        assert captured.err == ""
        assert gh_out.read_text(encoding="utf-8") == f"version=2.1.0\ncommit={release_sha}\nlatest=true\n"

    def test_resolve_release_commit_tag_checks(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        release_sha = _make_release_repo(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        changelog = tmp_path / "CHANGELOG.md"

        _git(tmp_path, "tag", "v2.1.0")
        with pytest.raises(ValueError, match=r"Release tag v2\.1\.0 already exists"):
            resolve_release_commit(tmp_path, pyproject_path=pyproject, version="2.1.0", prev_version="2.0.4")

        failed_notes = tmp_path / "failed-notes.md"
        failed_gh_out = tmp_path / "failed-github-output.txt"
        assert (
            main(
                [
                    "changelog",
                    "--pyproject",
                    str(pyproject),
                    "--changelog",
                    str(changelog),
                    "--resolve-commit",
                    "--notes-out",
                    str(failed_notes),
                    "--github-output",
                    str(failed_gh_out),
                ],
            )
            == 1
        )
        failed_captured = capsys.readouterr()
        assert failed_captured.out == ""
        assert "Release tag v2.1.0 already exists" in failed_captured.err
        assert not failed_notes.exists()
        assert not failed_gh_out.exists()

        _git(tmp_path, "tag", "-d", "v2.1.0")
        _git(tmp_path, "tag", "v2.2.0")
        with pytest.raises(ValueError, match=r"not greater than existing tag v2\.2\.0 on major 2"):
            resolve_release_commit(tmp_path, pyproject_path=pyproject, version="2.1.0", prev_version="2.0.4")

        _git(tmp_path, "tag", "-d", "v2.2.0")
        for extra_tag in ("v3.0.0", "v1.9.0", "v2.1.0-rc.1", "v2.x", "v02.5.0"):
            _git(tmp_path, "tag", extra_tag)

        assert (
            resolve_release_commit(tmp_path, pyproject_path=pyproject, version="2.1.0", prev_version="2.0.4")
            == release_sha
        )

        gh_out = tmp_path / "github-output.txt"
        rc = main(
            [
                "changelog",
                "--pyproject",
                str(pyproject),
                "--changelog",
                str(changelog),
                "--resolve-commit",
                "--github-output",
                str(gh_out),
            ],
        )
        assert rc == 0
        assert capsys.readouterr().out == f"{release_sha}\n"
        assert gh_out.read_text(encoding="utf-8") == f"version=2.1.0\ncommit={release_sha}\nlatest=false\n"

    def test_resolve_release_commit_parent_and_head_version(self, tmp_path: Path) -> None:
        release_sha = _make_release_repo(tmp_path)
        pyproject = tmp_path / "pyproject.toml"

        with pytest.raises(
            ValueError,
            match=r"Version before release commit .* is 2\.0\.4, but CHANGELOG\.md lists previous release 2\.0\.3",
        ):
            resolve_release_commit(tmp_path, pyproject_path=pyproject, version="2.1.0", prev_version="2.0.3")

        assert (
            resolve_release_commit(tmp_path, pyproject_path=pyproject, version="2.1.0", prev_version=None)
            == release_sha
        )

        with pytest.raises(
            ValueError,
            match=r"Committed pyproject\.toml at HEAD declares version '2\.1\.0', expected 2\.9\.9",
        ):
            resolve_release_commit(tmp_path, pyproject_path=pyproject, version="2.9.9", prev_version="2.0.4")

    def test_resolve_release_commit_first_release_and_recovery_history(self, tmp_path: Path) -> None:
        first_repo = tmp_path / "first"
        first_repo.mkdir()
        _git(first_repo, "init", "-b", "main")
        _write_lf(first_repo / "pyproject.toml", '[project]\nname = "cuid2"\nversion = "2.1.0"\n')
        _git(first_repo, "add", "pyproject.toml")
        _git(first_repo, "commit", "-q", "-m", "chore: initial release 2.1.0")
        first_sha = _git(first_repo, "rev-parse", "HEAD")
        assert (
            resolve_release_commit(
                first_repo,
                pyproject_path=first_repo / "pyproject.toml",
                version="2.1.0",
                prev_version=None,
            )
            == first_sha
        )

        recovery_repo = tmp_path / "recovery"
        recovery_repo.mkdir()
        _make_release_repo(recovery_repo)
        _write_lf(recovery_repo / "pyproject.toml", '[project]\nname = "cuid2"\nversion = "2.0.4"\n')
        _git(recovery_repo, "add", "pyproject.toml")
        _git(recovery_repo, "commit", "-q", "-m", "revert: restore 2.0.4")
        _write_lf(recovery_repo / "pyproject.toml", '[project]\nname = "cuid2"\nversion = "2.1.1"\n')
        _git(recovery_repo, "add", "pyproject.toml")
        _git(recovery_repo, "commit", "-q", "-m", "chore: release 2.1.1")
        final_sha = _git(recovery_repo, "rev-parse", "HEAD")
        assert (
            resolve_release_commit(
                recovery_repo,
                pyproject_path=recovery_repo / "pyproject.toml",
                version="2.1.1",
                prev_version="2.0.4",
            )
            == final_sha
        )

    def test_resolve_release_commit_shallow_clone(self, tmp_path: Path) -> None:
        repo = tmp_path / "origin"
        repo.mkdir()
        _make_release_repo(repo)
        clone = tmp_path / "shallow"
        _git(tmp_path, "clone", "--depth", "1", repo.as_uri(), str(clone))
        with pytest.raises(ValueError, match="Repository is shallow"):
            resolve_release_commit(
                clone,
                pyproject_path=clone / "pyproject.toml",
                version="2.1.0",
                prev_version="2.0.4",
            )

    def test_resolve_release_commit_requires_git(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _make_release_repo(tmp_path)
        monkeypatch.setattr(shutil, "which", lambda _name: None)
        with pytest.raises(ValueError, match="git executable not found"):
            resolve_release_commit(
                tmp_path,
                pyproject_path=tmp_path / "pyproject.toml",
                version="2.1.0",
                prev_version="2.0.4",
            )

    def test_resolve_release_commit_historical_pyproject_edge_cases(self, tmp_path: Path) -> None:
        dyn_repo = tmp_path / "dynamic"
        dyn_repo.mkdir()
        _git(dyn_repo, "init", "-b", "main")
        _write_lf(dyn_repo / "pyproject.toml", '[project]\nname = "cuid2"\ndynamic = ["version"]\n')
        _git(dyn_repo, "add", "pyproject.toml")
        _git(dyn_repo, "commit", "-q", "-m", "chore: dynamic version")
        _write_lf(dyn_repo / "pyproject.toml", '[project]\nname = "cuid2"\nversion = "2.1.0"\n')
        _git(dyn_repo, "add", "pyproject.toml")
        _git(dyn_repo, "commit", "-q", "-m", "chore: static 2.1.0")
        dyn_bump_sha = _git(dyn_repo, "rev-parse", "HEAD")
        assert (
            resolve_release_commit(
                dyn_repo,
                pyproject_path=dyn_repo / "pyproject.toml",
                version="2.1.0",
                prev_version=None,
            )
            == dyn_bump_sha
        )
        with pytest.raises(
            ValueError,
            match=r"Version before release commit .* is absent, but CHANGELOG\.md lists previous release 2\.0\.4",
        ):
            resolve_release_commit(
                dyn_repo,
                pyproject_path=dyn_repo / "pyproject.toml",
                version="2.1.0",
                prev_version="2.0.4",
            )

        bad_toml_repo = tmp_path / "bad_toml"
        bad_toml_repo.mkdir()
        _git(bad_toml_repo, "init", "-b", "main")
        _write_lf(bad_toml_repo / "pyproject.toml", "[project\nbroken = true\n")
        _git(bad_toml_repo, "add", "pyproject.toml")
        _git(bad_toml_repo, "commit", "-q", "-m", "chore: broken toml")
        _write_lf(bad_toml_repo / "pyproject.toml", '[project]\nname = "cuid2"\nversion = "2.1.0"\n')
        _git(bad_toml_repo, "add", "pyproject.toml")
        _git(bad_toml_repo, "commit", "-q", "-m", "chore: fix toml and set 2.1.0")
        with pytest.raises(ValueError, match=r"Cannot parse pyproject\.toml at"):
            resolve_release_commit(
                bad_toml_repo,
                pyproject_path=bad_toml_repo / "pyproject.toml",
                version="2.1.0",
                prev_version=None,
            )

        untracked_repo = tmp_path / "untracked"
        untracked_repo.mkdir()
        _git(untracked_repo, "init", "-b", "main")
        _write_lf(untracked_repo / "README.md", "# cuid2\n")
        _git(untracked_repo, "add", "README.md")
        _git(untracked_repo, "commit", "-q", "-m", "docs: add readme")
        _write_lf(untracked_repo / "pyproject.toml", '[project]\nname = "cuid2"\nversion = "2.1.0"\n')
        with pytest.raises(ValueError, match=r"No first-parent commit reachable from HEAD touches pyproject\.toml"):
            resolve_release_commit(
                untracked_repo,
                pyproject_path=untracked_repo / "pyproject.toml",
                version="2.1.0",
                prev_version=None,
            )
