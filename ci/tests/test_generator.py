from cuid2.generator import (generate_entropy, generate_fingerprint,
                             generate_hash)

from tests import is_base36


def test_generate_entropy() -> None:
    entropy: str = generate_entropy()

    assert entropy is not None  # noqa
    assert isinstance(entropy, str)  # noqa
    assert is_base36(entropy)  # noqa


def test_generate_entropy_custom_long_length() -> None:
    entropy: str = generate_entropy(32)

    assert entropy is not None  # noqa
    assert isinstance(entropy, str)  # noqa
    assert is_base36(entropy)  # noqa


def test_generate_hash() -> None:
    hash: str = generate_hash('this is a test')

    assert hash is not None  # noqa
    assert isinstance(hash, str)  # noqa
    assert is_base36(hash)  # noqa


def test_generate_fingerprint() -> None:
    fingerprint: str = generate_fingerprint()

    assert fingerprint is not None  # noqa
    assert isinstance(fingerprint, str)  # noqa
    assert is_base36(fingerprint)  # noqa
