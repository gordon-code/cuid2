import os
import string
from typing import TYPE_CHECKING

import pytest

from cuid2 import utils

if TYPE_CHECKING:
    from unittest.mock import Mock


class TestBase36Encode:
    #  Tests that the function returns "0" when given the number 0
    def test_zero_returns_0(self: "TestBase36Encode") -> None:
        assert utils.custom_base_encode(0) == "0"

    #  Tests that the function raises a ValueError when given a negative number
    def test_negative_number_raises_value_error(self: "TestBase36Encode") -> None:
        with pytest.raises(ValueError, match="Cannot encode negative integers."):
            utils.custom_base_encode(-1)

    #  Tests that the function can handle the maximum value for an integer
    def test_max_int(self: "TestBase36Encode") -> None:
        assert utils.custom_base_encode(2147483647) == "zik0zj"

    #  Tests that the function returns a string consisting only of lowercase letters and digits
    def test_returns_lowercase_letters_and_digits(self: "TestBase36Encode") -> None:
        encoded_string = utils.custom_base_encode(123456789)
        assert all(c in string.digits + string.ascii_lowercase for c in encoded_string)

    #  Tests that the function can handle a large prime number
    def test_large_prime_number(self: "TestBase36Encode") -> None:
        assert utils.custom_base_encode(982451653) == "g8xcjp"

    #  Tests that the function can handle a large composite number
    def test_large_composite_number(self: "TestBase36Encode") -> None:
        assert utils.custom_base_encode(999999999) == "gjdgxr"

    #  Tests that the function can handle a large power of 2
    def test_large_power_of_2(self: "TestBase36Encode") -> None:
        assert utils.custom_base_encode(2**50) == "b33j9ynrb4"

    #  Tests that the function can handle a large power of 10
    def test_large_power_of_10(self: "TestBase36Encode") -> None:
        assert utils.custom_base_encode(10**50) == "1ku3a4pjfxx2nd2gl07gtqboljenwn75s"

    #  Tests the performance of the function for very large numbers
    def test_performance_for_very_large_numbers(self: "TestBase36Encode") -> None:
        assert (
            utils.custom_base_encode(2**10000)
            == "2kqaqr9n8eopgtn6k95g23riodx51p4o3jwyma480okqkygdk2cn232qvv2svfuvbzb5dy9yeoqceom839h5k1yzf6izbx3rnrjx4pfili0r67ebjqnjhwqevgboilk8yf8ueh7pnd28hk2xttyvgmiqcew98grghfhqz4xe93yiifh69uh4kxt2ld4ba87izsm9u323ekhjh37k5tsyn9of1gds6lzq526i1r3f70gd74z9ni2b2ej456p7frfijzu9hpdkw1vpsuwds7zpbr7uwcu2qbb0o9djiehjcltlpptcqg19sxajz8vyffjeuajmdew0q9j9h7ovpgmyat92n3rx0fgfsu4kluaoi146z5v1t00q073fe6f6ijdue1g06lvqx9ijmezax2tooljo5c362eil7nkkz91d0n5ghfe1rhofsyujw4209klyhjzcu10ycc0oc19pq7sqo1ugs10ym59phjo752siiuj56z2yns5dtodwff92we0a9sgho98t2jgqtgiwilmcmksi5aighqi8h5pxsvyc6owrans06be91u2gtwi43s3i46rjkvpn85xzco0dgwfzzp8hto1axij5w3j69snadxvc0ed3971r936qzc0cyou95081lvplzcrid76kf8wbm68tj3zv4j9fj4dnl19etn1koc3hx8eixx85uda4rv92j3dl0ib8ixgeywnjmivv3kmich1balqsp1hd4b88r7aephwoc9uphu9u2eorlvjmquvqziuu7w1usbf3lmdx289lkdeyecnymd88xlb7thrlmxvzjlmnxfjzmqcnaie4sfz81mlqq6n48b4vdkh7gimhfy9rddxdy3fi2faochb1cnikvkwdz02qa5v9p3l7cnzhxqwhrqdhrcawfl2lbzvs26uzf2fyj2u5i7gv750aitt8drg8md9i551u8hpaw28r1p3qi29soq8d2iakhw2ezzeux71zlex537kgs18lgk56nw1gbrk00oqowzb5t117bvgp6221nr5slvxz3ozr2gqdzume9xuqpeeza98qd009p50qkmghyb3tqsyhmo72h9ptv98w6dh1vwrja2oa5lfi2ei234f2haziqh3jp0v8vv40tur6cydgv8dohm20yurg6gymgjgm3pb8q2hf57hxioeiyild50rersbfumcyc4ij5nhxavlg5s976mkphr0wurzuri1uk44vmrw6w3mftfozkxvo14aii0xct1t6czu9w9njatnx9igw51aqy3c7rjz7vugf0yzlo6t61a72ddp7lrd9ymgyca271cr17f16fojq5g688h6rgxg1hhb5zzedw23723s93mai3f603gd4utc7levfzpdhqt7l7t4b70efvq029zofoqrzgno8bpyg5vgz12jdun0of0ua47zzpa7wk0psnrq0yal1isbf6hbnlvfundz2hbrl4mfxnxxgobkv2jyaag9872k45x8uwau1mlzx8xhtc43829wyauwejfqifs4em5ipgih0ypn8bfjyq6b3blevcmrostiqldnqa7znph1zfm7xdjmhghmx57qit1ojxjkjliendm98redq1xtai822suagwdzhq1y8kf523m0nslhvjomttuydoqqe6pr5rf76aqe3pwx6pmcrub3gmvg6scojyjj4o429qjpzjsehoqe8y6rivp7i904dricmv1l75cfomy5x92cd34m7r8k886i7o58krwj5257b9wfq7dcj4mwq76vctcezae4v8jtz29fsjl2lbjqhxfjb8itp6x89ems9fga26i7t7zl5njmbqtp2jt9ommmhiz3ty7izh9gk5dxr26n9bz6j3swbu980hfd9v0vbdrn72ra3eiawckwkvhmdgfpi12cjamr0jf22jf268sg"  # noqa: E501
        )


class TestCreateLetter:
    #  Tests that create_letter function returns a lowercase letter
    def test_happy_path_create_letter(self: "TestCreateLetter", mocker: "Mock") -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        assert utils.create_letter(random_generator=mock_random) in string.ascii_lowercase

    #  Tests that create_letter function returns a lowercase letter when random_generator returns 0
    def test_edge_case_create_letter_zero(self: "TestCreateLetter", mocker: "Mock") -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0
        assert utils.create_letter(random_generator=mock_random) in string.ascii_lowercase

    #  Tests that create_letter function returns a lowercase letter when random_generator returns 1
    def test_edge_case_create_letter_one(self: "TestCreateLetter", mocker: "Mock") -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.999
        assert utils.create_letter(random_generator=mock_random) in string.ascii_lowercase


class TestCreateHash:
    #  Tests that the output of create_hash() is always a string of length 98
    def test_hash_output_length(self: "TestCreateHash") -> None:
        assert len(utils.create_hash()) == 98

    #  Tests that create_hash() returns the same output for the same input
    def test_same_output_for_same_input(self: "TestCreateHash") -> None:
        input_str = "test string"
        assert utils.create_hash(input_str) == utils.create_hash(input_str)

    #  Tests that create_hash() returns a hash for an empty string input
    def test_empty_string_input(self: "TestCreateHash") -> None:
        assert utils.create_hash("")

    #  Tests that create_hash() returns a hash for a string input containing special characters
    def test_special_characters_input(self: "TestCreateHash") -> None:
        input_str = "test!@#$%^&*()_+-=[]{}|;':\",./<>? string"
        assert utils.create_hash(input_str)

    #  Tests that create_hash() returns a hash for a very long string input
    def test_very_long_string_input(self: "TestCreateHash") -> None:
        input_str = "a" * 1000000
        assert utils.create_hash(input_str)
        assert len(utils.create_hash(str(input_str))) == 98

    #  Tests that create_hash() can handle large input strings
    def test_large_input_strings(self: "TestCreateHash") -> None:
        input_str = "a" * 10000
        assert utils.create_hash(input_str)
        assert len(utils.create_hash(str(input_str))) == 98

    #  Tests that create_hash() can handle very large integers for base36 encoding
    def test_base36_encoding(self: "TestCreateHash") -> None:
        input_int = 99999999999999999999999999999999999999999999999999999999999999999999999999
        assert utils.create_hash(str(input_int))
        assert len(utils.create_hash(str(input_int))) == 98

    #  Tests that create_hash() raises a TypeError if the input is not a string
    def test_non_string_input_types(self: "TestCreateHash") -> None:
        with pytest.raises(AttributeError):
            utils.create_hash(12345)  # type: ignore[arg-type]


class TestCreateEntropy:
    #  Tests that create_entropy returns a string of expected length and only contains characters
    #  from base36 alphabet when given a valid instance of Random and a positive length
    def test_create_entropy_happy(self: "TestCreateEntropy", mocker: "Mock") -> None:
        # Happy path test
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        result = utils.create_entropy(mock_random, length=4)
        assert len(result) == 4
        assert all(c in string.digits + string.ascii_lowercase for c in result)

    #  Tests that create_entropy returns a string of expected length and only contains
    #  characters from base36 alphabet when given a valid instance of Random and a positive
    #  length, even if the random generator returns values outside the range [0, 1)
    def test_create_entropy_random_generator_out_of_range(self: "TestCreateEntropy", mocker: "Mock") -> None:
        # Test with random generator returning values outside [0, 1)
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        result = utils.create_entropy(mock_random, length=4)
        assert len(result) == 4
        assert all(c in string.digits + string.ascii_lowercase for c in result)

    #  Tests that create_entropy raises a ValueError when given a valid instance of Random and a length of 0
    def test_create_entropy_zero_length(self: "TestCreateEntropy", mocker: "Mock") -> None:
        # Edge case test with length = 0
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        with pytest.raises(ValueError, match="Cannot create entropy without a length >= 1."):
            utils.create_entropy(mock_random, length=0)

    #  Tests that create_entropy raises a ValueError when given a valid instance of Random and a negative length
    def test_create_entropy_negative_length(self: "TestCreateEntropy", mocker: "Mock") -> None:
        # Edge case test with negative length
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        with pytest.raises(ValueError, match="Cannot create entropy without a length >= 1."):
            utils.create_entropy(mock_random, length=-1)

    #  Tests that create_entropy raises a TypeError when given an invalid instance of Random
    def test_create_entropy_invalid_random_generator(self: "TestCreateEntropy") -> None:
        # Edge case test with invalid random generator
        with pytest.raises(AttributeError):
            utils.create_entropy("not a random generator")  # type: ignore[arg-type]

    #  Tests that create_entropy returns a string of expected length when given a
    #  valid instance of Random and a length equal to the maximum possible length (36)
    def test_create_entropy_length_max(self: "TestCreateEntropy", mocker: "Mock") -> None:
        # Happy path test with length = maximum possible length (36)
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        result = utils.create_entropy(mock_random, length=36)
        assert len(result) == 36
        assert all(c in string.digits + string.ascii_lowercase for c in result)

    #  Tests that create_entropy returns a string of length 1 when given a valid instance of Random and a length of 1
    def test_create_entropy_length_one(self: "TestCreateEntropy", mocker: "Mock") -> None:
        # Happy path test with length = 1
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        result = utils.create_entropy(mock_random, length=1)
        assert len(result) == 1
        assert all(c in string.digits + string.ascii_lowercase for c in result)

    #  Tests that create_entropy returns a string of expected length when given a valid instance of
    #  Random and a length greater than the maximum possible length (36)
    def test_create_entropy_length_greater_than_max(self: "TestCreateEntropy", mocker: "Mock") -> None:
        # Edge case test with length > maximum possible length (36)
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        result = utils.create_entropy(mock_random, length=40)
        assert len(result) == 40
        assert all(c in string.digits + string.ascii_lowercase for c in result)

    #  Tests that create_entropy returns a string of expected length when given a valid instance of
    #  Random and a length between 1 and the maximum possible length (36)
    def test_create_entropy_length_between_1_and_max(self: "TestCreateEntropy", mocker: "Mock") -> None:
        # Happy path test with length between 1 and maximum possible length (36)
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        result = utils.create_entropy(mock_random, length=10)
        assert len(result) == 10
        assert all(c in string.digits + string.ascii_lowercase for c in result)


class TestCreateFingerprint:
    #  Tests that create_fingerprint returns a string of length BIG_LENGTH when valid fingerprint data is provided
    def test_create_fingerprint_with_valid_data(self: "TestCreateFingerprint", mocker: "Mock") -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        fingerprint_data = "test_data"
        expected_length = utils.BIG_LENGTH

        result = utils.create_fingerprint(random_generator=mock_random, fingerprint_data=fingerprint_data)

        assert len(result) == expected_length

    #  Tests that create_entropy generates valid entropy when the random generator is provided
    def test_create_entropy_with_valid_data(self: "TestCreateFingerprint", mocker: "Mock") -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        length = 4
        expected_length = length

        result = utils.create_entropy(random_generator=mock_random, length=length)

        assert len(result) == expected_length

    #  Tests that create_fingerprint generates valid fingerprint data when no fingerprint data is provided
    def test_create_fingerprint_with_empty_fingerprint_data(self: "TestCreateFingerprint", mocker: "Mock") -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        expected_length = utils.BIG_LENGTH

        result = utils.create_fingerprint(random_generator=mock_random)

        assert len(result) == expected_length

    #  Tests that create_fingerprint generates valid fingerprint data when the hostname is empty
    def test_create_fingerprint_with_empty_hostname(self: "TestCreateFingerprint", mocker: "Mock") -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        mocker.patch("socket.gethostname", return_value="")
        expected_length = utils.BIG_LENGTH

        result = utils.create_fingerprint(random_generator=mock_random)

        assert len(result) == expected_length

    #  Tests that create_fingerprint generates valid fingerprint data when the env variables are empty
    def test_create_fingerprint_with_empty_env_variables(self: "TestCreateFingerprint", mocker: "Mock") -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        mocker.patch.dict(os.environ, {})
        expected_length = utils.BIG_LENGTH

        result = utils.create_fingerprint(random_generator=mock_random)

        assert len(result) == expected_length

    #  Tests that create_fingerprint ignores invalid data types are provided as input
    def test_create_fingerprint_with_invalid_data_types(self: "TestCreateFingerprint", mocker: "Mock") -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        non_string_data: int = 123
        fingerprint = utils.create_fingerprint(
            random_generator=mock_random,
            fingerprint_data=non_string_data,  # type: ignore[arg-type]
        )

        assert fingerprint == "ang0xqpl1depi0z4yaigbr4lh6bhc4gr"

    #  Tests that create_fingerprint raises an exception when the random generator is not provided
    def test_create_fingerprint_with_missing_random_generator(self: "TestCreateFingerprint") -> None:
        with pytest.raises(TypeError):
            utils.create_fingerprint()  # type: ignore[call-arg]

    #  Tests that create_entropy generates valid entropy when an invalid length is provided
    def test_create_entropy_with_invalid_length(self: "TestCreateFingerprint", mocker: "Mock") -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        invalid_length = -1

        with pytest.raises(ValueError, match="Cannot create entropy without a length >= 1."):
            utils.create_entropy(random_generator=mock_random, length=invalid_length)

    #  Tests that create_fingerprint returns a string of length BIG_LENGTH even when the entropy
    #  generated by create_entropy is shorter than BIG_LENGTH
    def test_create_fingerprint_with_invalid_length(self: "TestCreateFingerprint", mocker: "Mock") -> None:
        # Mock the create_entropy function to return a string shorter than BIG_LENGTH
        mocker.patch("cuid2.utils.create_entropy", return_value="abc")
        # Call the function with a random generator
        fingerprint = utils.create_fingerprint(mocker.Mock(), "fingerprint_data")
        # Assert that the length of the fingerprint is equal to BIG_LENGTH
        assert len(fingerprint) == utils.BIG_LENGTH

    #  Tests that create_fingerprint generates valid fingerprint data when all fingerprint
    #  data, hostname, and env variables are empty
    def test_create_fingerprint_with_empty_hostname_and_empty_env_variables(
        self: "TestCreateFingerprint",
        mocker: "Mock",
    ) -> None:
        mock_random = mocker.Mock()
        mock_random.random.return_value = 0.5
        # Mock os.getpid() and socket.gethostname() to return empty strings
        mocker.patch("os.getpid", return_value="")
        mocker.patch("socket.gethostname", return_value="")
        # Call the function with a random generator
        fingerprint = utils.create_fingerprint(random_generator=mock_random)
        # Assert that the length of the fingerprint is equal to BIG_LENGTH
        assert len(fingerprint) == utils.BIG_LENGTH

    #  Tests that create_fingerprint raises an exception when the random generator is not available
    def test_create_fingerprint_with_unavailable_random_generator(self: "TestCreateFingerprint") -> None:
        # Call the function with a None random generator
        with pytest.raises(AttributeError):
            utils.create_fingerprint(random_generator=None)  # type: ignore[arg-type]


class TestCreateCounter:
    #  Tests that create_counter returns a function
    def test_create_counter_returns_function(self: "TestCreateCounter") -> None:
        counter_func = utils.create_counter(0)
        assert callable(counter_func)

    #  Tests that the counter function increments the count variable
    def test_counter_increments_count(self: "TestCreateCounter") -> None:
        counter_func = utils.create_counter(0)
        assert counter_func() == 1
        assert counter_func() == 2

    #  Tests that the counter function works correctly when count starts at a negative number
    def test_count_starts_at_negative_number(self: "TestCreateCounter") -> None:
        counter_func = utils.create_counter(-10)
        assert counter_func() == -9
        assert counter_func() == -8

    #  Tests that the counter function works correctly when count is a large positive number
    def test_count_is_large_positive_number(self: "TestCreateCounter") -> None:
        counter_func = utils.create_counter(1000000)
        assert counter_func() == 1000001
        assert counter_func() == 1000002

    #  Tests that the count variable is not modified outside the counter function
    def test_count_variable_not_modified_outside_function(self: "TestCreateCounter") -> None:
        count = 0
        counter_func = utils.create_counter(count)
        assert counter_func() == 1
        assert count == 0

    #  Tests that multiple instances of the counter function can be created and called independently
    def test_multiple_instances_of_counter(self: "TestCreateCounter") -> None:
        counter_func1 = utils.create_counter(0)
        counter_func2 = utils.create_counter(10)
        assert counter_func1() == 1
        assert counter_func2() == 11
        assert counter_func1() == 2
        assert counter_func2() == 12

    #  Tests that the returned value from the counter function is an integer
    def test_returned_value_is_integer(self: "TestCreateCounter") -> None:
        counter = utils.create_counter(0)
        assert isinstance(counter(), int)

    #  Tests that create_counter returns a new instance of the counter function each time it is called
    def test_create_counter_returns_new_instance_each_time(self: "TestCreateCounter") -> None:
        counter1 = utils.create_counter(0)
        counter2 = utils.create_counter(0)
        assert counter1 != counter2

    #  Tests that the count variable is not accessed outside the counter function
    def test_count_variable_not_accessed_outside_function(self: "TestCreateCounter") -> None:
        counter = utils.create_counter(0)
        with pytest.raises(AttributeError):
            _ = counter.count  # type: ignore[attr-defined]
