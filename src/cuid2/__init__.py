"""Next generation GUIDs. Collision-resistant ids optimized for horizontal scaling and performance."""

from .generator import CUID, DEFAULT_LENGTH, INITIAL_COUNT_MAX, Cuid

__all__ = ["Cuid", "CUID", "DEFAULT_LENGTH", "INITIAL_COUNT_MAX"]
