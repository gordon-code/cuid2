from math import floor
from secrets import SystemRandom
from timeit import repeat
from typing import TYPE_CHECKING

import pytest

from cuid2 import CUID, DEFAULT_LENGTH, INITIAL_COUNT_MAX, Cuid

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

    # Tests that instantiating the CUID class provides a deprecation warning.
    def test_constructor_deprecation_warning(self: "TestCuid") -> None:
        with pytest.deprecated_call():
            cuid = CUID()
            assert isinstance(cuid, Cuid)

    # Tests that subclassing the CUID class provides a deprecation warning.
    def test_subclass_deprecation_warning(self: "TestCuid") -> None:
        with pytest.deprecated_call():

            class CuidSubclass(CUID):
                pass
