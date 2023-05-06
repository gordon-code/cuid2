from tests import create_id_pool


def test_collision() -> None:
    magic: int = 500000
    id_pool: list[str] = create_id_pool(magic)
    id_set: set[str] = set(id_pool)

    assert len(id_set) == magic  # noqa
