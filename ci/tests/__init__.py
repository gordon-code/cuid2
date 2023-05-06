import string
from math import floor

from cuid2 import cuid


def is_base36(text: str) -> bool:
    alphabet: str = string.digits + string.ascii_lowercase
    return all(char in alphabet for char in text)


def create_id_pool(max: int = 100000) -> list[str]:
    id_pool: list[str] = []
    percent: int = -1

    for i in range(0, max):
        id_pool.append(cuid())

        if floor((i/max) * 100) != percent:
            percent = floor((i/max) * 100)
            print(f'ID Pool Generation {percent}% done')  # noqa

    return list(id_pool)
