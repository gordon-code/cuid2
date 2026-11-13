"""Release verification and changelog extraction helpers for CI and pre-commit."""

from __future__ import annotations

import argparse
import itertools
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import keepachangelog

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"
DEFAULT_CHANGELOG_PATH = _REPO_ROOT / "CHANGELOG.md"
DEFAULT_DIST_DIR = _REPO_ROOT / "dist"
DEFAULT_REPO_URL = "https://github.com/gordon-code/cuid2"

_MIN_RELEASES = 2
_MIN_RELEASES_WITH_PREV = 3
_SEMVER_CORE = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
_SEMVER_RE = re.compile(rf"^{_SEMVER_CORE}$")
_TAG_VER_RE = re.compile(rf"^v{_SEMVER_CORE}$")
_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_H2_RE = re.compile(r"^## ")
_RELEASE_H2_RE = re.compile(rf"^## \[(?P<version>{_SEMVER_CORE})\] - \d{{4}}-\d{{2}}-\d{{2}}$")
_FOOTER_LINK_RE = re.compile(r"^\[[^\]]+\]:\s*https?://")


def _parse_semver(version: str) -> tuple[int, int, int]:
    match = _SEMVER_RE.fullmatch(version)
    if match is None:
        msg = f"Invalid semantic version: {version}"
        raise ValueError(msg)
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch))


def _previous_release_version(release_keys: Sequence[str]) -> str | None:
    return release_keys[2] if len(release_keys) >= _MIN_RELEASES_WITH_PREV else None


def read_project_version(pyproject_path: Path = DEFAULT_PYPROJECT_PATH) -> str:
    """Read and validate the semantic version from ``pyproject.toml``.

    Parameters
    ----------
    pyproject_path : Path, optional
        Path to ``pyproject.toml``, by default ``DEFAULT_PYPROJECT_PATH``.

    Returns
    -------
    str
        Validated ``MAJOR.MINOR.PATCH`` version string.

    Raises
    ------
    ValueError
        If the version string is missing or not ``MAJOR.MINOR.PATCH``.
    """
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = str(data.get("project", {}).get("version", ""))
    if not _SEMVER_RE.fullmatch(version):
        msg = f"Invalid version in {pyproject_path}: {version}"
        raise ValueError(msg)
    return version


def _parse_release_h2(header: str) -> str:
    match = _RELEASE_H2_RE.fullmatch(header)
    if match is None:
        msg = f"Invalid release heading in CHANGELOG.md: {header}"
        raise ValueError(msg)
    return match.group("version")


def _validate_release_headings(release_keys: Sequence[str], lines: Sequence[str]) -> None:
    h2_headers = [line for line in lines if _H2_RE.match(line)]
    heading_versions = [_parse_release_h2(header) for header in h2_headers[1:]]
    if len(set(heading_versions)) != len(heading_versions):
        msg = "CHANGELOG.md has duplicate release headings"
        raise ValueError(msg)
    if list(release_keys) != ["unreleased", *heading_versions]:
        msg = "CHANGELOG.md footer links do not match release headings"
        raise ValueError(msg)
    for newer, older in itertools.pairwise(heading_versions):
        if _parse_semver(newer) <= _parse_semver(older):
            msg = f"Release versions must be strictly decreasing: {newer} is listed above {older}"
            raise ValueError(msg)


def _validate_keepachangelog_metadata(
    changelog_path: Path,
    lines: list[str],
    *,
    version: str,
    repo_url: str,
) -> None:
    releases: dict[str, dict[str, Any]] = keepachangelog.to_dict(str(changelog_path), show_unreleased=True)
    release_keys = list(releases.keys())
    if len(release_keys) < _MIN_RELEASES or release_keys[0] != "unreleased" or release_keys[1] != version:
        msg = f"Expected keepachangelog release order ['unreleased', '{version}', ...] in {changelog_path}"
        raise ValueError(msg)
    _validate_release_headings(release_keys, lines)

    unreleased_meta = releases["unreleased"].get("metadata", {})
    version_entry = releases[version]
    version_meta = version_entry.get("metadata", {})

    release_date = str(version_meta.get("release_date") or "")
    if not _DATE_RE.fullmatch(release_date) or "semantic_version" not in version_meta:
        msg = f"Invalid release metadata for {version} in {changelog_path}"
        raise ValueError(msg)

    expected_unreleased_url = f"{repo_url}/compare/v{version}...HEAD"
    version_url = str(version_meta.get("url") or "")
    unreleased_link_line = f"[Unreleased]: {expected_unreleased_url}"
    prev_version = _previous_release_version(release_keys)
    if prev_version is None:
        version_link_prefix = f"[{version}]: {repo_url}/"
        valid_version_link = version_url.startswith(f"{repo_url}/") and any(
            line.startswith(version_link_prefix) for line in lines
        )
    else:
        expected_version_url = f"{repo_url}/compare/v{prev_version}...v{version}"
        valid_version_link = version_url == expected_version_url and f"[{version}]: {expected_version_url}" in lines
    if (
        unreleased_meta.get("url") != expected_unreleased_url
        or unreleased_link_line not in lines
        or not valid_version_link
    ):
        msg = f"Missing or stale compare links for {version} in {changelog_path} footer"
        raise ValueError(msg)

    if not any(key != "metadata" and bool(val) for key, val in version_entry.items()):
        msg = f"Missing or empty CHANGELOG.md section for version {version}"
        raise ValueError(msg)


def verify_and_extract_release_notes(
    changelog_path: Path = DEFAULT_CHANGELOG_PATH,
    *,
    version: str,
    repo_url: str = DEFAULT_REPO_URL,
) -> str:
    """Validate ``CHANGELOG.md`` invariants and extract release notes for ``version``.

    Parameters
    ----------
    changelog_path : Path, optional
        Path to ``CHANGELOG.md``, by default ``DEFAULT_CHANGELOG_PATH``.
    version : str
        Expected release version from ``pyproject.toml``.
    repo_url : str, optional
        Repository base URL for compare links, by default ``DEFAULT_REPO_URL``.

    Returns
    -------
    str
        Extracted Markdown body for ``version`` ending with a single newline.

    Raises
    ------
    ValueError
        If ``CHANGELOG.md`` violates Keep a Changelog structure, heading order,
        compare-link invariants, or has an empty release body.
    """
    lines = changelog_path.read_text(encoding="utf-8").splitlines()
    header_re = re.compile(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$")

    h2_headers = [line for line in lines if _H2_RE.match(line)]
    if len(h2_headers) < _MIN_RELEASES or h2_headers[0] != "## [Unreleased]" or not header_re.match(h2_headers[1]):
        msg = f"Expected '## [Unreleased]' followed by '## [{version}] - YYYY-MM-DD' in {changelog_path}"
        raise ValueError(msg)

    _validate_keepachangelog_metadata(changelog_path, lines, version=version, repo_url=repo_url)

    collecting = False
    collected: list[str] = []
    for line in lines:
        if not collecting:
            if header_re.match(line):
                collecting = True
            continue
        if _H2_RE.match(line) or _FOOTER_LINK_RE.match(line):
            break
        collected.append(line)

    body = "\n".join(collected).strip()
    if not collecting or not body:
        msg = f"Missing or empty CHANGELOG.md section for version {version}"
        raise ValueError(msg)

    return f"{body}\n"


def expected_wheel_members(version: str) -> set[str]:
    """Return the exact set of regular file paths expected in the built wheel.

    Parameters
    ----------
    version : str
        Package semantic version.

    Returns
    -------
    set[str]
        Expected archive member names for ``cuid2-{version}-py3-none-any.whl``.
    """
    dist_info = f"cuid2-{version}.dist-info"
    return {
        "cuid2/__init__.py",
        "cuid2/__main__.py",
        "cuid2/cli.py",
        "cuid2/generator.py",
        "cuid2/utils.py",
        "cuid2/py.typed",
        f"{dist_info}/METADATA",
        f"{dist_info}/WHEEL",
        f"{dist_info}/entry_points.txt",
        f"{dist_info}/RECORD",
        f"{dist_info}/licenses/LICENSE",
    }


def expected_sdist_members(version: str) -> set[str]:
    """Return the exact set of regular file paths expected in the built sdist.

    Parameters
    ----------
    version : str
        Package semantic version.

    Returns
    -------
    set[str]
        Expected archive member names for ``cuid2-{version}.tar.gz``.
    """
    sdist_prefix = f"cuid2-{version}"
    return {
        f"{sdist_prefix}/PKG-INFO",
        f"{sdist_prefix}/README.md",
        f"{sdist_prefix}/LICENSE",
        f"{sdist_prefix}/pyproject.toml",
        f"{sdist_prefix}/pyproject.toml.orig",
        f"{sdist_prefix}/src/cuid2/__init__.py",
        f"{sdist_prefix}/src/cuid2/__main__.py",
        f"{sdist_prefix}/src/cuid2/cli.py",
        f"{sdist_prefix}/src/cuid2/generator.py",
        f"{sdist_prefix}/src/cuid2/utils.py",
        f"{sdist_prefix}/src/cuid2/py.typed",
    }


def verify_dist_archives(dist_dir: Path = DEFAULT_DIST_DIR, *, version: str) -> None:
    """Verify that ``dist_dir`` contains exactly one wheel and one sdist with expected members.

    Parameters
    ----------
    dist_dir : Path, optional
        Directory containing built distributions, by default ``DEFAULT_DIST_DIR``.
    version : str
        Expected package version from ``pyproject.toml``.

    Raises
    ------
    ValueError
        If the wheel/sdist count or archive member list does not match expectations.
    """
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1:
        msg = f"Expected 1 wheel in {dist_dir}, found {wheels}"
        raise ValueError(msg)
    if len(sdists) != 1:
        msg = f"Expected 1 sdist in {dist_dir}, found {sdists}"
        raise ValueError(msg)

    expected_wheel = expected_wheel_members(version)
    with zipfile.ZipFile(wheels[0]) as zf:
        actual_wheel = {info.filename for info in zf.infolist() if not info.is_dir()}
    if actual_wheel != expected_wheel:
        msg = f"Wheel mismatch: {sorted(actual_wheel ^ expected_wheel)}"
        raise ValueError(msg)

    expected_sdist = expected_sdist_members(version)
    with tarfile.open(sdists[0], "r:gz") as tf:
        actual_sdist = {member.name for member in tf.getmembers() if member.isfile()}
    if actual_sdist != expected_sdist:
        msg = f"Sdist mismatch: {sorted(actual_sdist ^ expected_sdist)}"
        raise ValueError(msg)


def _run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git = shutil.which("git")
    if git is None:
        msg = "git executable not found"
        raise ValueError(msg)
    return subprocess.run(  # noqa: S603
        [git, *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _assert_full_history(repo_root: Path) -> None:
    res = _run_git(repo_root, "rev-parse", "--is-shallow-repository")
    if res.returncode != 0:
        msg = f"Failed to query git repository history depth: {res.stderr.strip()}"
        raise ValueError(msg)
    if res.stdout.strip() == "true":
        msg = "Repository is shallow; fetch full history (fetch-depth: 0)"
        raise ValueError(msg)


def _assert_tag_available(repo_root: Path, version: str) -> None:
    if _run_git(repo_root, "rev-parse", "--verify", "--quiet", f"refs/tags/v{version}").returncode == 0:
        msg = f"Release tag v{version} already exists"
        raise ValueError(msg)


def _list_version_tags(repo_root: Path) -> list[str]:
    res = _run_git(repo_root, "tag", "--list", "v*")
    if res.returncode != 0:
        msg = f"Failed to list git tags: {res.stderr.strip()}"
        raise ValueError(msg)
    return res.stdout.splitlines()


def _check_version_vs_tags(version: str, tag_names: Iterable[str]) -> None:
    target = _parse_semver(version)
    major = target[0]
    for tag_name in tag_names:
        if not _TAG_VER_RE.fullmatch(tag_name):
            continue
        tag_ver = tag_name[1:]
        parsed_tag = _parse_semver(tag_ver)
        if parsed_tag[0] == major and target <= parsed_tag:
            msg = f"Version {version} is not greater than existing tag v{tag_ver} on major {major}"
            raise ValueError(msg)


def _assert_version_above_same_major_tags(repo_root: Path, version: str) -> None:
    _check_version_vs_tags(version, _list_version_tags(repo_root))


def _is_latest_version(version: str, tag_names: Iterable[str]) -> bool:
    target = _parse_semver(version)
    return all(target > _parse_semver(tag_name[1:]) for tag_name in tag_names if _TAG_VER_RE.fullmatch(tag_name))


def _project_version_at(repo_root: Path, rev: str, rel_pyproject: str) -> str | None:
    res = _run_git(repo_root, "show", f"{rev}:{rel_pyproject}")
    if res.returncode != 0:
        return None
    try:
        data = tomllib.loads(res.stdout)
    except tomllib.TOMLDecodeError as exc:
        msg = f"Cannot parse {rel_pyproject} at {rev}: {exc}"
        raise ValueError(msg) from exc
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    raw_version = project.get("version")
    return raw_version if isinstance(raw_version, str) else None


def _find_bump_commit(
    repo_root: Path,
    rel_pyproject: str,
    *,
    version: str,
    prev_version: str | None,
) -> str:
    res = _run_git(repo_root, "log", "--first-parent", "--format=%H", "HEAD", "--", rel_pyproject)
    if res.returncode != 0:
        msg = f"Failed to inspect git history for {rel_pyproject}: {res.stderr.strip()}"
        raise ValueError(msg)
    shas = res.stdout.split()
    if not shas:
        msg = f"No first-parent commit reachable from HEAD touches {rel_pyproject}"
        raise ValueError(msg)
    for sha in shas:
        if _COMMIT_SHA_RE.fullmatch(sha) is None:
            msg = f"Invalid commit SHA from git log: {sha}"
            raise ValueError(msg)
    tip = _project_version_at(repo_root, shas[0], rel_pyproject)
    if tip != version:
        msg = f"Committed {rel_pyproject} at HEAD declares version {tip!r}, expected {version}"
        raise ValueError(msg)
    bump = shas[0]
    prev: str | None = None
    for sha in shas[1:]:
        candidate = _project_version_at(repo_root, sha, rel_pyproject)
        if candidate != version:
            prev = candidate
            break
        bump = sha
    if prev_version is not None and prev != prev_version:
        msg = (
            f"Version before release commit {bump} is {prev or 'absent'}, "
            f"but CHANGELOG.md lists previous release {prev_version}"
        )
        raise ValueError(msg)
    return bump


def resolve_release_commit(
    repo_root: Path,
    *,
    pyproject_path: Path,
    version: str,
    prev_version: str | None,
) -> str:
    """Resolve the first-parent commit SHA that bumped ``pyproject.toml`` to ``version``.

    Parameters
    ----------
    repo_root : Path
        Root directory of the git repository.
    pyproject_path : Path
        Path to ``pyproject.toml`` inside ``repo_root``.
    version : str
        Target strict SemVer release version expected at ``HEAD``.
    prev_version : str | None
        Immediately preceding release version from ``CHANGELOG.md``, or ``None`` for an initial release.

    Returns
    -------
    str
        40-character lowercase hexadecimal SHA-1 of the commit that introduced ``version``.

    Raises
    ------
    ValueError
        If ``git`` is unavailable, the repository is shallow, tag ``v{version}`` already exists,
        ``version`` is not greater than every existing strict-SemVer tag of the same major version,
        ``pyproject_path`` is outside ``repo_root``, ``HEAD`` does not declare ``version``, or the
        version immediately preceding the bump commit does not match ``prev_version``.
    """
    _parse_semver(version)
    _assert_full_history(repo_root)
    _assert_tag_available(repo_root, version)
    _assert_version_above_same_major_tags(repo_root, version)
    rel_pyproject = pyproject_path.resolve().relative_to(repo_root.resolve()).as_posix()
    return _find_bump_commit(
        repo_root,
        rel_pyproject,
        version=version,
        prev_version=prev_version,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m local.verify_release",
        description="Verify CHANGELOG.md release invariants and built distribution archives.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    changelog_parser = subparsers.add_parser(
        "changelog",
        help="Validate pyproject.toml version and CHANGELOG.md release notes.",
    )
    changelog_parser.add_argument(
        "--pyproject",
        type=Path,
        default=DEFAULT_PYPROJECT_PATH,
        help="Path to pyproject.toml.",
    )
    changelog_parser.add_argument(
        "--changelog",
        type=Path,
        default=DEFAULT_CHANGELOG_PATH,
        help="Path to CHANGELOG.md.",
    )
    changelog_parser.add_argument(
        "--notes-out",
        type=Path,
        default=None,
        help="Optional path to write the extracted release notes Markdown body.",
    )
    changelog_parser.add_argument(
        "--github-output",
        type=Path,
        default=None,
        help=(
            "Optional path to GITHUB_OUTPUT file to append version=<version> "
            "(plus commit=<sha> and latest=<true|false> with --resolve-commit)."
        ),
    )
    changelog_parser.add_argument(
        "--resolve-commit",
        action="store_true",
        help="Resolve and verify the release commit SHA and tag invariants, printing the SHA to stdout.",
    )

    dist_parser = subparsers.add_parser(
        "dist",
        help="Verify built wheel and sdist archive members in dist/.",
    )
    dist_parser.add_argument(
        "--pyproject",
        type=Path,
        default=DEFAULT_PYPROJECT_PATH,
        help="Path to pyproject.toml.",
    )
    dist_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=DEFAULT_DIST_DIR,
        help="Directory containing built wheel and sdist archives.",
    )

    return parser


def _run_changelog_command(args: argparse.Namespace, *, version: str) -> None:
    notes = verify_and_extract_release_notes(args.changelog, version=version)
    commit_sha: str | None = None
    latest: bool | None = None
    if args.resolve_commit:
        release_keys = list(keepachangelog.to_dict(str(args.changelog), show_unreleased=True))
        prev_version = _previous_release_version(release_keys)
        repo_root = args.pyproject.resolve().parent
        commit_sha = resolve_release_commit(
            repo_root,
            pyproject_path=args.pyproject,
            version=version,
            prev_version=prev_version,
        )
        latest = _is_latest_version(version, _list_version_tags(repo_root))

    if args.notes_out is not None:
        args.notes_out.write_text(notes, encoding="utf-8")
    if commit_sha is not None:
        sys.stdout.write(f"{commit_sha}\n")
    if args.github_output is not None:
        output_lines = [f"version={version}\n"]
        if commit_sha is not None and latest is not None:
            output_lines.append(f"commit={commit_sha}\n")
            output_lines.append(f"latest={'true' if latest else 'false'}\n")
        with args.github_output.open("a", encoding="utf-8") as fh:
            fh.writelines(output_lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for release and distribution verification.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Command-line arguments, by default ``None`` (uses ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit status code (``0`` on success, ``1`` on validation error).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        version = read_project_version(args.pyproject)
        if args.command == "changelog":
            _run_changelog_command(args, version=version)
        elif args.command == "dist":
            verify_dist_archives(args.dist_dir, version=version)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
