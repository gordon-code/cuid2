from __future__ import annotations

import inspect
import re
import time
import warnings
from math import floor
from secrets import SystemRandom
from typing import TYPE_CHECKING, Callable, Final, Optional, Protocol

from cuid2 import utils
from cuid2.utils import BIG_LENGTH, DEFAULT_LENGTH, INITIAL_COUNT_MAX, MAXIMUM_LENGTH, MIN_LENGTH

if TYPE_CHECKING:
    from _random import Random

    class FingerprintCallable(Protocol):  # pylint: disable=too-few-public-methods
        def __call__(self: FingerprintCallable, random_generator: Random) -> str: ...


_CUID_REGEX: Final[re.Pattern[str]] = re.compile(r"^[a-z][0-9a-z]+\Z")


def _validate_length(length: int) -> None:
    """Validate that the requested CUID length is within supported bounds.

    Parameters
    ----------
    length : int
        The requested CUID length to validate.

    Raises
    ------
    ValueError
        If `length` is a boolean, less than 1, or greater than `MAXIMUM_LENGTH` (98).

    Warns
    -----
    DeprecationWarning
        If `length` is outside the CUID2 specification range (`MIN_LENGTH`..`BIG_LENGTH`, i.e., 2..32).
    """
    if isinstance(length, bool) or length < 1:
        msg = "Length must be at least 1 character."
        raise ValueError(msg)
    if length > MAXIMUM_LENGTH:
        msg = "Length must never exceed 98 characters."
        raise ValueError(msg)
    if length < MIN_LENGTH or length > BIG_LENGTH:
        stacklevel: int = 1
        frame = inspect.currentframe()
        while frame is not None and frame.f_code.co_filename == __file__:
            stacklevel += 1
            frame = frame.f_back
        warnings.warn(
            f"Length {length} outside the CUID2 specification range ({MIN_LENGTH}..{BIG_LENGTH}) "
            "is deprecated and will raise ValueError in v3.0.0.",
            DeprecationWarning,
            stacklevel=stacklevel,
        )


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
        length : int, default=DEFAULT_LENGTH (24)
            The length parameter is an integer that determines the maximum length of the generated string.
            It has a default value of DEFAULT_LENGTH (24).
            A length value less than 1 or greater than `MAXIMUM_LENGTH` (98 characters) will raise a ValueError.
            Lengths outside `MIN_LENGTH`..`BIG_LENGTH` (2..32) emit a DeprecationWarning.
        fingerprint : "FingerprintCallable", default=utils.create_fingerprint
            The "fingerprint" parameter is a callable function that generates a unique identifier.

        Raises
        ------
        ValueError
            If the length parameter is a boolean, less than 1, or greater than `MAXIMUM_LENGTH` (98 characters).

        Warns
        -----
        DeprecationWarning
            If the length parameter is outside `MIN_LENGTH`..`BIG_LENGTH` (2..32 characters).
        """
        _validate_length(length)

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
            A length value less than 1 or greater than `MAXIMUM_LENGTH` (98 characters) will raise a ValueError.
            Lengths outside `MIN_LENGTH`..`BIG_LENGTH` (2..32) emit a DeprecationWarning.

        Returns
        -------
        str
            Starts with a single, random letter, followed by a hash. The hash is generated using a combination of
            the current time in base 36, a random salt, a base 36 counter, and a system fingerprint.
            The length of the returned string is limited by `length`.

        Raises
        ------
        ValueError
            If the length parameter is a boolean, less than 1, or greater than `MAXIMUM_LENGTH` (98 characters).

        Warns
        -----
        DeprecationWarning
            If the length parameter is outside `MIN_LENGTH`..`BIG_LENGTH` (2..32 characters).
        """
        if length is not None:
            _validate_length(length)
        resolved_length: int = self._length if length is None else length

        first_letter: str = utils.create_letter(random_generator=self._random)

        base36_time: str = utils.base36_encode(time.time_ns())
        base36_count: str = utils.base36_encode(self._counter())

        salt: str = utils.create_entropy(length=resolved_length, random_generator=self._random)
        hash_input: str = base36_time + salt + base36_count + self._fingerprint

        return first_letter + utils.create_hash(hash_input)[1:resolved_length]

    @staticmethod
    def is_cuid(cuid_str: str, min_length: int = MIN_LENGTH, max_length: int = MAXIMUM_LENGTH) -> bool:
        """Validates whether a given string is a valid CUID2 identifier.

        Parameters
        ----------
        cuid_str : str
            The string to validate as a CUID2 identifier.
        min_length : int, default=MIN_LENGTH (2)
            The minimum allowed length of the identifier. Values below 2 have no effect, since a valid
            identifier always has a leading letter followed by at least one more character.
        max_length : int, default=MAXIMUM_LENGTH (98)
            The maximum allowed length of the identifier. Values above `MAXIMUM_LENGTH` are clamped to it.

        Returns
        -------
        bool
            True if `cuid_str` is a string starting with a lowercase ASCII letter followed by
            lowercase base36 characters and has length between `min_length` and `max_length`
            inclusive; False otherwise. The length bounds can only narrow the range of valid
            lengths (2 to `MAXIMUM_LENGTH`), never widen it.
        """
        max_length = min(max_length, MAXIMUM_LENGTH)
        return (
            isinstance(cuid_str, str)
            and min_length <= len(cuid_str) <= max_length
            and bool(_CUID_REGEX.match(cuid_str))
        )


_DEFAULT_GENERATOR: Optional[Cuid] = None


def create_id(length: Optional[int] = None) -> str:
    """Generate a CUID2 string using the module-level lazy default generator.

    Parameters
    ----------
    length : int, optional
        The optional length of the generated CUID2 string. Defaults to `DEFAULT_LENGTH` (24) when omitted.
        A length value less than 1 or greater than `MAXIMUM_LENGTH` (98 characters) will raise a ValueError.
        Lengths outside `MIN_LENGTH`..`BIG_LENGTH` (2..32) emit a DeprecationWarning.

    Returns
    -------
    str
        A collision-resistant, base36-encoded CUID2 identifier starting with a lowercase ASCII letter.

    Raises
    ------
    ValueError
        If the length parameter is a boolean, less than 1, or greater than `MAXIMUM_LENGTH` (98 characters).

    Warns
    -----
    DeprecationWarning
        If the length parameter is outside `MIN_LENGTH`..`BIG_LENGTH` (2..32 characters).
    """
    global _DEFAULT_GENERATOR  # noqa: PLW0603  # pylint: disable=global-statement
    if _DEFAULT_GENERATOR is None:
        _DEFAULT_GENERATOR = Cuid()
    return _DEFAULT_GENERATOR.generate(length=length)


is_cuid = Cuid.is_cuid


def cuid_wrapper(length: int = DEFAULT_LENGTH) -> Callable[[], str]:
    """Wrap `create_id` and return a zero-argument callable that generates a CUID string.

    .. deprecated:: 2.1.0
        `cuid_wrapper` is deprecated and will be removed in v3.0.0.
        Use `create_id` or `functools.partial(create_id, length=...)` instead.

    Parameters
    ----------
    length : int, default=DEFAULT_LENGTH (24)
        The length parameter is an integer that determines the maximum length of the generated string.
        It has a default value of DEFAULT_LENGTH (24).
        A length value less than 1 or greater than `MAXIMUM_LENGTH` (98 characters) will raise a ValueError.
        Lengths outside `MIN_LENGTH`..`BIG_LENGTH` (2..32) emit a DeprecationWarning.

    Returns
    -------
    Callable[[], str]
        A callable that generates a CUID string.

    Raises
    ------
    ValueError
        If the length parameter is a boolean, less than 1, or greater than `MAXIMUM_LENGTH` (98 characters).

    Warns
    -----
    DeprecationWarning
        Always emitted because `cuid_wrapper` is deprecated and will be removed in v3.0.0,
        and also emitted if the length parameter is outside `MIN_LENGTH`..`BIG_LENGTH` (2..32 characters).
    """
    _validate_length(length)
    warnings.warn(
        "cuid_wrapper() is deprecated and will be removed in v3.0.0. "
        "Use create_id() or functools.partial(create_id, length=...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    def cuid() -> str:
        return create_id(length=length)

    return cuid
