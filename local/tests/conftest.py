from __future__ import annotations

import sys
from weakref import WeakSet

import pytest
from hypothesis import settings

settings.register_profile("ci", settings.get_profile("ci"), derandomize=False)
settings.register_profile("deep", settings.get_profile("ci"), max_examples=10_000)


@pytest.fixture(autouse=True)
def _reset_default_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restore _default_generator and _instances after each test without importing cuid2 before coverage starts."""
    generator_mod = sys.modules.get("cuid2.generator")
    if generator_mod is not None:
        monkeypatch.setattr(generator_mod, "_default_generator", generator_mod._default_generator)
        monkeypatch.setattr(generator_mod, "_instances", WeakSet(generator_mod._instances))
