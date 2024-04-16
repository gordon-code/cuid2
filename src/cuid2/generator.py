from __future__ import annotations

import time
from math import floor
from secrets import SystemRandom
from typing import TYPE_CHECKING, Callable, Final, Optional, Protocol

from cuid2 import utils

if TYPE_CHECKING:
    from _random import Random

    class FingerprintCallable(Protocol):  # pylint: disable=too-few-public-methods
        def __call__(self: FingerprintCallable, random_generator: Random) -> str: ...


# ~22k hosts before 50% chance of initial counter collision
# with a remaining counter range of 9.0e+15 in JavaScript.
INITIAL_COUNT_MAX: Final[int] = 476782367
DEFAULT_LENGTH: Final = 24
MAXIMUM_LENGTH: Final = 98


class Cuid:  # pylint: disable=too-few-public-methods
    def __init__(
        self: Cuid,
        random_generator: Callable[[], Random] = SystemRandom,
        counter: Callable[[int], Callable[[], int]] = utils.create_counter,
        length: int = DEFAULT_LENGTH,
        fingerprint: FingerprintCallable = utils.create_fingerprint,
    ) -> None:
        """Initialization function for the Cuid class that generates a universally unique,
        base36 encoded string.

        Parameters
        ----------
        random_generator : Callable[[], "Random"], default=SystemRandom
            Used as the base random generator. The default value is `secrets.SystemRandom`, which is a
            cryptographically secure random number generator provided by the Python standard library.
        counter : Callable[[int], Callable[[], int]], default=utils.create_counter
            The `counter` parameter is a callable that creates a counter returning an incremented value each time it
            is called. The `create_counter` function from the `utils` module is used by default.
        length : int, default=DEFAULT_LENGTH (4)
            The length parameter is an integer that determines the maximum length of the generated string.
            It has a default value of DEFAULT_LENGTH (4).
            A length value greater than `MAXIMUM_LENGTH` (98 characters) will raise a ValueError.
        fingerprint : "FingerprintCallable", default=utils.create_fingerprint
            The "fingerprint" parameter is a callable function that generates a unique identifier.

        Raises
        ------
        ValueError
            If the length parameter is greater than `MAXIMUM_LENGTH` (98 characters).
        """
        if length > MAXIMUM_LENGTH:
            msg = "Length must never exceed 98 characters."
            raise ValueError(msg)

        self._random: Random = random_generator()
        self._counter: Callable[[], int] = counter(floor(self._random.random() * INITIAL_COUNT_MAX))
        self._length: int = length
        self._fingerprint: str = fingerprint(random_generator=self._random)

    def generate(self: Cuid, length: Optional[int] = None) -> str:
        """Generates a universally unique, base36 encoded string with a specified length.

        Parameters
        ----------
        length : int, optional
            The length parameter is an optional integer value that specifies the length of the generated string.
            If it is not provided, the default length value provided during class initialization is used.
            A length value greater than `MAXIMUM_LENGTH` (98 characters) will raise a ValueError.

        Returns
        -------
        str
            Starts with a single, random letter, followed by a hash. The hash is generated using a combination of
            the current time in base 36, a random salt, a base 36 counter, and a system fingerprint.
            The length of the returned string is limited by `length`.

        Raises
        ------
        ValueError
            If the length parameter is greater than `MAXIMUM_LENGTH` (98 characters).
        """
        length = length or self._length
        if length > MAXIMUM_LENGTH:
            msg = "Length must never exceed 98 characters."
            raise ValueError(msg)

        first_letter: str = utils.create_letter(random_generator=self._random)

        base36_time: str = utils.base36_encode(time.time_ns())
        base36_count: str = utils.base36_encode(self._counter())

        salt: str = utils.create_entropy(length=length, random_generator=self._random)
        hash_input: str = base36_time + salt + base36_count + self._fingerprint

        return first_letter + utils.create_hash(hash_input)[1 : length or self._length]


def cuid_wrapper() -> Callable[[], str]:
    """Wrap a single Cuid class instance and return a callable that generates a CUID string.

    Returns
    -------
    Callable[[], str]
        A callable that generates a CUID string.
    """
    cuid_generator: Cuid = Cuid()

    def cuid() -> str:
        return cuid_generator.generate()

    return cuid
