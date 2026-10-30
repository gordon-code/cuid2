from __future__ import annotations

import gc
import multiprocessing
import os
import pickle
import random
import threading
import time
import warnings
import weakref
from functools import partial
from math import floor
from secrets import SystemRandom
from timeit import repeat
from typing import TYPE_CHECKING

import pytest

import cuid2.generator
from cuid2 import (
    BIG_LENGTH,
    DEFAULT_LENGTH,
    INITIAL_COUNT_MAX,
    MAXIMUM_LENGTH,
    MIN_LENGTH,
    Cuid,
    create_id,
    cuid_wrapper,
    is_cuid,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from multiprocessing.connection import Connection
    from multiprocessing.process import BaseProcess
    from typing import Any
    from unittest.mock import Mock


class TestCuid:
    #  Tests execution time to ensure that time complexity doesn't increase.
    @pytest.mark.slow
    def test_generate_performance(self: TestCuid) -> None:
        timing_result = repeat(
            stmt="cuid.generate()",
            setup="from cuid2 import Cuid; cuid = Cuid()",
            repeat=10,
            number=50_000,
        )
        # 50k iterations of cuid.generate() should take less than 2 seconds
        assert min(timing_result) < 2

    #  Tests that generate() returns a string of length DEFAULT_LENGTH.
    def test_generate_default_length(self: TestCuid) -> None:
        cuid = Cuid()
        assert len(cuid.generate()) == DEFAULT_LENGTH

    #  Tests that generate() returns a string starting with a letter.
    def test_generate_starts_with_letter(self: TestCuid) -> None:
        cuid = Cuid()
        assert cuid.generate()[0].isalpha()

    #  Tests that generate() works when length parameter is None.
    def test_generate_length_none(self: TestCuid) -> None:
        cuid = Cuid(length=10)
        assert len(cuid.generate(length=None)) == 10

    #  Tests that generate() works when length parameter is really long.
    def test_generate_really_long_length(self: TestCuid) -> None:
        for invalid_length in (99, 100):
            with pytest.raises(ValueError, match=r"Length must never exceed 98 characters\."):
                Cuid(length=invalid_length)
            cuid = Cuid()
            with pytest.raises(ValueError, match=r"Length must never exceed 98 characters\."):
                cuid.generate(length=invalid_length)

    #  Tests that Cuid and generate() raise ValueError when length is less than 1 or a boolean.
    @pytest.mark.parametrize("invalid_length", [0, -1, -5, True, False])
    def test_generate_non_positive_length(self: TestCuid, invalid_length: int) -> None:
        with pytest.raises(ValueError, match=r"Length must be at least 1 character\."):
            Cuid(length=invalid_length)
        cuid = Cuid()
        with pytest.raises(ValueError, match=r"Length must be at least 1 character\."):
            cuid.generate(length=invalid_length)

    #  Tests that generate() works when length parameter is less than 2.
    def test_generate_length_less_than_2(self: TestCuid) -> None:
        cuid = Cuid()
        with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range") as record:
            assert len(cuid.generate(length=1)) == 1
        assert record[0].filename == __file__

    #  Tests that lengths outside MIN_LENGTH..BIG_LENGTH (1 and 33..98) emit DeprecationWarning attributed to caller.
    @pytest.mark.parametrize("deprecated_length", [1, BIG_LENGTH + 1, MAXIMUM_LENGTH - 2])
    def test_deprecated_lengths_emit_warning(self: TestCuid, deprecated_length: int) -> None:
        with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range") as record:
            cuid_instance = Cuid(length=deprecated_length)
        assert record[0].filename == __file__
        assert len(cuid_instance.generate()) == deprecated_length

        cuid = Cuid()
        with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range") as record:
            generated = cuid.generate(length=deprecated_length)
        assert record[0].filename == __file__
        assert len(generated) == deprecated_length

        with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range") as record:
            generated_from_create_id = create_id(length=deprecated_length)
        assert record[0].filename == __file__
        assert len(generated_from_create_id) == deprecated_length

    #  Tests that specification boundary lengths MIN_LENGTH (2) and BIG_LENGTH (32) emit no DeprecationWarning.
    @pytest.mark.parametrize("valid_length", [MIN_LENGTH, BIG_LENGTH])
    def test_spec_boundary_lengths_emit_no_warning(self: TestCuid, valid_length: int) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            cuid_instance = Cuid(length=valid_length)
            assert len(cuid_instance.generate()) == valid_length

            cuid = Cuid()
            assert len(cuid.generate(length=valid_length)) == valid_length

            assert len(create_id(length=valid_length)) == valid_length

    #  Tests that multiple instances of Cuid generate unique IDs.
    def test_generate_multiple_instances_unique_ids(self: TestCuid) -> None:
        cuid1 = Cuid()
        cuid2 = Cuid()
        assert cuid1.generate() != cuid2.generate()

    #  Tests that the same instance of Cuid generates unique IDs.
    def test_generate_unique_ids(self: TestCuid) -> None:
        cuid = Cuid()
        assert cuid.generate() != cuid.generate()

    #  Tests that generate() works when random_generator returns same values.
    def test_generate_same_random_values(self: TestCuid, mocker: Mock) -> None:
        mock_random_class = mocker.Mock()
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        mock_random_class.return_value = mock_random

        mocker.patch("cuid2.utils.create_entropy", return_value="mocked_entropy")
        mocker.patch("cuid2.utils.create_letter", return_value="l")
        mocker.patch("cuid2.utils.create_hash", return_value="mocked_hash")

        # Initialize Cuid with mocked random generator
        cuid = Cuid(random_generator=mock_random_class)

        # Generate two Cuids and assert they are the same
        cuid1 = cuid.generate()
        cuid2 = cuid.generate()
        assert cuid1 == cuid2

    #  Tests that the constructor sets default values if not provided.
    def test_constructor_default_values(self: TestCuid) -> None:
        # Initialize Cuid with default values
        cuid = Cuid()

        # Assert that the values are set to their default values
        assert isinstance(cuid._random, SystemRandom)
        assert callable(cuid._counter)
        assert cuid._length == DEFAULT_LENGTH
        assert isinstance(cuid._fingerprint, str)

    #  Tests that the random_generator and fingerprint functions are called correctly when mocked.
    def test_mock_random_generator_and_fingerprint(self: TestCuid, mocker: Mock) -> None:
        mock_random_class = mocker.Mock()
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        mock_random_class.return_value = mock_random

        mock_fingerprint = mocker.Mock()
        mock_fingerprint.return_value = "mocked_fingerprint"

        mocker.patch("cuid2.utils.create_entropy", return_value="mocked_entropy")
        mocker.patch("cuid2.utils.create_letter", return_value="l")
        mocker.patch("cuid2.utils.create_hash", return_value="mocked_hash")

        # Initialize Cuid with mocked random generator and fingerprint functions
        cuid = Cuid(random_generator=mock_random_class, fingerprint=mock_fingerprint)

        # Generate a Cuid and assert that the mocked functions were called correctly
        cuid_str = cuid.generate()
        assert cuid_str == "locked_hash"  # first letter is "l" from mocked create_letter function
        assert cuid._fingerprint == "mocked_fingerprint"
        assert (
            cuid._counter() == 238391185
        )  # counter is statically assigned since mocked random always returns the same value

    #  Tests that generate() returns a string of specified length.
    def test_generate_specified_length(self: TestCuid) -> None:
        cuid = Cuid(length=10)
        result = cuid.generate()
        assert len(result) == 10

    #  Tests that the constructor initializes random, counter, length, and fingerprint.
    def test_constructor_initializes_members(self: TestCuid, mocker: Mock) -> None:
        # Arrange
        mock_random_class = mocker.Mock()
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        mock_random_class.return_value = mock_random
        mock_counter = mocker.Mock()
        mock_fingerprint = mocker.Mock()

        # Act
        cuid = Cuid(random_generator=mock_random_class, counter=mock_counter, fingerprint=mock_fingerprint)

        # Assert
        assert cuid._random == mock_random_class()
        assert cuid._counter == mock_counter(floor(cuid._random.random() * INITIAL_COUNT_MAX))
        assert cuid._length == DEFAULT_LENGTH
        assert cuid._fingerprint == mock_fingerprint(random_generator=cuid._random)

    #  Tests that generate() uses base36 encoding and creates a hash.
    def test_generate_uses_base36_encoding(self: TestCuid, mocker: Mock) -> None:
        # Arrange
        mock_random_class = mocker.Mock()
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        mock_random_class.return_value = mock_random
        mock_counter = mocker.Mock()
        mock_counter.return_value = lambda: 123456789
        mock_fingerprint = mocker.Mock(return_value="abcdefg")
        mocker.patch("time.time_ns", return_value=1627584000000000000)  # 2021-07-30 00:00:00 UTC
        mocker.patch("cuid2.utils.create_letter", return_value="l")

        cuid = Cuid(random_generator=mock_random_class, counter=mock_counter, fingerprint=mock_fingerprint)

        # Act
        result = cuid.generate()

        # Assert
        assert result.startswith("l")
        assert len(result) == DEFAULT_LENGTH
        assert result == "l9j3ikop1bi8tcvzme3x3yv7"

    def test_generate_thread_safety_custom_random(self: TestCuid) -> None:
        """Tests that Cuid.generate() serializes calls to a non-reentrant custom random generator across threads."""

        class _NonReentrantRandom(random.Random):
            def __init__(self: _NonReentrantRandom, seed: int) -> None:
                super().__init__(seed)
                self._busy = False

            def random(self: _NonReentrantRandom) -> float:
                if self._busy:
                    msg = "Concurrent access to non-reentrant random generator"
                    raise RuntimeError(msg)
                self._busy = True
                try:
                    time.sleep(0)
                    return super().random()
                finally:
                    self._busy = False

        cuid = Cuid(random_generator=lambda: _NonReentrantRandom(42))
        num_threads = 8
        ids_per_thread = 25
        barrier = threading.Barrier(num_threads)
        buckets: list[list[str]] = [[] for _ in range(num_threads)]
        errors: list[BaseException] = []

        def worker(index: int) -> None:
            try:
                barrier.wait()
                buckets[index] = [cuid.generate() for _ in range(ids_per_thread)]
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        generated = [cid for bucket in buckets for cid in bucket]
        assert len(generated) == num_threads * ids_per_thread
        assert len(set(generated)) == len(generated)
        assert all(is_cuid(cid) for cid in generated)


class TestIsCuid:
    #  Tests that is_cuid accepts well-formed identifiers, including the shortest and longest allowed ones.
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("ab", id="minimum-length"),
            pytest.param("a0", id="letter-then-digit"),
            pytest.param("zz", id="last-letter"),
            pytest.param("a" * MAXIMUM_LENGTH, id="maximum-length"),
            pytest.param("z" + "9" * (MAXIMUM_LENGTH - 1), id="maximum-length-digits"),
            pytest.param("a0123456789abcdefghijklmnopqrstuvwxyz", id="full-base36-alphabet"),
            pytest.param("cjld2cjxh0000qzrmn831i7r", id="24-chars-starting-with-c"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", id="24-chars-random"),
            pytest.param("yi7rqj1trke", id="upstream-valid-vector"),
        ],
    )
    def test_is_cuid_valid(self: TestIsCuid, value: str) -> None:
        assert Cuid.is_cuid(value) is True

    #  Tests that is_cuid rejects strings that are too short, too long, or have the wrong shape.
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("", id="empty"),
            pytest.param("a", id="single-letter"),
            pytest.param("1", id="single-digit"),
            pytest.param("42", id="digits-only"),
            pytest.param("0a", id="leading-zero"),
            pytest.param("1b", id="leading-digit"),
            pytest.param("9" + "a" * (MAXIMUM_LENGTH - 1), id="leading-digit-maximum-length"),
            pytest.param("a" * (MAXIMUM_LENGTH + 1), id="one-over-maximum-length"),
            pytest.param("a" * 1000, id="far-over-maximum-length"),
        ],
    )
    def test_is_cuid_invalid_shape_or_length(self: TestIsCuid, value: str) -> None:
        assert Cuid.is_cuid(value) is False

    #  Tests that is_cuid rejects any character outside of [0-9a-z], including case and symbol variants.
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("aB", id="trailing-uppercase"),
            pytest.param("Ab", id="leading-uppercase"),
            pytest.param("AB", id="all-uppercase"),
            pytest.param("aaaaDLL", id="upstream-uppercase-vector"),
            pytest.param("-x!ha", id="upstream-symbol-vector"),
            pytest.param("ab*%@#x", id="upstream-symbols-vector"),
            pytest.param("cjld2cjxh0000qzrmn831i7rn!", id="trailing-bang"),
            pytest.param("a-b", id="hyphen"),
            pytest.param("a_b", id="underscore"),
            pytest.param("a.b", id="dot"),
            pytest.param("a/b", id="slash"),
            pytest.param("a b", id="inner-space"),
            pytest.param("a\x00", id="nul-byte"),
        ],
    )
    def test_is_cuid_invalid_characters(self: TestIsCuid, value: str) -> None:
        assert Cuid.is_cuid(value) is False

    #  Tests that is_cuid rejects surrounding whitespace; Python's `$` would wrongly accept a trailing newline.
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(" ab", id="leading-space"),
            pytest.param("ab ", id="trailing-space"),
            pytest.param("\tab", id="leading-tab"),
            pytest.param("ab\t", id="trailing-tab"),
            pytest.param("ab\n", id="trailing-newline"),
            pytest.param("ab\r\n", id="trailing-crlf"),
            pytest.param("\nab", id="leading-newline"),
            pytest.param("a\nb", id="inner-newline"),
            pytest.param("ab\n\n", id="trailing-double-newline"),
        ],
    )
    def test_is_cuid_invalid_whitespace(self: TestIsCuid, value: str) -> None:
        assert Cuid.is_cuid(value) is False

    #  Tests that is_cuid only accepts ASCII, guarding against `\d`, `\w`, or re.IGNORECASE regressions.
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("a\u0663", id="arabic-indic-digit"),
            pytest.param("\uff41b", id="fullwidth-letter"),
            pytest.param("a\uff11", id="fullwidth-digit"),
            pytest.param("\u00e9a", id="accented-leading-letter"),
            pytest.param("a\u00e9", id="accented-trailing-letter"),
            pytest.param("\u0430b", id="cyrillic-homoglyph-a"),
            pytest.param("ab\u200b", id="zero-width-space"),
            pytest.param("a\u212a", id="kelvin-sign"),
            pytest.param("\u017fa", id="long-s"),
        ],
    )
    def test_is_cuid_invalid_non_ascii(self: TestIsCuid, value: str) -> None:
        assert Cuid.is_cuid(value) is False

    #  Tests that is_cuid returns False, rather than raising, for anything that is not a str.
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(None, id="none"),
            pytest.param(123, id="int"),
            pytest.param(1.5, id="float"),
            pytest.param(True, id="bool"),
            pytest.param(["ab"], id="list"),
            pytest.param(("ab",), id="tuple"),
            pytest.param({"ab"}, id="set"),
            pytest.param({"ab": "ab"}, id="dict"),
            pytest.param(b"ab", id="bytes"),
            pytest.param(bytearray(b"ab"), id="bytearray"),
            pytest.param(object(), id="object"),
        ],
    )
    def test_is_cuid_invalid_non_string(self: TestIsCuid, value: object) -> None:
        assert Cuid.is_cuid(value) is False  # type: ignore[arg-type]

    #  Tests that is_cuid accepts str subclasses, since they are still strings.
    def test_is_cuid_str_subclass(self: TestIsCuid) -> None:
        class MyStr(str):
            __slots__ = ()

        assert Cuid.is_cuid(MyStr("abc")) is True

    #  Tests that min_length and max_length narrow the allowed range, inclusive of both bounds.
    @pytest.mark.parametrize(
        ("value", "kwargs", "expected"),
        [
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"min_length": 20}, True, id="min-below-length"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"min_length": 24}, True, id="min-equals-length"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"min_length": 25}, False, id="min-above-length"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"max_length": 25}, True, id="max-above-length"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"max_length": 24}, True, id="max-equals-length"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"max_length": 23}, False, id="max-below-length"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"max_length": 5}, False, id="max-far-below-length"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"min_length": 24, "max_length": 24}, True, id="exact-length"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"min_length": 20, "max_length": 30}, True, id="inside-range"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"min_length": 25, "max_length": 30}, False, id="below-range"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"min_length": 2, "max_length": 23}, False, id="above-range"),
            pytest.param("dlwvlnik2o0lh47uh4kg6q8j", {"min_length": 30, "max_length": 20}, False, id="inverted-range"),
            pytest.param("ab", {"min_length": 2}, True, id="shortest-at-min"),
            pytest.param("ab", {"max_length": 2}, True, id="shortest-at-max"),
            pytest.param("ab", {"min_length": 3}, False, id="shortest-below-min"),
            pytest.param("ab", {"max_length": 1}, False, id="shortest-above-max"),
            pytest.param("abc", {"min_length": 3, "max_length": 3}, True, id="exact-length-three"),
        ],
    )
    def test_is_cuid_length_bounds(
        self: TestIsCuid,
        value: str,
        kwargs: dict[str, int],
        expected: bool,
    ) -> None:
        assert Cuid.is_cuid(value, **kwargs) is expected

    #  Tests that min_length cannot go below 2: the identifier shape always needs 2+ characters.
    @pytest.mark.parametrize("min_length", [1, 0, -1, -5, -(10**9)])
    @pytest.mark.parametrize("value", ["", "a", "1"])
    def test_is_cuid_min_length_cannot_go_below_minimum(
        self: TestIsCuid,
        value: str,
        min_length: int,
    ) -> None:
        assert Cuid.is_cuid(value, min_length=min_length) is False

    #  Tests that lowering min_length still accepts valid identifiers.
    @pytest.mark.parametrize("min_length", [2, 1, 0, -1])
    def test_is_cuid_min_length_below_minimum_still_accepts_valid(self: TestIsCuid, min_length: int) -> None:
        assert Cuid.is_cuid("ab", min_length=min_length) is True

    #  Tests that max_length cannot go above MAXIMUM_LENGTH, matching the generator's own limit.
    @pytest.mark.parametrize("max_length", [MAXIMUM_LENGTH + 1, 200, 10**9])
    def test_is_cuid_max_length_cannot_exceed_maximum(self: TestIsCuid, max_length: int) -> None:
        assert Cuid.is_cuid("a" * (MAXIMUM_LENGTH + 1), max_length=max_length) is False
        assert Cuid.is_cuid("a" * 150, max_length=max_length) is False
        assert Cuid.is_cuid("a" * MAXIMUM_LENGTH, max_length=max_length) is True

    #  Tests that a min_length above MAXIMUM_LENGTH can never match.
    def test_is_cuid_min_length_above_maximum(self: TestIsCuid) -> None:
        assert Cuid.is_cuid("a" * MAXIMUM_LENGTH, min_length=MAXIMUM_LENGTH + 1) is False

    #  Tests that max_length below 2 can never match.
    @pytest.mark.parametrize("max_length", [1, 0, -1])
    def test_is_cuid_max_length_below_minimum(self: TestIsCuid, max_length: int) -> None:
        assert Cuid.is_cuid("ab", max_length=max_length) is False

    #  Tests that non-integer bounds raise TypeError instead of being silently accepted.
    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param({"min_length": None}, id="min-none"),
            pytest.param({"max_length": None}, id="max-none"),
            pytest.param({"min_length": "2"}, id="min-str"),
            pytest.param({"max_length": "5"}, id="max-str"),
        ],
    )
    def test_is_cuid_non_integer_bounds_raise(self: TestIsCuid, kwargs: dict[str, object]) -> None:
        with pytest.raises(TypeError):
            Cuid.is_cuid("abc", **kwargs)  # type: ignore[arg-type]

    #  Tests that is_cuid can be called on an instance as well as on the class.
    def test_is_cuid_callable_on_instance(self: TestIsCuid) -> None:
        cuid = Cuid()
        assert cuid.is_cuid(cuid.generate()) is True
        assert cuid.is_cuid("NOT-A-CUID") is False

    #  Tests that every generated id validates for every supported length, including the boundaries.
    #  The exact length is only asserted below MAXIMUM_LENGTH - 1: at 97 and 98 characters the generator
    #  occasionally returns a shorter id (the SHA3-512 base36 digest is not always long enough), but
    #  such ids are still valid.
    @pytest.mark.parametrize("length", [2, 3, 10, DEFAULT_LENGTH, BIG_LENGTH, 50, MAXIMUM_LENGTH - 2, MAXIMUM_LENGTH])
    def test_is_cuid_accepts_generated_ids(self: TestIsCuid, length: int) -> None:
        if length > BIG_LENGTH:
            with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range"):
                cuid = Cuid(length=length)
        else:
            cuid = Cuid(length=length)
        for _ in range(250):
            generated = cuid.generate()
            assert len(generated) <= length
            if length < MAXIMUM_LENGTH - 1:
                assert len(generated) == length
            assert Cuid.is_cuid(generated) is True

    #  Tests that ids generated via generate(length=...) and via the wrapper also validate.
    def test_is_cuid_accepts_generate_override_and_wrapper(self: TestIsCuid) -> None:
        cuid = Cuid()
        wrapper = cuid_wrapper()
        for _ in range(250):
            assert Cuid.is_cuid(cuid.generate(length=8)) is True
            assert Cuid.is_cuid(wrapper()) is True

    #  Tests that a tightened min/max still accepts a generated id of exactly that length.
    def test_is_cuid_generated_id_exact_bounds(self: TestIsCuid) -> None:
        generated = Cuid().generate()
        assert Cuid.is_cuid(generated, min_length=DEFAULT_LENGTH, max_length=DEFAULT_LENGTH) is True
        assert Cuid.is_cuid(generated, min_length=DEFAULT_LENGTH + 1) is False
        assert Cuid.is_cuid(generated, max_length=DEFAULT_LENGTH - 1) is False

    #  Documents a known asymmetry: the generator can emit 1-character ids, but a valid CUID2 needs 2+ characters.
    #  If the generator's minimum length is ever raised to 2, this test should be updated.
    def test_is_cuid_rejects_single_character_generated_id(self: TestIsCuid) -> None:
        with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range"):
            generated = Cuid(length=1).generate()
        assert len(generated) == 1
        assert Cuid.is_cuid(generated) is False
        assert Cuid.is_cuid(generated, min_length=1) is False

    #  Tests that mutating a generated id in each way is detected.
    def test_is_cuid_detects_mutated_generated_id(self: TestIsCuid) -> None:
        generated = Cuid().generate()
        assert Cuid.is_cuid(generated) is True
        assert Cuid.is_cuid("1" + generated[1:]) is False
        assert Cuid.is_cuid(generated.upper()) is False
        assert Cuid.is_cuid(generated + " ") is False
        assert Cuid.is_cuid(generated + "\n") is False
        assert Cuid.is_cuid(generated[:-1] + "!") is False
        assert Cuid.is_cuid("") is False

    #  Tests that top-level is_cuid is exported and behaves identically to Cuid.is_cuid.
    def test_top_level_is_cuid_export(self: TestIsCuid) -> None:
        assert is_cuid is Cuid.is_cuid
        generated = Cuid().generate()
        assert is_cuid(generated) is True
        assert is_cuid("yi7rqj1trke") is True
        assert is_cuid("NOT-A-CUID") is False
        assert is_cuid("") is False
        assert is_cuid(generated, min_length=DEFAULT_LENGTH, max_length=DEFAULT_LENGTH) is True
        assert is_cuid(generated, min_length=DEFAULT_LENGTH + 1) is False


class TestCreateId:
    def test_create_id_lazy_singleton(self: TestCreateId, mocker: Mock) -> None:
        """Tests that create_id() lazily initializes _default_generator and reuses the singleton instance."""
        assert cuid2.generator._default_generator is None
        spy = mocker.spy(cuid2.generator, "Cuid")
        first_id: str = create_id()
        first_generator = cuid2.generator._default_generator
        assert isinstance(first_generator, Cuid)
        assert spy.call_count == 1
        second_id: str = create_id()
        assert cuid2.generator._default_generator is first_generator
        assert spy.call_count == 1
        assert first_id != second_id

    def test_create_id_default_length(self: TestCreateId) -> None:
        """Tests that create_id() generates a valid 24-character CUID2 string by default."""
        generated: str = create_id()
        assert isinstance(generated, str)
        assert len(generated) == DEFAULT_LENGTH
        assert is_cuid(generated) is True

    @pytest.mark.parametrize("length", [MIN_LENGTH, 16, BIG_LENGTH])
    def test_create_id_custom_length(self: TestCreateId, length: int) -> None:
        """Tests that create_id() generates a valid CUID2 string of the specified length."""
        generated: str = create_id(length=length)
        assert len(generated) == length
        assert is_cuid(generated) is True

    def test_create_id_unique_ids(self: TestCreateId) -> None:
        """Tests that consecutive create_id() calls return distinct IDs."""
        assert create_id() != create_id()

    @pytest.mark.parametrize("length", [1, BIG_LENGTH + 1])
    def test_create_id_deprecated_length(self: TestCreateId, length: int) -> None:
        """Tests that create_id() emits DeprecationWarning attributed to the caller for lengths outside 2..32."""
        with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range") as record:
            generated: str = create_id(length=length)
        assert len(generated) == length
        assert record[0].filename == __file__

    @pytest.mark.parametrize(
        ("invalid_length", "expected_match"),
        [
            (0, r"Length must be at least 1 character\."),
            (-1, r"Length must be at least 1 character\."),
            (True, r"Length must be at least 1 character\."),
            (False, r"Length must be at least 1 character\."),
            (MAXIMUM_LENGTH + 1, r"Length must never exceed 98 characters\."),
        ],
    )
    def test_create_id_invalid_length(
        self: TestCreateId,
        invalid_length: int,
        expected_match: str,
    ) -> None:
        """Tests that create_id() raises ValueError when length is out of bounds."""
        with pytest.raises(ValueError, match=expected_match):
            create_id(length=invalid_length)

    def test_create_id_concurrent_first_call_singleton(self: TestCreateId, mocker: Mock) -> None:
        """Tests that concurrent first-time create_id() calls initialize _default_generator once."""
        assert cuid2.generator._default_generator is None
        spy = mocker.spy(cuid2.generator, "Cuid")
        num_threads = 8
        ids_per_thread = 25
        barrier = threading.Barrier(num_threads)
        buckets: list[list[str]] = [[] for _ in range(num_threads)]

        def worker(index: int) -> None:
            barrier.wait()
            buckets[index] = [create_id() for _ in range(ids_per_thread)]

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert spy.call_count == 1
        generated = [cid for bucket in buckets for cid in bucket]
        assert len(generated) == num_threads * ids_per_thread
        assert len(set(generated)) == len(generated)
        assert all(is_cuid(cid) for cid in generated)

    def test_create_id_double_checked_locking_inner_branch(
        self: TestCreateId,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Deterministically exercises the inner 'generator is not None' branch of double-checked locking."""
        assert cuid2.generator._default_generator is None
        pre_created = Cuid()

        class _PrepopulatingLock:
            def __enter__(self: _PrepopulatingLock) -> None:
                cuid2.generator._default_generator = pre_created

            def __exit__(self: _PrepopulatingLock, *_args: object) -> None:
                return None

        monkeypatch.setattr(cuid2.generator, "_default_generator_lock", _PrepopulatingLock())
        generated = create_id()
        assert is_cuid(generated)
        assert cuid2.generator._default_generator is pre_created


class TestCuidWrapper:
    def test_cuid_wrapper_is_callable(self: TestCuidWrapper) -> None:
        """Tests that cuid_wrapper() returns a functools.partial bound to create_id."""
        cuid_func: Callable[[], str] = cuid_wrapper()
        assert callable(cuid_func)
        assert isinstance(cuid_func, partial)
        assert cuid_func.func is create_id
        assert cuid_func.args == ()
        assert cuid_func.keywords == {"length": DEFAULT_LENGTH}

    def test_cuid_wrapper_delegates_to_create_id_lazily(self: TestCuidWrapper, mocker: Mock) -> None:
        """Tests that cuid_wrapper() is lazy at creation time and delegates to create_id()."""
        spy = mocker.spy(cuid2.generator, "create_id")
        cuid_func: Callable[[], str] = cuid_wrapper(length=10)
        assert cuid2.generator._default_generator is None
        assert spy.call_count == 0
        generated: str = cuid_func()
        assert len(generated) == 10
        assert spy.call_count == 1
        spy.assert_called_once_with(length=10)

    def test_cuid_wrapper_return_type(self: TestCuidWrapper) -> None:
        """Tests that the function returns a callable that generates a CUID string."""
        cuid_func: Callable[[], str] = cuid_wrapper()
        assert isinstance(cuid_func(), str)

    def test_cuid_wrapper_no_parameters(self: TestCuidWrapper) -> None:
        """Tests that positional length raises TypeError while keyword override is accepted by partial."""
        cuid_func: Callable[[], str] = cuid_wrapper()
        with pytest.raises(
            TypeError,
            match=r"create_id\(\) got multiple values for argument 'length'",
        ):
            cuid_func(DEFAULT_LENGTH)  # type: ignore[call-arg]
        overridden: str = cuid_func(length=10)  # type: ignore[call-arg]
        assert len(overridden) == 10
        assert is_cuid(overridden) is True

    def test_cuid_wrapper_pickle_round_trip(self: TestCuidWrapper) -> None:
        """Tests that the returned functools.partial can be pickled and unpickled."""
        restored = pickle.loads(pickle.dumps(cuid_wrapper(length=10)))  # noqa: S301
        assert isinstance(restored, partial)
        assert restored.func is create_id
        assert restored.keywords == {"length": 10}
        assert len(restored()) == 10

    def test_cuid_wrapper_length(self: TestCuidWrapper) -> None:
        """Tests that the function returns a callable that generates a CUID string with the default length."""
        cuid_func: Callable[[], str] = cuid_wrapper()
        assert len(cuid_func()) == DEFAULT_LENGTH

    @pytest.mark.parametrize("length", [MIN_LENGTH, 10, BIG_LENGTH])
    def test_cuid_wrapper_custom_length(self: TestCuidWrapper, length: int) -> None:
        """Tests that cuid_wrapper generates a CUID string with a specified length."""
        cuid_func: Callable[[], str] = cuid_wrapper(length=length)
        assert len(cuid_func()) == length

    @pytest.mark.parametrize("length", [1, BIG_LENGTH + 1, MAXIMUM_LENGTH])
    def test_cuid_wrapper_deprecated_length(self: TestCuidWrapper, length: int) -> None:
        """Tests that cuid_wrapper emits DeprecationWarning for lengths outside MIN_LENGTH..BIG_LENGTH."""
        with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range") as record:
            cuid_func: Callable[[], str] = cuid_wrapper(length=length)
        assert len(record) == 1
        assert record[0].filename == __file__
        with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range") as call_record:
            generated = cuid_func()
        assert len(call_record) == 1
        assert call_record[0].filename == __file__
        assert len(generated) <= length
        if length < MAXIMUM_LENGTH - 1:
            assert len(generated) == length

    @pytest.mark.parametrize(
        ("invalid_length", "expected_match"),
        [
            (0, r"Length must be at least 1 character\."),
            (-1, r"Length must be at least 1 character\."),
            (True, r"Length must be at least 1 character\."),
            (False, r"Length must be at least 1 character\."),
            (MAXIMUM_LENGTH + 1, r"Length must never exceed 98 characters\."),
        ],
    )
    def test_cuid_wrapper_invalid_length(
        self: TestCuidWrapper,
        invalid_length: int,
        expected_match: str,
    ) -> None:
        """Tests that cuid_wrapper raises ValueError when length is out of bounds."""
        with pytest.raises(ValueError, match=expected_match):
            cuid_wrapper(length=invalid_length)


def _fork_child_worker(custom_cuid: Cuid, conn: Connection[Any, Any]) -> None:
    try:
        default_ids = [create_id() for _ in range(20)]
        custom_ids = [custom_cuid.generate() for _ in range(20)]
        conn.send((os.getpid(), custom_cuid._fingerprint, default_ids, custom_ids))
    finally:
        conn.close()


class TestForkSafety:
    def test_register_at_fork_posix_and_non_posix(
        self: TestForkSafety,
        monkeypatch: pytest.MonkeyPatch,
        mocker: Mock,
    ) -> None:
        """Tests _register_at_fork() both when os.register_at_fork exists and when it is absent."""
        mock_register = mocker.Mock()
        monkeypatch.setattr(os, "register_at_fork", mock_register, raising=False)
        cuid2.generator._register_at_fork()
        mock_register.assert_called_once_with(after_in_child=cuid2.generator._reinit_after_fork)

        monkeypatch.delattr(os, "register_at_fork", raising=False)
        cuid2.generator._register_at_fork()

    def test_reinit_after_fork_resets_default_generator_and_live_instances(
        self: TestForkSafety,
        mocker: Mock,
    ) -> None:
        """Tests that _reinit_after_fork() resets _default_generator, locks, and live Cuid instances."""
        _ = create_id()
        assert cuid2.generator._default_generator is not None
        old_default_lock = cuid2.generator._default_generator_lock
        old_instances_lock = cuid2.generator._instances_lock

        cuid = Cuid()
        old_instance_lock = cuid._lock
        old_random = cuid._random
        old_counter = cuid._counter
        old_fingerprint = cuid._fingerprint

        mocker.patch("os.getpid", return_value=os.getpid() + 10_000)
        cuid2.generator._reinit_after_fork()

        assert cuid2.generator._default_generator is None
        assert cuid2.generator._default_generator_lock is not old_default_lock
        assert cuid2.generator._instances_lock is not old_instances_lock
        assert cuid._lock is not old_instance_lock
        assert cuid._random is not old_random
        assert cuid._counter is not old_counter
        assert cuid._fingerprint != old_fingerprint
        assert is_cuid(create_id())

    def test_reinit_after_fork_reseeds_shared_random_and_handles_seedless_rng(
        self: TestForkSafety,
        mocker: Mock,
    ) -> None:
        """Tests that _reinit_after_fork() reseeds a reused RNG instance and tolerates RNGs without .seed()."""
        shared_rng = random.Random(999)  # noqa: S311
        cuid_shared = Cuid(random_generator=lambda: shared_rng)
        unreseeded_rng = random.Random()  # noqa: S311
        unreseeded_rng.setstate(shared_rng.getstate())
        for _ in range(1 + BIG_LENGTH):
            _ = unreseeded_rng.random()

        seed_spy = mocker.spy(shared_rng, "seed")

        class _SeedlessRng:
            def random(self: _SeedlessRng) -> float:
                return 0.25

        seedless = _SeedlessRng()
        cuid_seedless = Cuid(random_generator=lambda: seedless)  # type: ignore[arg-type, return-value]

        cuid2.generator._reinit_after_fork()

        seed_spy.assert_called_once_with()
        assert shared_rng.getstate() != unreseeded_rng.getstate()
        assert is_cuid(cuid_shared.generate())
        assert is_cuid(cuid_seedless.generate())

    def test_instances_weakset_allows_garbage_collection(self: TestForkSafety) -> None:
        """Tests that unreferenced Cuid instances are garbage-collected and removed from _instances."""
        cuid = Cuid()
        ref = weakref.ref(cuid)
        assert cuid in cuid2.generator._instances
        del cuid
        gc.collect()
        assert ref() is None

    @pytest.mark.skipif(
        "fork" not in multiprocessing.get_all_start_methods(),
        reason="POSIX fork start method required",
    )
    def test_posix_fork_child_reinitializes_generators(self: TestForkSafety) -> None:
        """Tests that forked child processes receive distinct fingerprints, RNG states, and ID streams."""
        shared_rng = random.Random(12345)  # noqa: S311
        custom_cuid = Cuid(random_generator=lambda: shared_rng)
        _ = create_id()
        parent_fingerprint = custom_cuid._fingerprint

        ctx = multiprocessing.get_context("fork")
        parent_conns: list[Connection[Any, Any]] = []
        procs: list[BaseProcess] = []
        for _ in range(2):
            parent_conn, child_conn = ctx.Pipe(duplex=False)
            proc: BaseProcess = ctx.Process(target=_fork_child_worker, args=(custom_cuid, child_conn))
            proc.start()
            child_conn.close()
            parent_conns.append(parent_conn)
            procs.append(proc)

        results = [conn.recv() for conn in parent_conns]
        for conn in parent_conns:
            conn.close()
        for proc in procs:
            proc.join(timeout=10)
            assert proc.exitcode == 0

        (pid_a, fp_a, default_a, custom_a), (pid_b, fp_b, default_b, custom_b) = results
        assert pid_a != os.getpid()
        assert pid_b != os.getpid()
        assert pid_a != pid_b
        assert fp_a != parent_fingerprint
        assert fp_b != parent_fingerprint
        assert fp_a != fp_b
        assert set(default_a).isdisjoint(set(default_b))
        assert set(custom_a).isdisjoint(set(custom_b))
