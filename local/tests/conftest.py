from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def _reset_default_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restore _default_generator after each test without importing cuid2 before coverage starts."""
    generator_mod = sys.modules.get("cuid2.generator")
    if generator_mod is not None:
        monkeypatch.setattr(generator_mod, "_default_generator", generator_mod._default_generator)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command-line options to pytest to run slow and heavy tests.

    Parameters
    ----------
    parser : pytest.Parser
        Used to define and parse command-line arguments for the pytest test runner.
    """
    parser.addoption("--runslow", action="store_true", default=False, help="run slow tests")
    parser.addoption(
        "--run-heavy",
        action="store_true",
        default=False,
        help="run heavy (>=10M IDs) collision tests",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip slow and heavy tests unless their respective CLI flags are passed.

    Parameters
    ----------
    config : pytest.Config
        Provides access to the configuration of the pytest framework.
    items : list[pytest.Item]
        List of all test items collected by pytest during test discovery.
    """
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    if not config.getoption("--run-heavy"):
        skip_heavy = pytest.mark.skip(reason="need --run-heavy option to run")
        for item in items:
            if "heavy" in item.keywords:
                item.add_marker(skip_heavy)
