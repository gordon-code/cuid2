# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html), except that 2.0.2 and 2.0.3 shipped breaking and deprecation changes in patch releases (see their notes).

This repository continues the `overflowdigital` `cuid2` package (`b02c8ca`); versions below 1.3.0 were not published from here, and no entries are invented for them.

## [Unreleased]

### Changed

- Faster ID generation and cold-start imports via single-draw `getrandbits` MSB fixed-point entropy and letter generation (`< 2^-64` bias), leading-digit base36 SHA3-512 hash encoding, reduced lock and reference-count contention on free-threaded Python (`3.14t` and `3.15t`), and deferred `inspect` and `socket` imports.
- Custom `random_generator` instances must implement `.getrandbits(k)` (typed as `random.Random` instead of `_random.Random`), and seeded `random.Random` generators produce a different sequence of IDs than in `2.2.0`.

## [2.2.0] - 2026-10-30

### Added

- Python 3.15 and free-threaded Python 3.14t and 3.15t support in CI and package classifiers (`Programming Language :: Python :: Free Threading :: 3 - Stable`).
- `Changelog` and `Issues` project URLs in the package metadata.
- CLI flags `-V`/`--version`, `-l`/`--length`, `--slug` (5-character short ID preset), `-n`/`-c`/`--count`, `-f`/`--fingerprint` (used verbatim as the fingerprint, as in `@paralleldrive/cuid2`), and `--check`/`--validate` (with `-` `stdin`, skipping blank lines, and `-q`/`--quiet` support), plus `python -m cuid2` module execution. A count below `1` or an empty fingerprint exits with code `2`.

### Changed

- `cuid_wrapper()` is no longer deprecated and now returns `functools.partial(create_id, length=length)`, making it picklable and directly usable as a Django migration `default=` callable (passing an extra positional argument now raises `TypeError: create_id() got multiple values for argument 'length'`, and passing `length=...` by keyword overrides the bound length).
- Internal: strengthened `ruff`, `mypy`, and `pyright` static checking, enabled `pytest` 9 strict mode and 100% branch coverage enforcement, added `hypothesis` + `atheris` property-based fuzzing and bounded-memory statistical collision testing in CI, added `rumdl` markdown linting/formatting, `zizmor` and `actionlint` workflow linting, `prek.toml` pre-commit hooks, and OpenSSF Scorecard analysis, set a fixed CodeQL analysis category shared by the CI and release workflows, hardened the release pipeline with SLSA build provenance and PEP 740 PyPI attestations plus `CHANGELOG.md` release notes, extended `codespell` to repository documentation, and removed `pylint` and `tox`.

### Fixed

- CLI out-of-range lengths (`<= 0` or `> 98`) now exit with code `2` and an `argparse` usage error on `stderr` instead of an uncaught `ValueError` traceback.
- `Cuid`, `create_id()`, `cuid_wrapper()`, and `utils.create_counter()` are now thread-safe (synchronizing counter increments, lazy singleton initialization, and per-instance stateful draws across threads, including free-threaded Python, where unsynchronized counters returned roughly 323,000–380,000 unique values from 1,600,000 calls on 8 threads, with re-entrant locks so a signal handler or finalizer that generates an ID cannot deadlock) and fork-safe (the first ID generated in a forked child process, including uWSGI workers that skip Python's fork hooks, rebuilds the lock, RNG state, counter, and child-PID fingerprint once, even when several child threads race; fixed-seed `random_generator` factories still give every child the same stream).
- `copy.deepcopy()` of a `Cuid` now returns an independent generator that shares the factories and builds fresh RNG state, counter, and fingerprint, instead of raising `NotImplementedError` for the default `SystemRandom` or cloning a seeded generator's stream and sharing its counter.

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

[Unreleased]: https://github.com/gordon-code/cuid2/compare/v2.2.0...HEAD
[2.2.0]: https://github.com/gordon-code/cuid2/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/gordon-code/cuid2/compare/v2.0.4...v2.1.0
[2.0.4]: https://github.com/gordon-code/cuid2/compare/v2.0.3...v2.0.4
[2.0.3]: https://github.com/gordon-code/cuid2/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/gordon-code/cuid2/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/gordon-code/cuid2/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/gordon-code/cuid2/compare/v1.3.0...v2.0.0
[1.3.0]: https://github.com/gordon-code/cuid2/releases/tag/v1.3.0
