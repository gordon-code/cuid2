from math import floor
from secrets import SystemRandom
from timeit import repeat
from typing import TYPE_CHECKING, Callable

import pytest

from cuid2 import DEFAULT_LENGTH, INITIAL_COUNT_MAX, Cuid, cuid_wrapper
from cuid2.cli import main as cli_main
from cuid2.generator import MAXIMUM_LENGTH

if TYPE_CHECKING:
    from unittest.mock import Mock


class TestCuid:
    #  Tests execution time to ensure that time complexity doesn't increase.
    @pytest.mark.slow
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
        with pytest.raises(ValueError, match=r"Length must never exceed 98 characters\."):
            Cuid(length=100)
        cuid = Cuid()
        with pytest.raises(ValueError, match=r"Length must never exceed 98 characters\."):
            cuid.generate(length=100)

    #  Tests that Cuid and generate() raise ValueError when length is less than 1 or a boolean.
    @pytest.mark.parametrize("invalid_length", [0, -1, True, False])
    def test_generate_non_positive_length(self: "TestCuid", invalid_length: int) -> None:
        with pytest.raises(ValueError, match=r"Length must be at least 1 character\."):
            Cuid(length=invalid_length)
        cuid = Cuid()
        with pytest.raises(ValueError, match=r"Length must be at least 1 character\."):
            cuid.generate(length=invalid_length)

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

    @pytest.mark.parametrize("length", [1, 10, 32])
    def test_cuid_wrapper_custom_length(self: "TestCuidWrapper", length: int) -> None:
        """Tests that cuid_wrapper generates a CUID string with a specified length."""
        cuid_func: Callable[[], str] = cuid_wrapper(length=length)
        assert len(cuid_func()) == length

    @pytest.mark.parametrize(
        ("invalid_length", "expected_match"),
        [
            (0, r"Length must be at least 1 character\."),
            (-1, r"Length must be at least 1 character\."),
            (True, r"Length must be at least 1 character\."),
            (MAXIMUM_LENGTH + 1, r"Length must never exceed 98 characters\."),
        ],
    )
    def test_cuid_wrapper_invalid_length(
        self: "TestCuidWrapper",
        invalid_length: int,
        expected_match: str,
    ) -> None:
        """Tests that cuid_wrapper raises ValueError when length is out of bounds."""
        with pytest.raises(ValueError, match=expected_match):
            cuid_wrapper(length=invalid_length)


class TestCli:
    def test_cli_default_length(self: "TestCli", capsys: pytest.CaptureFixture[str]) -> None:
        """Tests that the CLI prints a default-length CUID when invoked without arguments."""
        cli_main([])
        output = capsys.readouterr().out.strip()
        assert len(output) == DEFAULT_LENGTH
        assert output[0].isalpha()

    @pytest.mark.parametrize("length", [1, 10, 32])
    def test_cli_custom_length(self: "TestCli", length: int, capsys: pytest.CaptureFixture[str]) -> None:
        """Tests that the CLI prints a CUID of the requested custom length."""
        cli_main([str(length)])
        output = capsys.readouterr().out.strip()
        assert len(output) == length
        assert output[0].isalpha()

    @pytest.mark.parametrize(
        ("arg", "expected_match"),
        [
            ("0", r"Length must be at least 1 character\."),
            ("-5", r"Length must be at least 1 character\."),
            (str(MAXIMUM_LENGTH + 1), r"Length must never exceed 98 characters\."),
        ],
    )
    def test_cli_invalid_lengths(self: "TestCli", arg: str, expected_match: str) -> None:
        """Tests that the CLI rejects lengths <= 0 and > MAXIMUM_LENGTH."""
        with pytest.raises(ValueError, match=expected_match):
            cli_main([arg])

    def test_cli_non_integer_argument(self: "TestCli") -> None:
        """Tests that the CLI exits when given a non-integer argument."""
        with pytest.raises(SystemExit):
            cli_main(["invalid"])
