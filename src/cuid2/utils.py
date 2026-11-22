"""Cryptographic hashing, entropy, counter, fingerprint, and base36 helpers for CUID2."""

from __future__ import annotations

import os
import threading
from functools import partial
from hashlib import sha3_512
from math import floor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from random import Random
    from typing import Final

# ~25.7k hosts before 50% chance of initial counter collision
# with a remaining counter range of 9.0e+15 in JavaScript.
INITIAL_COUNT_MAX: Final[int] = 476782367
MIN_LENGTH: Final[int] = 2
DEFAULT_LENGTH: Final[int] = 24
BIG_LENGTH: Final[int] = 32

ASCII_LOWERCASE: Final[str] = "abcdefghijklmnopqrstuvwxyz"
ASCII_LOWERCASE_LEN: Final[int] = len(ASCII_LOWERCASE)
BASE36_ALPHABET: Final[str] = "0123456789abcdefghijklmnopqrstuvwxyz"
BASE36_RADIX: Final[int] = len(BASE36_ALPHABET)

_OVERSAMPLE_BITS: Final[int] = 64
_COUNTER_DRAW_BITS: Final[int] = INITIAL_COUNT_MAX.bit_length() + _OVERSAMPLE_BITS
_POWERS_OF_36: Final[tuple[int, ...]] = tuple(BASE36_RADIX**i for i in range(101))
_HASH_MIN_99_DIGITS: Final[int] = _POWERS_OF_36[98]
_HASH_MIN_100_DIGITS: Final[int] = _POWERS_OF_36[99]


def _uses_random_only(random_generator: Random) -> bool:
    # Generators without getrandbits(), and random.Random subclasses whose nearest definition is random() rather
    # than getrandbits() (mirroring random.Random.__init_subclass__), supply their own core generator through
    # random() alone; they are drawn from with one floor(random() * n) call per character, never through the
    # inherited getrandbits(), so random() of any resolution keeps its full per-character entropy.
    if getattr(random_generator, "getrandbits", None) is None:
        return True
    for klass in type(random_generator).__mro__:
        namespace = vars(klass)
        if "getrandbits" in namespace:
            return False
        if "random" in namespace:
            return True
    return False


def _scale_randbits(bits: int, upper_bound: int, draw_bits: int) -> int:
    return (bits * upper_bound) >> draw_bits


def _create_initial_count(random_generator: Random) -> int:  # pyright: ignore[reportUnusedFunction]
    if _uses_random_only(random_generator):
        return floor(random_generator.random() * INITIAL_COUNT_MAX)
    return _scale_randbits(
        random_generator.getrandbits(_COUNTER_DRAW_BITS),
        INITIAL_COUNT_MAX,
        _COUNTER_DRAW_BITS,
    )


def _entropy_from_scaled(scaled: int, length: int) -> str:
    alphabet: str = BASE36_ALPHABET
    chars: list[str] = []
    for _ in range(length):
        scaled, mod = divmod(scaled, BASE36_RADIX)
        chars.append(alphabet[mod])
    return "".join(chars)


def _letter_via_random(random_generator: Random) -> str:
    return ASCII_LOWERCASE[floor(random_generator.random() * ASCII_LOWERCASE_LEN)]


def _entropy_via_random(random_generator: Random, length: int) -> str:
    return "".join([BASE36_ALPHABET[floor(random_generator.random() * BASE36_RADIX)] for _ in range(length)])


def _letter_and_entropy_via_getrandbits(getrandbits: Callable[[int], int], length: int) -> tuple[str, str]:
    entropy_modulus: int = _POWERS_OF_36[length]
    modulus: int = ASCII_LOWERCASE_LEN * entropy_modulus
    draw_bits: int = modulus.bit_length() + _OVERSAMPLE_BITS
    letter_idx, entropy_scaled = divmod(_scale_randbits(getrandbits(draw_bits), modulus, draw_bits), entropy_modulus)
    return ASCII_LOWERCASE[letter_idx], _entropy_from_scaled(entropy_scaled, length)


def _letter_and_entropy_via_random(random_generator: Random, length: int) -> tuple[str, str]:
    return _letter_via_random(random_generator), _entropy_via_random(random_generator, length)


def _letter_and_entropy_source(  # pyright: ignore[reportUnusedFunction]
    random_generator: Random,
) -> Callable[[int], tuple[str, str]]:
    if _uses_random_only(random_generator):
        return partial(_letter_and_entropy_via_random, random_generator)
    return partial(_letter_and_entropy_via_getrandbits, random_generator.getrandbits)


def _create_hash_slice(data: str, start: int, stop: int) -> str:
    hashed_int: int = int.from_bytes(sha3_512(data.encode()).digest(), byteorder="big")
    raw_start: int = start + 1
    raw_stop: int = stop + 1
    # Callers pass stop <= BIG_LENGTH. The division fast path is valid only for stop <= 98: with a 99-digit digest and
    # a larger stop, _POWERS_OF_36[total_digits - raw_stop] would index from the end and return a wrong slice.
    if hashed_int >= _HASH_MIN_99_DIGITS:
        total_digits: int = 100 if hashed_int >= _HASH_MIN_100_DIGITS else 99
        return base36_encode(hashed_int // _POWERS_OF_36[total_digits - raw_stop])[raw_start:raw_stop]
    return base36_encode(hashed_int)[raw_start:raw_stop]


def create_counter(count: int) -> Callable[[], int]:
    """Create a thread-safe counter that returns an incremented value each time it is called.

    Parameters
    ----------
    count : int
        Initial count value for the counter.

    Returns
    -------
    Callable[[], int]
        Closure function `counter` that takes no arguments and returns an integer. The closure function keeps track
        of a count variable that is initialized with the value passed as an argument to `create_counter`. Each time
        the closure function is called, it atomically increments the count variable under a lock and returns its
        new value.
    """
    lock = threading.RLock()

    def counter() -> int:
        nonlocal count
        with lock:
            count += 1
            return count

    return counter


def create_fingerprint(random_generator: Random, fingerprint_data: str | None = "") -> str:
    """Create a host/process fingerprint combined with random entropy and hashed.

    Parameters
    ----------
    random_generator : random.Random
        Random number generator used to generate fingerprint entropy. Its `.getrandbits(k)` is used; a generator
        without `.getrandbits(k)`, or whose class defines `.random()` but not `.getrandbits(k)` (such as a
        `random.Random` subclass overriding only `.random()`), is drawn from with one `.random()` call per character.
    fingerprint_data : str, optional
        An optional parameter that contains data to be included in the fingerprint.
        If it is not provided, the function combines process ID, hostname, and environment variables

    Returns
    -------
    str
        The hashed value of the input `fingerprint_data` or default value concatenated with a randomly generated
        entropy string.
        The length of the returned string is trimmed to the constant `BIG_LENGTH` (32 characters).
    """
    if not fingerprint_data:
        import socket  # noqa: PLC0415

        process_id: int = os.getpid()
        hostname: str = socket.gethostname()
        env_variables: str = "".join(os.environ.keys())

        fingerprint_data = str(process_id) + hostname + env_variables

    fingerprint: str = str(fingerprint_data) + create_entropy(random_generator, BIG_LENGTH)
    return _create_hash_slice(fingerprint, 0, BIG_LENGTH)


def create_entropy(random_generator: Random, length: int = 4) -> str:
    """Create a random string of specified length using base36 encoding.

    Parameters
    ----------
    random_generator : random.Random
        Random number generator used to generate a random string. Its `.getrandbits(k)` is used; a generator
        without `.getrandbits(k)`, or whose class defines `.random()` but not `.getrandbits(k)` (such as a
        `random.Random` subclass overriding only `.random()`), is drawn from with one `.random()` call per character.
    length : int, default=4
        The length parameter is an integer that specifies the length of the entropy string to be generated.
        The default value is 4, but it can be set to any positive integer value.

    Returns
    -------
    str
        Random characters encoded as a base36 string. The length of the string is determined by
        the `length` parameter passed to the function.

    Raises
    ------
    ValueError
        If the input integer is less than 1.
    """
    if length < 1:
        msg = "Cannot create entropy without a length >= 1."
        raise ValueError(msg)

    if _uses_random_only(random_generator):
        return _entropy_via_random(random_generator, length)

    modulus: int = _POWERS_OF_36[length] if length < len(_POWERS_OF_36) else BASE36_RADIX**length
    draw_bits: int = modulus.bit_length() + _OVERSAMPLE_BITS
    scaled: int = _scale_randbits(random_generator.getrandbits(draw_bits), modulus, draw_bits)
    return _entropy_from_scaled(scaled, length)


def base36_encode(number: int) -> str:
    """Encode a non-negative integer into a base36 string.

    Parameters
    ----------
    number : int
        Integer to be encoded as a base36 string.

    Returns
    -------
    str
        A string that represents the base36 encoded input integer.
        If the input integer is negative, a ValueError is raised.
        If the input integer is 0, the function returns the string "0".

    Raises
    ------
    ValueError
        If the input integer is negative.
    """
    if number < 0:
        msg = "Cannot encode negative integers."
        raise ValueError(msg)

    if number == 0:
        return "0"

    alphabet: str = BASE36_ALPHABET
    encoded_chars: list[str] = []
    while number != 0:
        number, mod = divmod(number, BASE36_RADIX)
        encoded_chars.append(alphabet[mod])

    encoded_chars.reverse()
    return "".join(encoded_chars)
