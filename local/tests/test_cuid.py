from __future__ import annotations

from math import floor
from secrets import SystemRandom
from timeit import repeat
from typing import TYPE_CHECKING, Callable

import pytest

from cuid2 import DEFAULT_LENGTH, INITIAL_COUNT_MAX, Cuid, cuid_wrapper
from cuid2.generator import MAXIMUM_LENGTH, MINIMUM_LENGTH

if TYPE_CHECKING:
    from unittest.mock import Mock


class TestCuid:
    #  Tests execution time to ensure that time complexity doesn't increase.
    @pytest.mark.slow()
    def test_generate_performance(self: "TestCuid") -> None:
        timing_result = repeat(
            stmt="cuid.generate()",
            setup="from cuid2 import Cuid; cuid = Cuid()",
            repeat=10,
            number=50_000,
        )
        # 50k iterations of cuid.generate() should take less than 2 seconds
        assert min(timing_result) < 2

    #  Tests that generate() returns a string of length DEFAULT_LENGTH.
    def test_generate_default_length(self: "TestCuid") -> None:
        cuid = Cuid()
        assert len(cuid.generate()) == DEFAULT_LENGTH

    #  Tests that generate() returns a string starting with a letter.
    def test_generate_starts_with_letter(self: "TestCuid") -> None:
        cuid = Cuid()
        assert cuid.generate()[0].isalpha()

    #  Tests that generate() works when length parameter is None.
    def test_generate_length_none(self: "TestCuid") -> None:
        cuid = Cuid(length=10)
        assert len(cuid.generate(length=None)) == 10

    #  Tests that generate() works when length parameter is really long.
    def test_generate_really_long_length(self: "TestCuid") -> None:
        with pytest.raises(ValueError, match="Length must never exceed 98 characters."):
            Cuid(length=100)

    #  Tests that generate() works when length parameter is less than 2.
    def test_generate_length_less_than_2(self: "TestCuid") -> None:
        cuid = Cuid()
        assert len(cuid.generate(length=1)) == 1

    #  Tests that multiple instances of Cuid generate unique IDs.
    def test_generate_multiple_instances_unique_ids(self: "TestCuid") -> None:
        cuid1 = Cuid()
        cuid2 = Cuid()
        assert cuid1.generate() != cuid2.generate()

    #  Tests that the same instance of Cuid generates unique IDs.
    def test_generate_unique_ids(self: "TestCuid") -> None:
        cuid = Cuid()
        assert cuid.generate() != cuid.generate()

    #  Tests that generate() works when random_generator returns same values.
    def test_generate_same_random_values(self: "TestCuid", mocker: "Mock") -> None:
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
    def test_constructor_default_values(self: "TestCuid") -> None:
        # Initialize Cuid with default values
        cuid = Cuid()

        # Assert that the values are set to their default values
        assert isinstance(cuid._random, SystemRandom)
        assert callable(cuid._counter)
        assert cuid._length == DEFAULT_LENGTH
        assert isinstance(cuid._fingerprint, str)

    #  Tests that the random_generator and fingerprint functions are called correctly when mocked.
    def test_mock_random_generator_and_fingerprint(self: "TestCuid", mocker: "Mock") -> None:
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
    def test_generate_specified_length(self: "TestCuid") -> None:
        cuid = Cuid(length=10)
        result = cuid.generate()
        assert len(result) == 10

    #  Tests that the constructor initializes random, counter, length, and fingerprint.
    def test_constructor_initializes_members(self: "TestCuid", mocker: "Mock") -> None:
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
    def test_generate_uses_base36_encoding(self: "TestCuid", mocker: "Mock") -> None:
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
    def test_is_cuid_valid(self: "TestIsCuid", value: str) -> None:
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
    def test_is_cuid_invalid_shape_or_length(self: "TestIsCuid", value: str) -> None:
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
    def test_is_cuid_invalid_characters(self: "TestIsCuid", value: str) -> None:
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
    def test_is_cuid_invalid_whitespace(self: "TestIsCuid", value: str) -> None:
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
    def test_is_cuid_invalid_non_ascii(self: "TestIsCuid", value: str) -> None:
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
    def test_is_cuid_invalid_non_string(self: "TestIsCuid", value: object) -> None:
        assert Cuid.is_cuid(value) is False  # type: ignore[arg-type]

    #  Tests that is_cuid accepts str subclasses, since they are still strings.
    def test_is_cuid_str_subclass(self: "TestIsCuid") -> None:
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
        self: "TestIsCuid",
        value: str,
        kwargs: dict[str, int],
        expected: bool,
    ) -> None:
        assert Cuid.is_cuid(value, **kwargs) is expected

    #  Tests that min_length cannot go below MINIMUM_LENGTH: the identifier shape always needs 2+ characters.
    @pytest.mark.parametrize("min_length", [1, 0, -1, -5, -(10**9)])
    @pytest.mark.parametrize("value", ["", "a", "1"])
    def test_is_cuid_min_length_cannot_go_below_minimum(
        self: "TestIsCuid",
        value: str,
        min_length: int,
    ) -> None:
        assert Cuid.is_cuid(value, min_length=min_length) is False

    #  Tests that lowering min_length still accepts valid identifiers.
    @pytest.mark.parametrize("min_length", [MINIMUM_LENGTH, 1, 0, -1])
    def test_is_cuid_min_length_below_minimum_still_accepts_valid(self: "TestIsCuid", min_length: int) -> None:
        assert Cuid.is_cuid("ab", min_length=min_length) is True

    #  Tests that max_length cannot go above MAXIMUM_LENGTH, matching the generator's own limit.
    @pytest.mark.parametrize("max_length", [MAXIMUM_LENGTH + 1, 200, 10**9])
    def test_is_cuid_max_length_cannot_exceed_maximum(self: "TestIsCuid", max_length: int) -> None:
        assert Cuid.is_cuid("a" * (MAXIMUM_LENGTH + 1), max_length=max_length) is False
        assert Cuid.is_cuid("a" * 150, max_length=max_length) is False
        assert Cuid.is_cuid("a" * MAXIMUM_LENGTH, max_length=max_length) is True

    #  Tests that a min_length above MAXIMUM_LENGTH can never match.
    def test_is_cuid_min_length_above_maximum(self: "TestIsCuid") -> None:
        assert Cuid.is_cuid("a" * MAXIMUM_LENGTH, min_length=MAXIMUM_LENGTH + 1) is False

    #  Tests that max_length below MINIMUM_LENGTH can never match.
    @pytest.mark.parametrize("max_length", [1, 0, -1])
    def test_is_cuid_max_length_below_minimum(self: "TestIsCuid", max_length: int) -> None:
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
    def test_is_cuid_non_integer_bounds_raise(self: "TestIsCuid", kwargs: dict[str, object]) -> None:
        with pytest.raises(TypeError):
            Cuid.is_cuid("abc", **kwargs)  # type: ignore[arg-type]

    #  Tests that is_cuid can be called on an instance as well as on the class.
    def test_is_cuid_callable_on_instance(self: "TestIsCuid") -> None:
        cuid = Cuid()
        assert cuid.is_cuid(cuid.generate()) is True
        assert cuid.is_cuid("NOT-A-CUID") is False

    #  Tests that every generated id validates for every supported length, including the boundaries.
    #  The exact length is only asserted below MAXIMUM_LENGTH - 1: at 97 and 98 characters the generator
    #  occasionally returns a shorter id (the SHA3-512 base36 digest is not always long enough), but
    #  such ids are still valid.
    @pytest.mark.parametrize("length", [MINIMUM_LENGTH, 3, 10, DEFAULT_LENGTH, 50, MAXIMUM_LENGTH - 2, MAXIMUM_LENGTH])
    def test_is_cuid_accepts_generated_ids(self: "TestIsCuid", length: int) -> None:
        cuid = Cuid(length=length)
        for _ in range(250):
            generated = cuid.generate()
            assert len(generated) <= length
            if length < MAXIMUM_LENGTH - 1:
                assert len(generated) == length
            assert Cuid.is_cuid(generated) is True

    #  Tests that ids generated via generate(length=...) and via the wrapper also validate.
    def test_is_cuid_accepts_generate_override_and_wrapper(self: "TestIsCuid") -> None:
        cuid = Cuid()
        wrapper = cuid_wrapper()
        for _ in range(250):
            assert Cuid.is_cuid(cuid.generate(length=8)) is True
            assert Cuid.is_cuid(wrapper()) is True

    #  Tests that a tightened min/max still accepts a generated id of exactly that length.
    def test_is_cuid_generated_id_exact_bounds(self: "TestIsCuid") -> None:
        generated = Cuid().generate()
        assert Cuid.is_cuid(generated, min_length=DEFAULT_LENGTH, max_length=DEFAULT_LENGTH) is True
        assert Cuid.is_cuid(generated, min_length=DEFAULT_LENGTH + 1) is False
        assert Cuid.is_cuid(generated, max_length=DEFAULT_LENGTH - 1) is False

    #  Documents a known asymmetry: the generator can emit 1-character ids, but a valid CUID2 needs 2+ characters.
    #  If the generator's minimum length is ever raised to MINIMUM_LENGTH, this test should be updated.
    def test_is_cuid_rejects_single_character_generated_id(self: "TestIsCuid") -> None:
        generated = Cuid(length=1).generate()
        assert len(generated) == 1
        assert Cuid.is_cuid(generated) is False
        assert Cuid.is_cuid(generated, min_length=1) is False

    #  Tests that mutating a generated id in each way is detected.
    def test_is_cuid_detects_mutated_generated_id(self: "TestIsCuid") -> None:
        generated = Cuid().generate()
        assert Cuid.is_cuid(generated) is True
        assert Cuid.is_cuid("1" + generated[1:]) is False
        assert Cuid.is_cuid(generated.upper()) is False
        assert Cuid.is_cuid(generated + " ") is False
        assert Cuid.is_cuid(generated + "\n") is False
        assert Cuid.is_cuid(generated[:-1] + "!") is False
        assert Cuid.is_cuid("") is False


class TestCuidWrapper:
    def test_cuid_wrapper_is_callable(self: "TestCuidWrapper") -> None:
        """Tests that the function returns a callable."""
        cuid_func: Callable[[], str] = cuid_wrapper()
        assert callable(cuid_func)

    def test_cuid_wrapper_return_type(self: "TestCuidWrapper") -> None:
        """Tests that the function returns a callable that generates a CUID string."""
        cuid_func: Callable[[], str] = cuid_wrapper()
        assert isinstance(cuid_func(), str)

    def test_cuid_wrapper_no_parameters(self: "TestCuidWrapper") -> None:
        """Tests that the function doesn't accept any parameters."""
        cuid_func: Callable[[], str] = cuid_wrapper()
        with pytest.raises(
            TypeError,
            match="cuid\\(\\) takes 0 positional arguments but 1 was given",
        ):
            cuid_func(DEFAULT_LENGTH)  # type: ignore[call-arg]

    def test_cuid_wrapper_length(self: "TestCuidWrapper") -> None:
        """Tests that the function returns a callable that generates a CUID string with the default length."""
        cuid_func: Callable[[], str] = cuid_wrapper()
        assert len(cuid_func()) == DEFAULT_LENGTH
