from cuid2.utils import base36_encode, random_letter, string_to_int
from pytest import raises


def test_string_to_int() -> None:
    string_int: int = string_to_int('this is a test')
    expected: int = 2361031878030638688519054699098996

    assert string_int is not None  # noqa
    assert isinstance(string_int, int)  # noqa
    assert string_int == expected  # noqa


def test_base36_encode() -> None:
    encoded: str = base36_encode(1000)
    expected: str = 'rs'

    assert encoded is not None  # noqa
    assert isinstance(encoded, str)  # noqa
    assert encoded == expected  # noqa


def test_base36_raises() -> None:
    with raises(ValueError, match=r".* encode negative .*"):
        base36_encode(-1)


def test_random_letter() -> None:
    letter: str = random_letter()

    assert letter is not None  # noqa
    assert len(letter) == 1  # noqa
    assert isinstance(letter, str)  # noqa
