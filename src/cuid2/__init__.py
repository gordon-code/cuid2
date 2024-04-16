"""Next generation GUIDs. Collision-resistant ids optimized for horizontal scaling and performance."""

from .generator import DEFAULT_LENGTH, INITIAL_COUNT_MAX, Cuid, cuid_wrapper

__all__ = ["Cuid", "DEFAULT_LENGTH", "INITIAL_COUNT_MAX", "cuid_wrapper"]
