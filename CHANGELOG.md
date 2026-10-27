# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html), except that 2.0.2 and 2.0.3 shipped breaking and deprecation changes in patch releases (see their notes).

This repository continues the `overflowdigital` `cuid2` package (`b02c8ca`); versions below 1.3.0 were not published from here, and no entries are invented for them.

## [Unreleased]

### Added

- `Changelog` and `Issues` project URLs in the package metadata.

### Changed

- Internal: strengthened `ruff`, `mypy`, and `pyright` static checking, added `rumdl` markdown linting/formatting and `prek.toml` pre-commit hooks, extended `codespell` to repository documentation, and removed redundant `pylint`.

## [2.1.0] - 2026-10-25

### Added

- Top-level `create_id()` and `is_cuid()` functions for generating and validating CUID2 strings without instantiating `Cuid`.

## [2.0.4] - 2026-10-25

### Changed

- Faster ID generation via base36 and entropy hot-path optimizations, no behavior change.

## [2.0.3] - 2026-10-24

### Added

- Spec length constants (`MIN_LENGTH`, `BIG_LENGTH`, `MAXIMUM_LENGTH`) exported from `cuid2`.

### Deprecated

- Any `length` argument of `1` or `33`–`98` (`Cuid`, `generate`, `cuid_wrapper`) now emits `DeprecationWarning` (outside the CUID2 spec range 2–32; 3.0.0 will turn this into an error).

## [2.0.2] - 2026-10-24

Spans 49 commits since 2.0.1 over 2.5 years; the Python 3.8 drop (#24, merged 2026-04-17) and Python 3.9 drop (#29, merged 2026-07-23) were merged long before this release.

### Added

- Optional `length` argument for the `cuid2` CLI and for `cuid_wrapper(length)`.
- `Cuid.is_cuid` static method for validating CUID2 strings and length bounds.

### Changed

- Dropped Python 3.8 and 3.9 support (`Requires-Python: >=3.10`) and updated the supported-Python classifiers to 3.10–3.14.
- Invalid lengths now raise `ValueError` immediately (at `Cuid()`/`cuid_wrapper()` construction or at the `generate()` call), whereas in 2.0.1 `generate(0)` and `generate(False)` silently used the default length, `Cuid(length=True)` and `generate(True)` produced a 1-character ID, and `Cuid(length=0)` or a negative length failed only on the first `generate()`.
- Internal: build and dependency management migrated from PDM to `uv`/`uv_build`, Renovate replaced Dependabot, SPDX license metadata updated, and CI/tooling and dependency updates.

**Upgrade note:** 2.0.2 requires Python 3.10+, and invalid lengths now raise `ValueError` immediately: `generate(0)` and `generate(False)` no longer silently use the default length, and `True` no longer produces a 1-character ID.

## [2.0.1] - 2024-04-16

### Changed

- Internal: CI now tests Python 3.12, tooling and dependency updates.

## [2.0.0] - 2023-05-21

### Added

- Public `cuid_wrapper()` helper function exported in `__all__`.
- `cuid2` console script entry point (`cuid2.cli:main`).

### Changed

- Internal: CI runner and GitHub Actions workflow updates.

### Removed

- Deprecated `CUID` class (#2).

**Upgrade note:** Breaking: `CUID` removed; use `Cuid` (or `cuid_wrapper()`).

## [1.3.0] - 2023-05-19

### Changed

- First release from this repository, refactored to the latest CUID2 spec (`1342a13`).
- Internal: GitHub Actions workflow updates.

[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0
[2.0.4]: https://github.com/gordon-code/cuid2/compare/v2.0.3...v2.0.4
[2.0.3]: https://github.com/gordon-code/cuid2/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/gordon-code/cuid2/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/gordon-code/cuid2/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/gordon-code/cuid2/compare/v1.3.0...v2.0.0
[1.3.0]: https://github.com/gordon-code/cuid2/releases/tag/v1.3.0
