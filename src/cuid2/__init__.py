"""Next generation GUIDs. Collision-resistant ids optimized for horizontal scaling and performance."""

from cuid2.generator import Cuid, create_id, cuid_wrapper, is_cuid
from cuid2.utils import BIG_LENGTH, DEFAULT_LENGTH, INITIAL_COUNT_MAX, MAXIMUM_LENGTH, MIN_LENGTH

__all__ = [
    "BIG_LENGTH",
    "DEFAULT_LENGTH",
    "INITIAL_COUNT_MAX",
    "MAXIMUM_LENGTH",
    "MIN_LENGTH",
    "Cuid",
    "create_id",
    "cuid_wrapper",
    "is_cuid",
]
