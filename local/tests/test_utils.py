from __future__ import annotations

import math
import os
import random
import string
import subprocess
import sys
import threading
import time
from typing import TYPE_CHECKING

import pytest

from cuid2 import utils

if TYPE_CHECKING:
    from collections.abc import Callable
    from unittest.mock import Mock


class _LowBitStuckRandom(random.Random):
    """Test PRNG whose lowest 64 bits are permanently stuck at zero."""

    def getrandbits(self: _LowBitStuckRandom, k: int) -> int:
        return super().getrandbits(k) & ~((1 << 64) - 1)


class TestBase36Encode:
    #  Tests that the function returns "0" when given the number 0
    def test_zero_returns_0(self: TestBase36Encode) -> None:
        assert utils.base36_encode(0) == "0"

    #  Tests that the function raises a ValueError when given a negative number
    def test_negative_number_raises_value_error(self: TestBase36Encode) -> None:
        with pytest.raises(ValueError, match=r"Cannot encode negative integers\."):
            utils.base36_encode(-1)

    #  Tests that the function can handle the maximum value for an integer
    def test_max_int(self: TestBase36Encode) -> None:
        assert utils.base36_encode(2147483647) == "zik0zj"

    #  Tests that the function returns a string consisting only of lowercase letters and digits
    def test_returns_lowercase_letters_and_digits(self: TestBase36Encode) -> None:
        encoded_string = utils.base36_encode(123456789)
        assert all(c in string.digits + string.ascii_lowercase for c in encoded_string)

    #  Tests that the function can handle a large prime number
    def test_large_prime_number(self: TestBase36Encode) -> None:
        assert utils.base36_encode(982451653) == "g8xcjp"

    #  Tests that the function can handle a large composite number
    def test_large_composite_number(self: TestBase36Encode) -> None:
        assert utils.base36_encode(999999999) == "gjdgxr"

    #  Tests that the function can handle a large power of 2
    def test_large_power_of_2(self: TestBase36Encode) -> None:
        assert utils.base36_encode(2**50) == "b33j9ynrb4"

    #  Tests that the function can handle a large power of 10
    def test_large_power_of_10(self: TestBase36Encode) -> None:
        assert utils.base36_encode(10**50) == "1ku3a4pjfxx2nd2gl07gtqboljenwn75s"

    #  Tests the performance of the function for very large numbers
    def test_performance_for_very_large_numbers(self: TestBase36Encode) -> None:
        assert (
            utils.base36_encode(2**10000)
            == "2kqaqr9n8eopgtn6k95g23riodx51p4o3jwyma480okqkygdk2cn232qvv2svfuvbzb5dy9yeoqceom839h5k1yzf6izbx3rnrjx4pfili0r67ebjqnjhwqevgboilk8yf8ueh7pnd28hk2xttyvgmiqcew98grghfhqz4xe93yiifh69uh4kxt2ld4ba87izsm9u323ekhjh37k5tsyn9of1gds6lzq526i1r3f70gd74z9ni2b2ej456p7frfijzu9hpdkw1vpsuwds7zpbr7uwcu2qbb0o9djiehjcltlpptcqg19sxajz8vyffjeuajmdew0q9j9h7ovpgmyat92n3rx0fgfsu4kluaoi146z5v1t00q073fe6f6ijdue1g06lvqx9ijmezax2tooljo5c362eil7nkkz91d0n5ghfe1rhofsyujw4209klyhjzcu10ycc0oc19pq7sqo1ugs10ym59phjo752siiuj56z2yns5dtodwff92we0a9sgho98t2jgqtgiwilmcmksi5aighqi8h5pxsvyc6owrans06be91u2gtwi43s3i46rjkvpn85xzco0dgwfzzp8hto1axij5w3j69snadxvc0ed3971r936qzc0cyou95081lvplzcrid76kf8wbm68tj3zv4j9fj4dnl19etn1koc3hx8eixx85uda4rv92j3dl0ib8ixgeywnjmivv3kmich1balqsp1hd4b88r7aephwoc9uphu9u2eorlvjmquvqziuu7w1usbf3lmdx289lkdeyecnymd88xlb7thrlmxvzjlmnxfjzmqcnaie4sfz81mlqq6n48b4vdkh7gimhfy9rddxdy3fi2faochb1cnikvkwdz02qa5v9p3l7cnzhxqwhrqdhrcawfl2lbzvs26uzf2fyj2u5i7gv750aitt8drg8md9i551u8hpaw28r1p3qi29soq8d2iakhw2ezzeux71zlex537kgs18lgk56nw1gbrk00oqowzb5t117bvgp6221nr5slvxz3ozr2gqdzume9xuqpeeza98qd009p50qkmghyb3tqsyhmo72h9ptv98w6dh1vwrja2oa5lfi2ei234f2haziqh3jp0v8vv40tur6cydgv8dohm20yurg6gymgjgm3pb8q2hf57hxioeiyild50rersbfumcyc4ij5nhxavlg5s976mkphr0wurzuri1uk44vmrw6w3mftfozkxvo14aii0xct1t6czu9w9njatnx9igw51aqy3c7rjz7vugf0yzlo6t61a72ddp7lrd9ymgyca271cr17f16fojq5g688h6rgxg1hhb5zzedw23723s93mai3f603gd4utc7levfzpdhqt7l7t4b70efvq029zofoqrzgno8bpyg5vgz12jdun0of0ua47zzpa7wk0psnrq0yal1isbf6hbnlvfundz2hbrl4mfxnxxgobkv2jyaag9872k45x8uwau1mlzx8xhtc43829wyauwejfqifs4em5ipgih0ypn8bfjyq6b3blevcmrostiqldnqa7znph1zfm7xdjmhghmx57qit1ojxjkjliendm98redq1xtai822suagwdzhq1y8kf523m0nslhvjomttuydoqqe6pr5rf76aqe3pwx6pmcrub3gmvg6scojyjj4o429qjpzjsehoqe8y6rivp7i904dricmv1l75cfomy5x92cd34m7r8k886i7o58krwj5257b9wfq7dcj4mwq76vctcezae4v8jtz29fsjl2lbjqhxfjb8itp6x89ems9fga26i7t7zl5njmbqtp2jt9ommmhiz3ty7izh9gk5dxr26n9bz6j3swbu980hfd9v0vbdrn72ra3eiawckwkvhmdgfpi12cjamr0jf22jf268sg"  # noqa: E501
        )


class TestCreateLetter:
    #  Tests that create_letter function returns a lowercase letter
    def test_happy_path_create_letter(self: TestCreateLetter, mocker: Mock) -> None:
        mock_random = mocker.Mock()
        mock_random.getrandbits.return_value = 1 << (utils._LETTER_DRAW_BITS - 1)
        result = utils.create_letter(random_generator=mock_random)
        assert result == "n"
        assert result in string.ascii_lowercase
        mock_random.getrandbits.assert_called_once_with(utils._LETTER_DRAW_BITS)

    #  Tests that create_letter function returns a lowercase letter when random_generator returns 0
    def test_edge_case_create_letter_zero(self: TestCreateLetter, mocker: Mock) -> None:
        mock_random = mocker.Mock()
        mock_random.getrandbits.return_value = 0
        result = utils.create_letter(random_generator=mock_random)
        assert result == "a"
        assert result in string.ascii_lowercase
        mock_random.getrandbits.assert_called_once_with(utils._LETTER_DRAW_BITS)

    #  Tests that create_letter function returns a lowercase letter when random_generator returns max bits
    def test_edge_case_create_letter_one(self: TestCreateLetter, mocker: Mock) -> None:
        mock_random = mocker.Mock()
        mock_random.getrandbits.return_value = (1 << utils._LETTER_DRAW_BITS) - 1
        result = utils.create_letter(random_generator=mock_random)
        assert result == "z"
        assert result in string.ascii_lowercase
        mock_random.getrandbits.assert_called_once_with(utils._LETTER_DRAW_BITS)


class TestCreateHash:
    #  Tests that the output of create_hash() is always a string of length 98
    def test_hash_output_length(self: TestCreateHash) -> None:
        assert len(utils.create_hash()) == 98

    #  Tests that create_hash() returns the same output for the same input
    def test_same_output_for_same_input(self: TestCreateHash) -> None:
        input_str = "test string"
        assert utils.create_hash(input_str) == utils.create_hash(input_str)

    #  Tests that create_hash() returns a hash for an empty string input
    def test_empty_string_input(self: TestCreateHash) -> None:
        assert utils.create_hash("")

    #  Tests that create_hash() returns a hash for a string input containing special characters
    def test_special_characters_input(self: TestCreateHash) -> None:
        input_str = "test!@#$%^&*()_+-=[]{}|;':\",./<>? string"
        assert utils.create_hash(input_str)

    #  Tests that create_hash() returns a hash for a very long string input
    def test_very_long_string_input(self: TestCreateHash) -> None:
        input_str = "a" * 1000000
        assert utils.create_hash(input_str)
        assert len(utils.create_hash(str(input_str))) == 98

    #  Tests that create_hash() can handle large input strings
    def test_large_input_strings(self: TestCreateHash) -> None:
        input_str = "a" * 10000
        assert utils.create_hash(input_str)
        assert len(utils.create_hash(str(input_str))) == 98

    #  Tests that create_hash() can handle very large integers for base36 encoding
    def test_base36_encoding(self: TestCreateHash) -> None:
        input_int = 99999999999999999999999999999999999999999999999999999999999999999999999999
        assert utils.create_hash(str(input_int))
        assert len(utils.create_hash(str(input_int))) == 98

    #  Tests that create_hash() raises a TypeError if the input is not a string
    def test_non_string_input_types(self: TestCreateHash) -> None:
        with pytest.raises(AttributeError):
            utils.create_hash(12345)  # type: ignore[arg-type]

    #  Tests that create_hash() uses sha3_512 directly without a sha512 fallback attribute
    def test_create_hash_uses_sha3_512_directly(self: TestCreateHash, mocker: Mock) -> None:
        assert not hasattr(utils, "sha512")
        mock_hash = mocker.Mock()
        mock_hash.digest.return_value = b"\x08" + b"\x00" * 63
        mock_sha3 = mocker.patch("cuid2.utils.sha3_512", return_value=mock_hash)
        assert len(utils.create_hash("test")) == 98
        mock_sha3.assert_called_once_with(b"test")


class TestCreateEntropy:
    #  Tests that create_entropy returns a string of expected length and only contains characters
    #  from base36 alphabet when given a valid instance of Random and a positive length
    def test_create_entropy_happy(self: TestCreateEntropy, mocker: Mock) -> None:
        # Happy path test
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        result = utils.create_entropy(mock_random, length=4)
        assert len(result) == 4
        assert all(c in string.digits + string.ascii_lowercase for c in result)
        assert mock_random.getrandbits.call_count == 1

    #  Tests that create_entropy defaults to length 4 when length is omitted
    def test_create_entropy_default_length(self: TestCreateEntropy, mocker: Mock) -> None:
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        result = utils.create_entropy(mock_random)
        assert len(result) == 4
        assert all(c in string.digits + string.ascii_lowercase for c in result)
        assert mock_random.getrandbits.call_count == 1

    #  Tests that create_entropy raises a ValueError when given a valid instance of Random and a length of 0
    def test_create_entropy_zero_length(self: TestCreateEntropy, mocker: Mock) -> None:
        # Edge case test with length = 0
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        with pytest.raises(ValueError, match=r"Cannot create entropy without a length >= 1\."):
            utils.create_entropy(mock_random, length=0)
        assert mock_random.getrandbits.call_count == 0

    #  Tests that create_entropy raises a ValueError when given a valid instance of Random and a negative length
    def test_create_entropy_negative_length(self: TestCreateEntropy, mocker: Mock) -> None:
        # Edge case test with negative length
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        with pytest.raises(ValueError, match=r"Cannot create entropy without a length >= 1\."):
            utils.create_entropy(mock_random, length=-1)
        assert mock_random.getrandbits.call_count == 0

    #  Tests that create_entropy raises a TypeError when given an invalid instance of Random
    def test_create_entropy_invalid_random_generator(self: TestCreateEntropy) -> None:
        # Edge case test with invalid random generator
        with pytest.raises(AttributeError):
            utils.create_entropy("not a random generator")  # type: ignore[arg-type]

    #  Tests that create_entropy returns a string of expected length when given a
    #  valid instance of Random and a length equal to the maximum possible length (36)
    def test_create_entropy_length_max(self: TestCreateEntropy, mocker: Mock) -> None:
        # Happy path test with length = maximum possible length (36)
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        result = utils.create_entropy(mock_random, length=36)
        assert len(result) == 36
        assert all(c in string.digits + string.ascii_lowercase for c in result)
        assert mock_random.getrandbits.call_count == 1

    #  Tests that create_entropy returns a string of length 1 when given a valid instance of Random and a length of 1
    def test_create_entropy_length_one(self: TestCreateEntropy, mocker: Mock) -> None:
        # Happy path test with length = 1
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        result = utils.create_entropy(mock_random, length=1)
        assert len(result) == 1
        assert all(c in string.digits + string.ascii_lowercase for c in result)
        assert mock_random.getrandbits.call_count == 1

    #  Tests that create_entropy returns a string of expected length when given a valid instance of
    #  Random and a length greater than len(_POWERS_OF_36) - 1 (100)
    def test_create_entropy_length_greater_than_max(self: TestCreateEntropy, mocker: Mock) -> None:
        # Edge case test with length > 100 so both arms of length < len(_POWERS_OF_36) are covered
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        result = utils.create_entropy(mock_random, length=101)
        assert len(result) == 101
        assert all(c in string.digits + string.ascii_lowercase for c in result)
        assert mock_random.getrandbits.call_count == 1

    #  Tests that create_entropy returns a string of expected length when given a valid instance of
    #  Random and a length between 1 and the maximum possible length (36)
    def test_create_entropy_length_between_1_and_max(self: TestCreateEntropy, mocker: Mock) -> None:
        # Happy path test with length between 1 and maximum possible length (36)
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        result = utils.create_entropy(mock_random, length=10)
        assert len(result) == 10
        assert all(c in string.digits + string.ascii_lowercase for c in result)
        assert mock_random.getrandbits.call_count == 1

    #  Tests that create_entropy indexes BASE36_ALPHABET directly without calling base36_encode
    def test_create_entropy_does_not_call_base36_encode(self: TestCreateEntropy, mocker: Mock) -> None:
        spy = mocker.spy(utils, "base36_encode")
        mock_random = mocker.Mock()
        draw_bits = (36**4).bit_length() + 64
        mock_random.getrandbits.return_value = ((int("iiii", 36) << draw_bits) + 36**4 - 1) // 36**4
        assert utils.create_entropy(mock_random, length=4) == "iiii"
        assert spy.call_count == 0
        assert mock_random.getrandbits.call_count == 1


class TestCreateFingerprint:
    #  Tests that create_fingerprint returns a string of length BIG_LENGTH when valid fingerprint data is provided
    def test_create_fingerprint_with_valid_data(self: TestCreateFingerprint, mocker: Mock) -> None:
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        fingerprint_data = "test_data"
        expected_length = utils.BIG_LENGTH

        result = utils.create_fingerprint(random_generator=mock_random, fingerprint_data=fingerprint_data)

        assert len(result) == expected_length

    #  Tests that create_fingerprint generates valid fingerprint data when no fingerprint data is provided
    def test_create_fingerprint_with_empty_fingerprint_data(self: TestCreateFingerprint, mocker: Mock) -> None:
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        expected_length = utils.BIG_LENGTH

        result = utils.create_fingerprint(random_generator=mock_random)

        assert len(result) == expected_length

    #  Tests that create_fingerprint generates valid fingerprint data when the hostname is empty
    def test_create_fingerprint_with_empty_hostname(self: TestCreateFingerprint, mocker: Mock) -> None:
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        mocker.patch("socket.gethostname", return_value="")
        expected_length = utils.BIG_LENGTH

        result = utils.create_fingerprint(random_generator=mock_random)

        assert len(result) == expected_length

    #  Tests that create_fingerprint generates valid fingerprint data when the env variables are empty
    def test_create_fingerprint_with_empty_env_variables(self: TestCreateFingerprint, mocker: Mock) -> None:
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        mocker.patch.dict(os.environ, {})
        expected_length = utils.BIG_LENGTH

        result = utils.create_fingerprint(random_generator=mock_random)

        assert len(result) == expected_length

    #  Tests that create_fingerprint ignores invalid data types are provided as input
    def test_create_fingerprint_with_invalid_data_types(self: TestCreateFingerprint, mocker: Mock) -> None:
        mock_random = mocker.Mock()
        draw_bits = (36**32).bit_length() + 64
        mock_random.getrandbits.return_value = ((int("i" * 32, 36) << draw_bits) + 36**32 - 1) // 36**32
        non_string_data: int = 123
        fingerprint = utils.create_fingerprint(
            random_generator=mock_random,
            fingerprint_data=non_string_data,  # type: ignore[arg-type]
        )

        assert fingerprint == "ang0xqpl1depi0z4yaigbr4lh6bhc4gr"

    #  Tests that create_fingerprint raises an exception when the random generator is not provided
    def test_create_fingerprint_with_missing_random_generator(self: TestCreateFingerprint) -> None:
        with pytest.raises(TypeError):
            utils.create_fingerprint()  # type: ignore[call-arg]

    #  Tests that create_fingerprint returns a string of length BIG_LENGTH even when the entropy
    #  generated by create_entropy is shorter than BIG_LENGTH
    def test_create_fingerprint_with_invalid_length(self: TestCreateFingerprint, mocker: Mock) -> None:
        # Mock the create_entropy function to return a string shorter than BIG_LENGTH
        mocker.patch("cuid2.utils.create_entropy", return_value="abc")
        # Call the function with a random generator
        fingerprint = utils.create_fingerprint(mocker.Mock(), "fingerprint_data")
        # Assert that the length of the fingerprint is equal to BIG_LENGTH
        assert len(fingerprint) == utils.BIG_LENGTH

    #  Tests that create_fingerprint generates valid fingerprint data when all fingerprint
    #  data, hostname, and env variables are empty
    def test_create_fingerprint_with_empty_hostname_and_empty_env_variables(
        self: TestCreateFingerprint,
        mocker: Mock,
    ) -> None:
        mock_random = mocker.Mock()
        mock_random.getrandbits.side_effect = lambda k: 1 << (k - 1)
        # Mock os.getpid() and socket.gethostname() to return empty strings
        mocker.patch("os.getpid", return_value="")
        mocker.patch("socket.gethostname", return_value="")
        # Call the function with a random generator
        fingerprint = utils.create_fingerprint(random_generator=mock_random)
        # Assert that the length of the fingerprint is equal to BIG_LENGTH
        assert len(fingerprint) == utils.BIG_LENGTH

    #  Tests that create_fingerprint raises an exception when the random generator is not available
    def test_create_fingerprint_with_unavailable_random_generator(self: TestCreateFingerprint) -> None:
        # Call the function with a None random generator
        with pytest.raises(AttributeError):
            utils.create_fingerprint(random_generator=None)  # type: ignore[arg-type]

    def test_create_fingerprint_does_not_load_socket_when_fingerprint_data_provided(
        self: TestCreateFingerprint,
    ) -> None:
        code = (
            "import random, sys; "
            "import cuid2.utils as u; "
            "assert 'socket' not in sys.modules; "
            "u.create_fingerprint(random.Random(0), fingerprint_data='fixed'); "
            "assert 'socket' not in sys.modules"
        )
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-I", "-c", code],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


class TestCreateCounter:
    #  Tests that create_counter returns a function
    def test_create_counter_returns_function(self: TestCreateCounter) -> None:
        counter_func = utils.create_counter(0)
        assert callable(counter_func)

    #  Tests that the counter function increments the count variable
    def test_counter_increments_count(self: TestCreateCounter) -> None:
        counter_func = utils.create_counter(0)
        assert counter_func() == 1
        assert counter_func() == 2

    #  Tests that the counter function works correctly when count starts at a negative number
    def test_count_starts_at_negative_number(self: TestCreateCounter) -> None:
        counter_func = utils.create_counter(-10)
        assert counter_func() == -9
        assert counter_func() == -8

    #  Tests that the counter function works correctly when count is a large positive number
    def test_count_is_large_positive_number(self: TestCreateCounter) -> None:
        counter_func = utils.create_counter(1000000)
        assert counter_func() == 1000001
        assert counter_func() == 1000002

    #  Tests that the count variable is not modified outside the counter function
    def test_count_variable_not_modified_outside_function(self: TestCreateCounter) -> None:
        count = 0
        counter_func = utils.create_counter(count)
        assert counter_func() == 1
        assert count == 0

    #  Tests that multiple instances of the counter function can be created and called independently
    def test_multiple_instances_of_counter(self: TestCreateCounter) -> None:
        counter_func1 = utils.create_counter(0)
        counter_func2 = utils.create_counter(10)
        assert counter_func1() == 1
        assert counter_func2() == 11
        assert counter_func1() == 2
        assert counter_func2() == 12

    #  Tests that the returned value from the counter function is an integer
    def test_returned_value_is_integer(self: TestCreateCounter) -> None:
        counter = utils.create_counter(0)
        assert isinstance(counter(), int)

    #  Tests that create_counter returns a new instance of the counter function each time it is called
    def test_create_counter_returns_new_instance_each_time(self: TestCreateCounter) -> None:
        counter1 = utils.create_counter(0)
        counter2 = utils.create_counter(0)
        assert counter1 != counter2

    #  Tests that the count variable is not accessed outside the counter function
    def test_count_variable_not_accessed_outside_function(self: TestCreateCounter) -> None:
        counter = utils.create_counter(0)
        with pytest.raises(AttributeError):
            _ = counter.count  # type: ignore[attr-defined]

    def test_counter_thread_safety_barrier(self: TestCreateCounter) -> None:
        """Tests that 1,600,000 increments across 8 threads produce a contiguous, duplicate-free sequence.

        An unsynchronized counter on free-threaded Python returns roughly 320,000-380,000 unique values here.
        """
        counter = utils.create_counter(0)
        num_threads = 8
        increments_per_thread = 200_000
        barrier = threading.Barrier(num_threads)
        buckets: list[list[int]] = [[] for _ in range(num_threads)]

        def worker(index: int) -> None:
            barrier.wait()
            buckets[index] = [counter() for _ in range(increments_per_thread)]

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        combined = [val for bucket in buckets for val in bucket]
        total = num_threads * increments_per_thread
        assert len(combined) == total
        assert set(combined) == set(range(1, total + 1))
        assert counter() == total + 1

    def test_counter_thread_safety_forced_interleaving(self: TestCreateCounter) -> None:
        """Tests that the counter lock prevents lost updates even when addition yields the GIL."""

        class _YieldingInt(int):
            def __add__(self: _YieldingInt, other: int) -> _YieldingInt:
                time.sleep(0)
                return _YieldingInt(super().__add__(other))

        counter = utils.create_counter(_YieldingInt(0))
        num_threads = 8
        increments_per_thread = 25
        barrier = threading.Barrier(num_threads)
        buckets: list[list[int]] = [[] for _ in range(num_threads)]

        def worker(index: int) -> None:
            barrier.wait()
            buckets[index] = [int(counter()) for _ in range(increments_per_thread)]

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        combined = [val for bucket in buckets for val in bucket]
        total = num_threads * increments_per_thread
        assert set(combined) == set(range(1, total + 1))

    def test_counter_reentrant_call_on_same_thread_does_not_deadlock(self: TestCreateCounter) -> None:
        """Tests that the counter re-entered on the same thread (as from a signal handler) completes."""
        nested: list[int] = []
        counters: list[Callable[[], int]] = []

        class _ReentrantInt(int):
            def __add__(self: _ReentrantInt, other: int) -> _ReentrantInt:
                if not nested:
                    nested.append(0)
                    nested[0] = int(counters[0]())
                return _ReentrantInt(super().__add__(other))

        counters.append(utils.create_counter(_ReentrantInt(0)))
        outer: list[int] = []
        thread = threading.Thread(target=lambda: outer.append(int(counters[0]())), daemon=True)
        thread.start()
        thread.join(timeout=10)

        assert not thread.is_alive(), "re-entrant counter call deadlocked on the counter lock"
        assert len(outer) == 1
        assert nested[0] >= 1


class TestFixedPointScalingAndHashSlice:
    def test_nist_oversampling_bias_bound_proof(self: TestFixedPointScalingAndHashSlice) -> None:
        assert 1 << utils._COUNTER_DRAW_BITS >= (1 << 64) * utils.INITIAL_COUNT_MAX
        assert 1 << utils._LETTER_DRAW_BITS >= (1 << 64) * utils.ASCII_LOWERCASE_LEN

        for length in range(1, 102):
            modulus = utils._POWERS_OF_36[length] if length < len(utils._POWERS_OF_36) else 36**length
            draw_bits = modulus.bit_length() + utils._OVERSAMPLE_BITS
            assert 1 << draw_bits >= (1 << 64) * modulus

        for length in range(1, 99):
            modulus = utils.ASCII_LOWERCASE_LEN * utils._POWERS_OF_36[length]
            draw_bits = utils._letter_and_entropy_bits(length)
            assert 1 << draw_bits >= (1 << 64) * modulus

    def test_boundary_midpoint_monotonicity_and_float_equivalence(
        self: TestFixedPointScalingAndHashSlice,
    ) -> None:
        moduli = (26, 36, utils.INITIAL_COUNT_MAX, 36**24, 26 * 36**24)
        for modulus in moduli:
            k = modulus.bit_length() + 64
            assert utils._scale_randbits(0, modulus, k) == 0
            assert utils._scale_randbits(1 << (k - 1), modulus, k) == modulus // 2
            assert utils._scale_randbits((1 << k) - 1, modulus, k) == modulus - 1

            sample_points = [
                0,
                1,
                (1 << (k - 2)) - 1,
                1 << (k - 2),
                (1 << (k - 1)) - 1,
                1 << (k - 1),
                (3 << (k - 2)) - 1,
                3 << (k - 2),
                (1 << k) - 2,
                (1 << k) - 1,
            ]
            scaled_points = [utils._scale_randbits(x, modulus, k) for x in sample_points]
            assert scaled_points == sorted(scaled_points)

        k_fused = utils._letter_and_entropy_bits(24)
        assert utils._decode_letter_and_entropy(0, 24) == ("a", "0" * 24)
        assert utils._decode_letter_and_entropy(1 << (k_fused - 1), 24)[0] == "n"
        assert utils._decode_letter_and_entropy((1 << k_fused) - 1, 24) == ("z", "z" * 24)

        u53_samples = [
            0,
            1,
            2,
            (1 << 26) - 1,
            1 << 26,
            (1 << 52) - 1,
            1 << 52,
            (1 << 52) + 123456789,
            (1 << 53) - 2,
            (1 << 53) - 1,
        ]
        for modulus in (26, 36, utils.INITIAL_COUNT_MAX):
            k = modulus.bit_length() + 64
            for u53 in u53_samples:
                assert utils._scale_randbits(u53 << (k - 53), modulus, k) == (u53 * modulus) >> 53

            for j in (0, 1, 2, 17, 1023, (1 << 10) + 7, (1 << 19) - 1, 1 << 19, (1 << 20) - 1):
                assert j * modulus < 1 << 53
                u53 = j << (53 - 20)
                assert utils._scale_randbits(u53 << (k - 53), modulus, k) == math.floor((u53 / 2**53) * modulus)

    def test_low_64_bit_perturbation_bound(self: TestFixedPointScalingAndHashSlice) -> None:
        low_mask = (1 << 64) - 1
        for modulus in (26, 36, utils.INITIAL_COUNT_MAX, 36**24, 26 * 36**24):
            k = modulus.bit_length() + 64
            high_bits = k - 64
            max_high = (1 << high_bits) - 1
            for x_high in (
                0,
                1,
                2,
                max_high // 4,
                max_high // 3,
                max_high // 2,
                (3 * max_high) // 4,
                max_high - 1,
                max_high,
            ):
                low_zero = utils._scale_randbits(x_high << 64, modulus, k)
                low_ones = utils._scale_randbits((x_high << 64) | low_mask, modulus, k)
                assert 0 <= low_ones - low_zero <= 1

    def test_low_bit_stuck_random_immunity(self: TestFixedPointScalingAndHashSlice) -> None:
        rng = _LowBitStuckRandom(42)
        sample_bits = rng.getrandbits(utils._LETTER_DRAW_BITS)
        assert sample_bits % 2 == 0
        assert sample_bits % 4 == 0

        rng_letters = _LowBitStuckRandom(42)
        letters = {utils.create_letter(rng_letters) for _ in range(500)}
        assert letters == set(utils.ASCII_LOWERCASE)

        rng_entropy = _LowBitStuckRandom(42)
        entropy_draws = [utils.create_entropy(rng_entropy, 24) for _ in range(500)]
        all_chars = {ch for draw in entropy_draws for ch in draw}
        assert all_chars == set(utils.BASE36_ALPHABET)
        for pos in range(24):
            parities = {utils.BASE36_ALPHABET.index(draw[pos]) % 2 for draw in entropy_draws}
            assert parities == {0, 1}

        rng_counter = _LowBitStuckRandom(42)
        counter_parities = {utils._create_initial_count(rng_counter) % 2 for _ in range(500)}
        assert counter_parities == {0, 1}

    def test_create_hash_slice_boundary_matrix(
        self: TestFixedPointScalingAndHashSlice,
        mocker: Mock,
    ) -> None:
        boundary_ints = [
            0,
            1,
            35,
            36,
            36**97 - 1,
            36**97,
            36**98 - 1,
            36**98,
            36**98 + 1,
            36**99 - 1,
            36**99,
            36**99 + 1,
            (1 << 512) - 1,
        ]
        for boundary_int in boundary_ints:
            mock_hash = mocker.Mock()
            mock_hash.digest.return_value = boundary_int.to_bytes(64, byteorder="big")
            mocker.patch("cuid2.utils.sha3_512", return_value=mock_hash)

            full_hash = utils.create_hash("boundary")
            assert utils._create_hash_slice("boundary", 0, utils.BIG_LENGTH) == full_hash[: utils.BIG_LENGTH]
            for length in range(1, utils.MAXIMUM_LENGTH + 1):
                assert utils._create_hash_slice("boundary", 0, length) == full_hash[:length]
                assert utils._create_hash_slice("boundary", 1, length) == full_hash[1:length]
