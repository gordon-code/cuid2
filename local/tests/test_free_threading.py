from __future__ import annotations

import ast
import re
import sys
import sysconfig
from pathlib import Path

import pytest

TEST_WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "test_lint_scan.yml"
# PEP 779 made free-threaded builds officially supported starting with Python 3.14.
FIRST_SUPPORTED_FREE_THREADED = (3, 14)


def _ci_python_versions() -> list[str]:
    """Return the `python-version` matrix entries of the CI test job."""
    match = re.search(r"^\s*python-version:\s*(\[.*\])\s*$", TEST_WORKFLOW.read_text(encoding="utf-8"), re.MULTILINE)
    assert match is not None, f"python-version matrix not found in {TEST_WORKFLOW}"
    versions: list[str] = ast.literal_eval(match.group(1))
    return versions


@pytest.mark.skipif(not sysconfig.get_config_var("Py_GIL_DISABLED"), reason="free-threaded build required")
def test_free_threaded_build_runs_without_gil() -> None:
    """Tests that no imported module re-enabled the GIL, so free-threaded CI jobs exercise real parallelism."""
    if sys.version_info >= (3, 13):
        assert not sys._is_gil_enabled()


def test_ci_matrix_tests_free_threaded_build_for_each_supported_python() -> None:
    """Tests that every CI Python version from 3.14 on also runs as a free-threaded ("t") build."""
    versions = _ci_python_versions()
    expected = {
        f"{version}t"
        for version in versions
        if not version.endswith("t") and tuple(map(int, version.split("."))) >= FIRST_SUPPORTED_FREE_THREADED
    }
    assert expected
    assert expected <= set(versions), f"missing free-threaded CI jobs: {sorted(expected - set(versions))}"
