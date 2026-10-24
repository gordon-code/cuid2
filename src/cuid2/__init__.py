"""Next generation GUIDs. Collision-resistant ids optimized for horizontal scaling and performance."""

from .generator import (
    BIG_LENGTH,
    DEFAULT_LENGTH,
    INITIAL_COUNT_MAX,
    MAXIMUM_LENGTH,
    MIN_LENGTH,
    Cuid,
    cuid_wrapper,
)

__all__ = [
    "BIG_LENGTH",
    "DEFAULT_LENGTH",
    "INITIAL_COUNT_MAX",
    "MAXIMUM_LENGTH",
    "MIN_LENGTH",
    "Cuid",
    "cuid_wrapper",
]
