from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def _reset_default_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restore _default_generator after each test without importing cuid2 before coverage starts."""
    generator_mod = sys.modules.get("cuid2.generator")
    if generator_mod is not None:
        monkeypatch.setattr(generator_mod, "_default_generator", generator_mod._default_generator)
