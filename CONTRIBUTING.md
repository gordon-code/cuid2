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

## Preparing your commit

We rely on a number of formatters, linters, and tests to ensure that
the codebase is consistent and free from regressions. Running with
`uv run ruff check --fix && uv run ruff format && uv run rumdl fmt`
enables quick updates to files during development. You can also install and run the parallel pre-commit hooks via [`prek`](https://github.com/j178/prek) (`prek install && prek run --all-files`).

Prior to committing, run the full test, static-analysis, and workflow-linting suite (`pytest`, `ruff`, `codespell`, `rumdl`, `mypy --strict`, `pyright`, `pyright --verifytypes`, `zizmor`, and `actionlint`):

```bash
prek run --all-files
```

You can also audit GitHub Actions workflows directly with `uv run zizmor --persona=pedantic .github/workflows`.

To catch any collision regressions, you may also run `uv run pytest --runslow` locally. The test takes approximately 40 minutes.

## Changelog

Pull requests that change behavior, packaging, or documentation that consumers read should add a brief, user-facing entry under `## [Unreleased]` in `CHANGELOG.md` using the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) categories (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`). Repository, CI, test, tooling, and dependency hygiene is folded into a single `Internal:` bullet under `### Changed` for the release rather than itemized per PR. Contributor pull requests do not bump the package version; the maintainer bumps the version in the release PR.

To cut a release:

1. Open a release PR that renames `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`, adds a fresh empty `## [Unreleased]` section above it, bumps `version` in `pyproject.toml` and `uv.lock`, and updates the compare-link footer in `CHANGELOG.md` (adds `[X.Y.Z]` comparing `v<prev>...vX.Y.Z` and updates `[Unreleased]` to `compare/vX.Y.Z...HEAD`).
2. After the release PR merges to `main`, dispatch `.github/workflows/build_release.yml` from `main` and approve the `pypi` environment deployment when prompted (the workflow reads the version from `pyproject.toml`, extracts the matching `## [X.Y.Z]` section from `CHANGELOG.md`, verifies the built sdist and wheel, publishes distributions with PEP 740 attestations via `pypa/gh-action-pypi-publish`, and creates the GitHub release tagged at the built commit). Verify the published attestation at `https://pypi.org/integrity/cuid2/<version>/<wheel>/provenance`.

## Submitting Pull Requests

Pull requests are welcomed! We'd like to review the design and implementation as early as
possible so please submit the pull request even if it's not 100%.
Let us know the purpose of the change and list the remaining items which need to be
addressed before merging. Finally, PR's should include unit tests and documentation
where appropriate.

If you have further questions, contact us at <dev@gordoncode.dev>.
