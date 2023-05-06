from cuid2 import cuid


def test_cuid_generation() -> None:
    generated_cuid: str = cuid()
    default_length: int = 24

    assert generated_cuid is not None  # noqa
    assert len(generated_cuid) == default_length  # noqa
    assert isinstance(generated_cuid, str)  # noqa


def test_cuid_generation_custom_length() -> None:
    generated_cuid: str = cuid(10)
    default_length: int = 24

    assert generated_cuid is not None  # noqa
    assert len(generated_cuid) != default_length  # noqa
    assert len(generated_cuid) == 10  # noqa
    assert isinstance(generated_cuid, str)  # noqa


def test_cuid_generation_custom_long_length() -> None:
    generated_cuid: str = cuid(32)
    default_length: int = 24

    assert generated_cuid is not None  # noqa
    assert len(generated_cuid) != default_length  # noqa
    assert len(generated_cuid) == 32  # noqa
    assert isinstance(generated_cuid, str)  # noqa
