from typing import Iterator

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add a command line option to pytest to run slow tests.

    Parameters
    ----------
    parser: pytest.Parser
        Used to define and parse command-line arguments for the pytest test runner.
    """
    parser.addoption("--runslow", action="store_true", default=False, help="run slow tests")


def pytest_configure(config: pytest.Config) -> None:
    """Add a custom marker "slow" to pytest configuration to mark tests as slow to run.

    Parameters
    ----------
    config: pytest.Config
        Provides access to the configuration of the pytest framework. It allows you to modify the behavior of pytest
        by setting various options and parameters. In this specific case, the `config` object is used to add a custom
        marker to pytest, which can be used to run or skip slow tests.
    """
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config: pytest.Config, items: Iterator[pytest.Item]) -> None:
    """Skip tests marked as "slow" unless the "--runslow" option is given in the command line.

    Parameters
    ----------
    config: pytest.Config
        Provides access to the configuration of the pytest framework. It allows you to modify the behavior of pytest
        by setting various options and parameters. In this specific case, the `config` object is used to add a custom
        marker to pytest, which can be used to run or skip slow tests.
    items: Iterator[pytest.Item]
        List of all the test items collected by pytest during test discovery. Each item represents a single test
        function or method. The `pytest_collection_modifyitems` function is a hook that allows you to modify this
        list of items before the tests are run
    """
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
