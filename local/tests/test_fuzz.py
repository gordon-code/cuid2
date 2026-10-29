from __future__ import annotations

import random
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cuid2 import BIG_LENGTH, INITIAL_COUNT_MAX, MAXIMUM_LENGTH, MIN_LENGTH, Cuid, create_id, is_cuid, utils
from cuid2.utils import ASCII_LOWERCASE, BASE36_ALPHABET
from local.verify_release import (
    DEFAULT_REPO_URL,
    expected_sdist_members,
    expected_wheel_members,
    read_project_version,
    verify_and_extract_release_notes,
)

if TYPE_CHECKING:

    class _HypothesisAttr(Protocol):
        def fuzz_one_input(self, data: bytes, /) -> bytes | None: ...

    class _FuzzTarget(Protocol):
        hypothesis: _HypothesisAttr


@settings(derandomize=True, database=None, deadline=None, max_examples=100)
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


@settings(derandomize=True, database=None, deadline=None, max_examples=100)
@given(candidate=st.from_regex(r"\A[a-z][0-9a-z]{1,97}\Z", fullmatch=True))
def test_fuzz_is_cuid_valid_regex(candidate: str) -> None:
    assert is_cuid(candidate) is True
    assert is_cuid(candidate, min_length=len(candidate), max_length=len(candidate)) is True


@settings(derandomize=True, database=None, deadline=None, max_examples=100)
@given(number=st.integers(min_value=0, max_value=(1 << 512) - 1))
def test_fuzz_base36_encode_round_trip(number: int) -> None:
    encoded: str = utils.base36_encode(number)
    assert len(encoded) >= 1
    assert all(ch in BASE36_ALPHABET for ch in encoded)
    if number > 0:
        assert not encoded.startswith("0")
    assert int(encoded, 36) == number


@settings(derandomize=True, database=None, deadline=None, max_examples=100)
@given(number=st.integers(max_value=-1))
def test_fuzz_base36_encode_negative_raises(number: int) -> None:
    with pytest.raises(ValueError, match=r"Cannot encode negative integers\."):
        utils.base36_encode(number)


@settings(derandomize=True, database=None, deadline=None, max_examples=100)
@given(
    seed=st.integers(0, (1 << 64) - 1),
    entropy_len=st.integers(1, 64),
    data=st.text(max_size=200),
    initial_count=st.integers(-10_000, INITIAL_COUNT_MAX),
)
def test_fuzz_utils_primitives(seed: int, entropy_len: int, data: str, initial_count: int) -> None:
    rng = random.Random(seed)  # noqa: S311
    letter: str = utils.create_letter(rng)
    assert len(letter) == 1
    assert letter in ASCII_LOWERCASE

    entropy: str = utils.create_entropy(rng, entropy_len)
    assert len(entropy) == entropy_len
    assert all(ch in BASE36_ALPHABET for ch in entropy)

    digest: str = utils.create_hash(data)
    assert 1 <= len(digest) <= MAXIMUM_LENGTH + 1
    assert all(ch in BASE36_ALPHABET for ch in digest)

    fingerprint: str = utils.create_fingerprint(rng, data)
    assert len(fingerprint) == BIG_LENGTH
    assert all(ch in BASE36_ALPHABET for ch in fingerprint)

    counter = utils.create_counter(initial_count)
    assert counter() == initial_count + 1
    assert counter() == initial_count + 2


@settings(derandomize=True, database=None, deadline=None, max_examples=100)
@given(
    seed=st.integers(0, (1 << 64) - 1),
    length=st.integers(MIN_LENGTH, BIG_LENGTH),
)
def test_fuzz_cuid_spec_lengths(seed: int, length: int) -> None:
    cuid = Cuid(random_generator=lambda: random.Random(seed), length=length)  # noqa: S311
    uid_instance: str = cuid.generate()
    assert len(uid_instance) == length
    assert is_cuid(uid_instance, min_length=length, max_length=length) is True

    uid_default: str = create_id(length=length)
    assert len(uid_default) == length
    assert is_cuid(uid_default, min_length=length, max_length=length) is True


@settings(derandomize=True, database=None, deadline=None, max_examples=100)
@given(
    deprecated_length=st.one_of(st.just(1), st.integers(BIG_LENGTH + 1, MAXIMUM_LENGTH)),
    invalid_length=st.one_of(st.integers(max_value=0), st.integers(min_value=MAXIMUM_LENGTH + 1, max_value=500)),
)
def test_fuzz_cuid_deprecated_and_invalid_lengths(deprecated_length: int, invalid_length: int) -> None:
    with pytest.warns(DeprecationWarning, match=r"outside the CUID2 specification range"):
        uid: str = create_id(length=deprecated_length)
    assert 1 <= len(uid) <= deprecated_length

    with pytest.raises(ValueError, match=r"Length must (be at least 1 character|never exceed 98 characters)\."):
        Cuid(length=invalid_length)
    with pytest.raises(ValueError, match=r"Length must (be at least 1 character|never exceed 98 characters)\."):
        create_id(length=invalid_length)


@settings(derandomize=True, database=None, deadline=None, max_examples=25)
@given(
    major=st.integers(0, 20),
    minor=st.integers(0, 50),
    patch=st.integers(0, 100),
    bullet=st.from_regex(r"\A[A-Za-z0-9](?:[A-Za-z0-9 .,_-]{0,58}[A-Za-z0-9.,_-])?\Z", fullmatch=True),
)
def test_fuzz_verify_release(major: int, minor: int, patch: int, bullet: str) -> None:
    version: str = f"{major}.{minor}.{patch}"
    wheel_members: set[str] = expected_wheel_members(version)
    sdist_members: set[str] = expected_sdist_members(version)
    assert f"cuid2-{version}.dist-info/METADATA" in wheel_members
    assert f"cuid2-{version}/PKG-INFO" in sdist_members

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        pyproject_path = tmp_dir / "pyproject.toml"
        pyproject_path.write_text(f'[project]\nname = "cuid2"\nversion = "{version}"\n', encoding="utf-8")
        assert read_project_version(pyproject_path) == version

        invalid_pyproject_path = tmp_dir / "invalid_pyproject.toml"
        invalid_pyproject_path.write_text(f'[project]\nname = "cuid2"\nversion = "v{version}"\n', encoding="utf-8")
        with pytest.raises(ValueError, match=r"Invalid version"):
            read_project_version(invalid_pyproject_path)

        changelog_path = tmp_dir / "CHANGELOG.md"
        changelog_text = (
            "# Changelog\n\n"
            "## [Unreleased]\n\n"
            f"## [{version}] - 2026-10-28\n\n"
            "### Changed\n\n"
            f"- {bullet}\n\n"
            f"[Unreleased]: {DEFAULT_REPO_URL}/compare/v{version}...HEAD\n"
            f"[{version}]: {DEFAULT_REPO_URL}/releases/tag/v{version}\n"
        )
        changelog_path.write_text(changelog_text, encoding="utf-8")
        extracted: str = verify_and_extract_release_notes(changelog_path, version=version)
        assert extracted == f"### Changed\n\n- {bullet}\n"

        with pytest.raises(ValueError, match=r"Expected '## \[Unreleased\]'"):
            verify_and_extract_release_notes(changelog_path, version=f"{major + 1}.{minor}.{patch}")


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
        test_fuzz_verify_release,
    ),
)


def _dispatch_fuzz_one_input(data: bytes) -> None:
    if not data:
        return
    target: _FuzzTarget = _FUZZ_TARGETS[data[0] % len(_FUZZ_TARGETS)]
    target.hypothesis.fuzz_one_input(data[1:])


def test_dispatch_fuzz_one_input_smoke() -> None:
    _dispatch_fuzz_one_input(b"")
    for idx in range(len(_FUZZ_TARGETS)):
        _dispatch_fuzz_one_input(bytes([idx]) + b"\x00" * 16)


if __name__ == "__main__":
    import sys

    import atheris  # pyright: ignore[reportMissingImports, reportMissingModuleSource]

    atheris.Setup(sys.argv, _dispatch_fuzz_one_input)
    atheris.Fuzz()
