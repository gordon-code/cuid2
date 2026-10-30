"""Core CUID2 generator class, validation, and module-level helper functions."""

from __future__ import annotations

import inspect
import os
import re
import threading
import time
import warnings
from contextlib import suppress
from copy import copy, deepcopy
from functools import partial
from math import floor
from secrets import SystemRandom
from typing import TYPE_CHECKING, ClassVar, Final, NamedTuple, Protocol

from cuid2 import utils
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

if TYPE_CHECKING:
    from _random import Random
    from collections.abc import Callable

    class FingerprintCallable(Protocol):
        """Protocol for fingerprint generator callables."""

        def __call__(self: FingerprintCallable, random_generator: Random) -> str:
            """Generate a host/process fingerprint using the provided random generator."""
            ...

    class IsCuidCallable(Protocol):
        """Protocol for the CUID2 validation callable."""

        def __call__(
            self: IsCuidCallable,
            cuid_str: str,
            min_length: int = MIN_LENGTH,
            max_length: int = MAXIMUM_LENGTH,
        ) -> bool:
            """Validate whether a string is a CUID2 identifier within the given length bounds."""
            ...


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


def is_cuid(cuid_str: str, min_length: int = MIN_LENGTH, max_length: int = MAXIMUM_LENGTH) -> bool:
    """Validate whether a given string is a valid CUID2 identifier.

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
        isinstance(cuid_str, str)  # pyright: ignore[reportUnnecessaryIsInstance]
        and min_length <= len(cuid_str) <= max_length
        and bool(_CUID_REGEX.match(cuid_str))
    )


class _GeneratorState(NamedTuple):
    """Per-process generator state, replaced as a whole when a forked child process first generates an ID."""

    pid: int
    lock: threading.RLock
    random: Random
    counter: Callable[[], int]
    fingerprint: str


# Factories are shared by reference when a Cuid is deep-copied so that RNG objects they hold are never cloned.
_SHARED_ON_DEEPCOPY: Final[frozenset[str]] = frozenset(
    {"_random_generator", "_counter_factory", "_fingerprint_factory", "_state"},
)
_process_locks: Final[dict[int, threading.RLock]] = {}


def _process_lock(pid: int) -> threading.RLock:
    """Return the lock that serializes state rebuilds and default generator creation within process `pid`.

    Keyed by process ID so a forked child never acquires a lock inherited from its parent, which a parent thread
    that does not exist in the child may hold; `dict.setdefault` gives every thread of a process the same lock.
    """
    return _process_locks.setdefault(pid, threading.RLock())


class Cuid:
    """Configurable thread- and fork-safe CUID2 generator instance."""

    def __init__(
        self: Cuid,
        random_generator: Callable[[], Random] = SystemRandom,
        counter: Callable[[int], Callable[[], int]] = utils.create_counter,
        length: int = DEFAULT_LENGTH,
        fingerprint: FingerprintCallable = utils.create_fingerprint,
    ) -> None:
        """Initialize a Cuid generator that produces universally unique, base36-encoded strings.

        Parameters
        ----------
        random_generator : Callable[[], "Random"], default=SystemRandom
            Factory callable returning the random number generator instance. Defaults to `secrets.SystemRandom`.
            Called again in a forked child process (see Notes).
        counter : Callable[[int], Callable[[], int]], default=utils.create_counter
            The `counter` parameter is a callable that creates a counter returning an incremented value each time it
            is called. The `create_counter` function from the `utils` module is used by default. Called again with a
            new random starting value in a forked child process.
        length : int, default=DEFAULT_LENGTH (24)
            The length parameter is an integer that determines the maximum length of the generated string.
            It has a default value of DEFAULT_LENGTH (24).
            A length value less than 1 or greater than `MAXIMUM_LENGTH` (98 characters) will raise a ValueError.
            Lengths outside `MIN_LENGTH`..`BIG_LENGTH` (2..32) emit a DeprecationWarning.
        fingerprint : "FingerprintCallable", default=utils.create_fingerprint
            The "fingerprint" parameter is a callable function that generates a unique identifier. Called again in a
            forked child process; the default includes the child's `os.getpid()`.

        Raises
        ------
        ValueError
            If the length parameter is a boolean, less than 1, or greater than `MAXIMUM_LENGTH` (98 characters).

        Warns
        -----
        DeprecationWarning
            If the length parameter is outside `MIN_LENGTH`..`BIG_LENGTH` (2..32 characters).

        Notes
        -----
        `generate()` may be called concurrently from multiple threads, including on free-threaded Python. Draws from
        the random generator and counter are serialized per instance by a re-entrant lock, so a signal handler or
        finalizer that generates an ID on the same thread does not deadlock.

        Each instance records the process ID that built its state. When `generate()` first runs in a different
        process, such as any `os.fork()` child (including pre-fork servers that fork without running Python's fork
        hooks), it builds a new lock, random generator, counter, and fingerprint once, by calling `random_generator`,
        `counter`, and `fingerprint` again before generating. If `random_generator` returns the same object as before
        the fork, its `seed()` method is called to reseed it from OS entropy; if it has no `seed()` method or `seed()`
        raises `NotImplementedError` or `TypeError`, that generator keeps the parent's stream, and IDs still differ by
        timestamp and, with the default `fingerprint`, by process ID. Fixed-seed factories (such as
        `functools.partial(random.Random, 42)`) give every process the same stream and are intended for deterministic
        single-process tests.

        `copy.deepcopy()` returns an independent generator: the three factories are shared by reference, other
        attributes are deep-copied, and the lock, random generator, counter, and fingerprint are built anew.
        """
        _validate_length(length)

        self._random_generator: Callable[[], Random] = random_generator
        self._counter_factory: Callable[[int], Callable[[], int]] = counter
        self._fingerprint_factory: FingerprintCallable = fingerprint
        self._length: int = length
        self._state: _GeneratorState = self._create_state(previous_random=None)

    def __deepcopy__(self: Cuid, memo: dict[int, object]) -> Cuid:
        """Return an independent generator that never clones the lock, random generator state, or counter."""
        clone = copy(self)
        memo[id(self)] = clone
        for name, value in vars(self).items():
            if name not in _SHARED_ON_DEEPCOPY:
                setattr(clone, name, deepcopy(value, memo))
        clone._state = clone._create_state(previous_random=None)  # noqa: SLF001
        return clone

    def _current_state(self: Cuid) -> _GeneratorState:
        """Return the state for the current process, rebuilding it once on the first call after a fork."""
        state: _GeneratorState = self._state
        pid: int = os.getpid()
        if state.pid == pid:
            return state
        with _process_lock(pid):
            state = self._state
            if state.pid != pid:
                state = self._state = self._create_state(previous_random=state.random)
        return state

    def _create_state(self: Cuid, previous_random: Random | None) -> _GeneratorState:
        """Build the lock, random generator, counter, and fingerprint for the current process."""
        random_generator: Random = self._random_generator()
        if random_generator is previous_random:
            with suppress(AttributeError, NotImplementedError, TypeError):
                random_generator.seed()
        return _GeneratorState(
            pid=os.getpid(),
            lock=threading.RLock(),
            random=random_generator,
            counter=self._counter_factory(floor(random_generator.random() * INITIAL_COUNT_MAX)),
            fingerprint=self._fingerprint_factory(random_generator=random_generator),
        )

    def generate(self: Cuid, length: int | None = None) -> str:
        """Generate a universally unique, base36-encoded string with a specified length.

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

        state: _GeneratorState = self._current_state()
        with state.lock:
            first_letter: str = utils.create_letter(random_generator=state.random)
            base36_count: str = utils.base36_encode(state.counter())
            salt: str = utils.create_entropy(length=resolved_length, random_generator=state.random)

        base36_time: str = utils.base36_encode(time.time_ns())
        hash_input: str = base36_time + salt + base36_count + state.fingerprint

        return first_letter + utils.create_hash(hash_input)[1:resolved_length]

    is_cuid: ClassVar[IsCuidCallable] = staticmethod(is_cuid)


_default_generator: Cuid | None = None


def create_id(length: int | None = None) -> str:
    """Generate a CUID2 string using the thread- and fork-safe module-level lazy default generator.

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
    global _default_generator  # noqa: PLW0603
    generator = _default_generator
    if generator is None:
        with _process_lock(os.getpid()):
            generator = _default_generator
            if generator is None:
                generator = Cuid()
                _default_generator = generator
    return generator.generate(length=length)


def cuid_wrapper(length: int = DEFAULT_LENGTH) -> Callable[[], str]:
    """Wrap `create_id` in `functools.partial` and return a callable that generates a CUID string.

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
        A `functools.partial(create_id, length=length)` callable that generates a CUID string.

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
    return partial(create_id, length=length)
