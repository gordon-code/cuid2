from __future__ import annotations

import random
from typing import TYPE_CHECKING, Protocol, cast
from unittest.mock import Mock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cuid2 import Cuid, create_id, cuid_wrapper, is_cuid, utils
from cuid2.utils import (
    ASCII_LOWERCASE,
    BASE36_ALPHABET,
    BASE36_RADIX,
    BIG_LENGTH,
    INITIAL_COUNT_MAX,
    MAXIMUM_LENGTH,
    MIN_LENGTH,
)

if TYPE_CHECKING:

    class _HypothesisAttr(Protocol):
        def fuzz_one_input(self, data: bytes, /) -> bytes | None: ...

    class _FuzzTarget(Protocol):
        hypothesis: _HypothesisAttr


@given(
    candidate=st.text(max_size=150),
    min_length=st.integers(-50, 150),
    max_length=st.integers(-50, 150),
)
def test_fuzz_is_cuid_arbitrary_strings(candidate: str, min_length: int, max_length: int) -> None:
    expected: bool = (
        len(candidate) >= MIN_LENGTH
        and min_length <= len(candidate) <= min(max_length, MAXIMUM_LENGTH)
        and candidate[0] in ASCII_LOWERCASE
        and all(ch in BASE36_ALPHABET for ch in candidate[1:])
    )
    assert is_cuid(candidate, min_length=min_length, max_length=max_length) is expected


@given(candidate=st.from_regex(r"\A[a-z][0-9a-z]{1,97}\Z", fullmatch=True))
def test_fuzz_is_cuid_valid_regex(candidate: str) -> None:
    assert is_cuid(candidate) is True
    assert is_cuid(candidate, min_length=len(candidate), max_length=len(candidate)) is True


@given(number=st.integers(min_value=0, max_value=(1 << 512) - 1))
def test_fuzz_base36_encode_round_trip(number: int) -> None:
    encoded: str = utils.base36_encode(number)
    assert len(encoded) >= 1
    assert all(ch in BASE36_ALPHABET for ch in encoded)
    if number > 0:
        assert not encoded.startswith("0")
    assert int(encoded, BASE36_RADIX) == number


@given(number=st.integers(max_value=-1))
def test_fuzz_base36_encode_negative_raises(number: int) -> None:
    with pytest.raises(ValueError, match=r"Cannot encode negative integers\."):
        utils.base36_encode(number)


@given(
    seed=st.integers(0, (1 << 64) - 1),
    entropy_len=st.integers(1, 64),
    invalid_entropy_len=st.integers(max_value=0),
    data=st.text(max_size=200),
    initial_count=st.integers(-10_000, INITIAL_COUNT_MAX),
)
def test_fuzz_utils_primitives(
    seed: int,
    entropy_len: int,
    invalid_entropy_len: int,
    data: str,
    initial_count: int,
) -> None:
    rng = random.Random(seed)  # noqa: S311
    letter: str = utils.create_letter(rng)
    assert len(letter) == 1
    assert letter in ASCII_LOWERCASE

    entropy: str = utils.create_entropy(rng, entropy_len)
    assert len(entropy) == entropy_len
    assert all(ch in BASE36_ALPHABET for ch in entropy)

    with pytest.raises(ValueError, match=r"Cannot create entropy without a length >= 1\."):
        utils.create_entropy(rng, invalid_entropy_len)

    digest: str = utils.create_hash(data)
    assert 1 <= len(digest) <= MAXIMUM_LENGTH + 1
    assert all(ch in BASE36_ALPHABET for ch in digest)

    fingerprint: str = utils.create_fingerprint(rng, data)
    assert len(fingerprint) == BIG_LENGTH
    assert all(ch in BASE36_ALPHABET for ch in fingerprint)

    counter = utils.create_counter(initial_count)
    assert counter() == initial_count + 1
    assert counter() == initial_count + 2


@given(
    seed=st.integers(0, (1 << 64) - 1),
    length=st.integers(MIN_LENGTH, BIG_LENGTH),
)
def test_fuzz_cuid_spec_lengths(seed: int, length: int) -> None:
    cuid = Cuid(random_generator=lambda: random.Random(seed), length=length)  # noqa: S311
    uid_instance: str = cuid.generate()
    assert len(uid_instance) == length
    assert is_cuid(uid_instance, min_length=length, max_length=length) is True

    uid_override: str = Cuid().generate(length=length)
    assert len(uid_override) == length
    assert is_cuid(uid_override, min_length=length, max_length=length) is True

    uid_default: str = create_id(length=length)
    assert len(uid_default) == length
    assert is_cuid(uid_default, min_length=length, max_length=length) is True

    wrapper = cuid_wrapper(length=length)
    uid_wrapped: str = wrapper()
    assert len(uid_wrapped) == length
    assert is_cuid(uid_wrapped, min_length=length, max_length=length) is True


@given(
    deprecated_length=st.one_of(st.just(1), st.integers(BIG_LENGTH + 1, MAXIMUM_LENGTH)),
    invalid_length=st.one_of(
        st.booleans(),
        st.integers(max_value=0),
        st.integers(min_value=MAXIMUM_LENGTH + 1, max_value=500),
    ),
)
def test_fuzz_cuid_deprecated_and_invalid_lengths(deprecated_length: int, invalid_length: int) -> None:
    with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range"):
        uid: str = create_id(length=deprecated_length)
    assert 1 <= len(uid) <= deprecated_length

    cuid = Cuid()
    with pytest.raises(ValueError, match=r"Length must (be at least 1 character|never exceed 98 characters)\."):
        Cuid(length=invalid_length)
    with pytest.raises(ValueError, match=r"Length must (be at least 1 character|never exceed 98 characters)\."):
        cuid.generate(length=invalid_length)
    with pytest.raises(ValueError, match=r"Length must (be at least 1 character|never exceed 98 characters)\."):
        create_id(length=invalid_length)
    with pytest.raises(ValueError, match=r"Length must (be at least 1 character|never exceed 98 characters)\."):
        cuid_wrapper(length=invalid_length)


@given(
    digest_int=st.integers(min_value=0, max_value=(1 << 512) - 1),
    length=st.integers(min_value=1, max_value=MAXIMUM_LENGTH),
)
def test_fuzz_create_hash_slice_arbitrary_digest(digest_int: int, length: int) -> None:
    mock_hash = Mock()
    mock_hash.digest.return_value = digest_int.to_bytes(64, byteorder="big")
    with patch.object(utils, "sha3_512", return_value=mock_hash):
        full_hash = utils.create_hash("fuzz")
        assert utils._create_hash_slice("fuzz", 1, length) == full_hash[1:length]
        assert utils._create_hash_slice("fuzz", 0, BIG_LENGTH) == full_hash[:BIG_LENGTH]


@given(
    data=st.text(max_size=200),
    length=st.integers(min_value=1, max_value=MAXIMUM_LENGTH),
)
def test_fuzz_create_hash_slice_and_scale_randbits(data: str, length: int) -> None:
    assert utils._create_hash_slice(data, 1, length) == utils.create_hash(data)[1:length]

    modulus = BASE36_RADIX**length
    draw_bits = modulus.bit_length() + 64
    high_bits = draw_bits - 64
    x_high = len(data) & ((1 << high_bits) - 1)
    low_zero = utils._scale_randbits(x_high << 64, modulus, draw_bits)
    low_ones = utils._scale_randbits((x_high << 64) | ((1 << 64) - 1), modulus, draw_bits)
    assert 0 <= low_ones - low_zero <= 1


_FUZZ_TARGETS: tuple[_FuzzTarget, ...] = cast(
    "tuple[_FuzzTarget, ...]",
    (
        test_fuzz_is_cuid_arbitrary_strings,
        test_fuzz_is_cuid_valid_regex,
        test_fuzz_base36_encode_round_trip,
        test_fuzz_base36_encode_negative_raises,
        test_fuzz_utils_primitives,
        test_fuzz_cuid_spec_lengths,
        test_fuzz_cuid_deprecated_and_invalid_lengths,
        test_fuzz_create_hash_slice_arbitrary_digest,
        test_fuzz_create_hash_slice_and_scale_randbits,
    ),
)


def _dispatch_fuzz_one_input(data: bytes) -> None:
    if not data:
        return
    target: _FuzzTarget = _FUZZ_TARGETS[data[0] % len(_FUZZ_TARGETS)]
    target.hypothesis.fuzz_one_input(data[1:])


if __name__ == "__main__":
    import sys

    import atheris  # pyright: ignore[reportMissingImports, reportMissingModuleSource]

    atheris.Setup(sys.argv, _dispatch_fuzz_one_input)
    atheris.Fuzz()
