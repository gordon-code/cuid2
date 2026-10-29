from __future__ import annotations

import os
from collections import Counter
from math import ceil, floor
from multiprocessing import Pool
from typing import TYPE_CHECKING, Any

import pytest

from cuid2 import Cuid
from cuid2.utils import BASE36_RADIX, DEFAULT_LENGTH

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

_NUM_BUCKETS: int = 256
_ID_BYTES: int = 16
_HISTOGRAM_BINS: int = 20
_TAIL_SPACE: int = BASE36_RADIX ** (DEFAULT_LENGTH - 1)
_BUCKET_LENGTH: int = ceil(_TAIL_SPACE / _HISTOGRAM_BINS)


def cuid_generator(max_ids: int) -> dict[str, Any]:
    """Generate a specified number of unique IDs using the CUID library and return a dictionary containing
    information about the generated IDs.

    Parameters
    ----------
    max_ids : int
        The maximum number of unique IDs to generate.

    Returns
    -------
    dict[str, Any]
        Dictionary containing 256-bucket 16-byte ID buffers (``id_buckets``) alongside
        ``id_histogram`` and ``char_histogram``.
    """
    cuid: Callable[[], str] = Cuid().generate
    id_buckets: list[bytearray] = [bytearray() for _ in range(_NUM_BUCKETS)]
    id_histogram: Counter[int] = Counter()
    char_histogram: Counter[str] = Counter()

    for _ in range(max_ids):
        uid: str = cuid()
        full_int: int = int(uid, BASE36_RADIX)
        id_buckets[full_int & 0xFF].extend(full_int.to_bytes(_ID_BYTES, "big"))
        id_histogram[(full_int % _TAIL_SPACE) // _BUCKET_LENGTH] += 1
        char_histogram.update(uid[1:])

    return {
        "id_buckets": id_buckets,
        "id_histogram": id_histogram,
        "char_histogram": char_histogram,
    }


def is_histogram_evenly_distributed(
    histogram_values: Iterable[int],
    expected_bin_size: int,
    tolerance: float = 0.04,
) -> bool:
    """Check if the values in a histogram are evenly distributed within a certain tolerance range.

    Parameters
    ----------
    histogram_values : Iterable[int]
        An iterable of integers representing the counts of items in each bin of a histogram.
    expected_bin_size : int
        The expected size of each bin in the histogram.
    tolerance : float
        The tolerance parameter is a float value that determines the acceptable range of deviation from the expected
        bin size. It is used to determine whether the histogram is evenly distributed or not. If the difference
        between the actual bin size and the expected bin size is within the tolerance range,
        the histogram is considered to be evenly distributed.

    Returns
    -------
    bool
        indicates whether the histogram values are evenly distributed within a certain tolerance range.
    """
    min_bin_size: int = floor(expected_bin_size * (1 - tolerance))
    max_bin_size: int = ceil(expected_bin_size * (1 + tolerance))
    return all(min_bin_size < count < max_bin_size for count in histogram_values)


@pytest.mark.parametrize(
    ("num_ids", "num_pools"),
    [
        pytest.param(1_000_000, 1, marks=pytest.mark.slow),
        pytest.param(100_000, 10, marks=pytest.mark.slow),
        pytest.param(10_000, 100, marks=pytest.mark.slow),
        pytest.param(10_000_000, 10, marks=pytest.mark.heavy),
        pytest.param(1_000_000, 100, marks=pytest.mark.heavy),
    ],
)
def test_collisions(num_ids: int, num_pools: int) -> None:
    """Test for collisions, character representation, even character frequency, and histogram distribution
    tolerance in a CUID generator.

    Parameters
    ----------
    num_ids : int
        The number of unique IDs to generate in each pool task.
    num_pools : int
        The number of independent generator tasks to dispatch across the worker pool (capped at os.cpu_count()).
    """
    total_num_ids: int = num_ids * num_pools
    effective_pools: int = min(num_pools, os.cpu_count() or 1)
    with Pool(effective_pools) as pool:
        result = pool.map(cuid_generator, (num_ids,) * num_pools)

    # should: generate no collisions
    assert (
        sum(
            len(
                {
                    bytes(bucket[i : i + _ID_BYTES])
                    for r in result
                    for bucket in (r["id_buckets"][b],)
                    for i in range(0, len(bucket), _ID_BYTES)
                }
            )
            for b in range(_NUM_BUCKETS)
        )
        == total_num_ids
    )

    # should: represent all 36 character values
    for r in result:
        assert len(r["char_histogram"]) == BASE36_RADIX

    # should: produce even character frequency
    sum_char_histograms: Counter[str] = Counter()
    for r in result:
        sum_char_histograms.update(r["char_histogram"])
    expected_char_bin_size: int = ceil(((DEFAULT_LENGTH - 1) * total_num_ids) / BASE36_RADIX)
    assert is_histogram_evenly_distributed(sum_char_histograms.values(), expected_char_bin_size)

    # should: produce a histogram with even distribution tolerance
    sum_id_histograms: Counter[int] = Counter()
    for r in result:
        sum_id_histograms.update(r["id_histogram"])
    assert len(sum_id_histograms) == _HISTOGRAM_BINS
    expected_id_bin_size: int = ceil(total_num_ids / _HISTOGRAM_BINS)
    assert is_histogram_evenly_distributed(sum_id_histograms.values(), expected_id_bin_size)
