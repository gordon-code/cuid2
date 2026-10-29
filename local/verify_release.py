"""Release verification and changelog extraction helpers for CI and pre-commit."""

from __future__ import annotations

import argparse
import re
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import keepachangelog

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from collections.abc import Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"
DEFAULT_CHANGELOG_PATH = _REPO_ROOT / "CHANGELOG.md"
DEFAULT_DIST_DIR = _REPO_ROOT / "dist"
DEFAULT_REPO_URL = "https://github.com/gordon-code/cuid2"

_MIN_RELEASES = 2
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_H2_RE = re.compile(r"^## ")
_FOOTER_LINK_RE = re.compile(r"^\[[^\]]+\]:\s*https?://")


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
    version_link_prefix = f"[{version}]: {repo_url}/"
    if (
        unreleased_meta.get("url") != expected_unreleased_url
        or not version_url.startswith(f"{repo_url}/")
        or unreleased_link_line not in lines
        or not any(line.startswith(version_link_prefix) for line in lines)
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
        help="Optional path to GITHUB_OUTPUT file to append version=<version>.",
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
            notes = verify_and_extract_release_notes(args.changelog, version=version)
            if args.notes_out is not None:
                args.notes_out.write_text(notes, encoding="utf-8")
            if args.github_output is not None:
                with args.github_output.open("a", encoding="utf-8") as fh:
                    fh.write(f"version={version}\n")
        elif args.command == "dist":
            verify_dist_archives(args.dist_dir, version=version)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
