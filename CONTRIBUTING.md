# Contribute

This is the contribute.md of our project. Great to have you here.
Here are a few ways you can help make this project better!

If you want to add an issue or pull request, please ensure that
the [existing issues](https://github.com/gordon-code/cuid2/issues)
don't already cover your question or contribution.

## Installation

We recommend using [`uv`](https://docs.astral.sh/uv/)
to isolate dependencies for development and reuse existing workflows.
This guide assumes that you have already installed `uv`.

Clone the repository (alternatively, if you plan on making a pull request and
are not in the cuid2.py organisation, use the [GitHub page](https://github.com/gordon-code/cuid2)
to create your own fork)

```bash
git clone git@github.com:gordon-code/cuid2.git
cd cuid2
```

Ensure that you have installed the package and development dependencies:

```bash
uv sync
```

And finally create a separate branch to begin work

```bash
git checkout -b my-new-feature
```

## Coding Standards and Contribution Requirements

All contributions must meet the following standards (configured in [`pyproject.toml`](pyproject.toml) and [`prek.toml`](prek.toml)):

- **Python compatibility & dependencies:** Code must support Python `>=3.10` (`3.10`–`3.15`) and maintain **zero runtime dependencies**.
- **Code style & formatting ([PEP 8](https://peps.python.org/pep-0008/) / [`ruff`](https://docs.astral.sh/ruff/)):** Source and test files are formatted with `ruff format` and linted with `ruff check` (`select = ["ALL"]`, 120-character maximum line length, `from __future__ import annotations` in every module, and `isort` import ordering).
- **Docstrings ([NumPy docstring standard](https://numpydoc.readthedocs.io/en/latest/format.html)):** All public modules, classes, and functions require NumPy-style docstrings (`[tool.ruff.lint.pydocstyle] convention = "numpy"`).
- **Static typing ([PEP 484](https://peps.python.org/pep-0484/) / [PEP 604](https://peps.python.org/pep-0604/)):** All code must be fully type-annotated and pass `mypy --strict`, `pyright` (`strict = ["src"]`), and 100% public symbol type completeness via `pyright --verifytypes cuid2 --ignoreexternal`.
- **Testing ([`pytest`](https://docs.pytest.org/) & [`hypothesis`](https://hypothesis.readthedocs.io/)):** Bug fixes and new features must include unit tests (and property-based tests where appropriate) in `local/tests/`, and the full test suite must pass under `pytest` (`strict = true`, `filterwarnings = ["error"]`) with 100% branch coverage on `cuid2` via `pytest-cov` (`fail_under = 100`).
- **Documentation, spelling, & workflows:** Markdown files must pass [`rumdl`](https://github.com/rvben/rumdl) (`rumdl check` and `rumdl fmt --check`), all repository files must pass [`codespell`](https://github.com/codespell-project/codespell), and GitHub Actions workflow changes must pass [`actionlint`](https://github.com/rhysd/actionlint) and [`zizmor`](https://docs.zizmor.sh/) (`--persona=pedantic`).
- **Commit messages & licensing:** Commits and pull request titles follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) (`type(scope): description`). By submitting a contribution, you agree to license your work under the project's [MIT License](LICENSE).

## Preparing your commit

We rely on a number of formatters, linters, and tests to ensure that
the codebase is consistent and free from regressions. Running with
`uv run ruff check --fix && uv run ruff format && uv run rumdl fmt`
enables quick updates to files during development. You can also install and run the parallel pre-commit hooks via [`prek`](https://github.com/j178/prek) (`uv run prek install && uv run prek run --all-files`).

Prior to committing, run the full test, static-analysis, and workflow-linting suite (`pytest`, `ruff`, `codespell`, `rumdl`, `mypy --strict`, `pyright`, `pyright --verifytypes`, `verify-changelog`, `zizmor`, and `actionlint`):

```bash
uv run prek run --all-files
```

You can also audit GitHub Actions workflows directly with `uv run zizmor --persona=pedantic .github/workflows`.

To catch collision or performance regressions locally, the `@pytest.mark.slow` suite (the 50k-ID generation benchmark and bounded 3M-ID statistical collision suite) runs automatically on `git push` via the `pre-push` hook in `prek.toml` and in PR CI, or can be invoked directly:

```bash
uv run pytest --no-cov -m slow
```

The 100M-ID `@pytest.mark.heavy` cases (`-m heavy`) are intended for scheduled/manual CI via [`.github/workflows/collision.yml`](.github/workflows/collision.yml) rather than developer laptops.

The `hypothesis` property tests in `local/tests/test_fuzz.py` search new random inputs on every run, locally and in CI. A failure prints the falsifying example and an `@reproduce_failure(...)` decorator that replays it. For a longer search (10,000 examples per test, also run weekly in `collision.yml`), use the `deep` profile:

```bash
uv run pytest --no-cov --hypothesis-profile=deep local/tests/test_fuzz.py
```

## Changelog

Pull requests that change behavior, packaging, or documentation that consumers read should add a brief, user-facing entry under `## [Unreleased]` in `CHANGELOG.md` using the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) categories (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`). Repository, CI, test, tooling, and dependency hygiene is folded into a single `Internal:` bullet under `### Changed` for the release rather than itemized per PR. Contributor pull requests do not bump the package version; the maintainer bumps the version in the release PR.

To cut a release:

1. Open a release PR that renames `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`, adds a fresh empty `## [Unreleased]` section above it, bumps `version` in `pyproject.toml` and `uv.lock`, and updates the compare-link footer in `CHANGELOG.md` (adds `[X.Y.Z]` comparing `v<prev>...vX.Y.Z` and updates `[Unreleased]` to `compare/vX.Y.Z...HEAD`).
2. After the release PR merges to `main`, dispatch `.github/workflows/build_release.yml` from `main` and approve the `pypi` environment deployment when prompted (the workflow reads the version from `pyproject.toml`, validates and extracts the matching `## [X.Y.Z]` section from `CHANGELOG.md` via `local.verify_release`, verifies and attests SLSA build provenance for the built sdist and wheel via `actions/attest`, publishes distributions with PEP 740 attestations via `pypa/gh-action-pypi-publish`, and creates the GitHub release tagged at the built commit). Verify the published attestations via `gh attestation verify <dist> --owner gordon-code` and at `https://pypi.org/integrity/cuid2/<version>/<wheel>/provenance`.

## Submitting Pull Requests

Pull requests are welcomed! We'd like to review the design and implementation as early as
possible so please submit the pull request even if it's not 100%.
Let us know the purpose of the change and list the remaining items which need to be
addressed before merging. Finally, PR's should include unit tests and documentation
where appropriate.

If you have further questions, contact us at <dev@gordoncode.dev>.
