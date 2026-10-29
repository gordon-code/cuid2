from __future__ import annotations

import os
from array import array
from collections import Counter
from math import ceil, floor
from multiprocessing import Pool
from typing import TYPE_CHECKING, Any

import pytest

from cuid2 import Cuid
from cuid2.utils import BASE36_ALPHABET, base36_encode
from local.tests.conftest import pytest_collection_modifyitems

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from unittest.mock import Mock

_NUM_BUCKETS: int = 256
_MASK64: int = (1 << 64) - 1


def cuid_generator(
    max_ids: int,
    id_fn: Callable[[], str] | None = None,
    hash64_fn: Callable[[str, int], int] | None = None,
) -> dict[str, Any]:
    """Generate unique IDs and bucketed 64-bit hash pairs for bounded-memory collision detection.

    Parameters
    ----------
    max_ids : int
        The number of IDs to generate in this worker batch.
    id_fn : Callable[[], str] | None
        Optional ID generator callable for deterministic unit testing.
    hash64_fn : Callable[[str, int], int] | None
        Optional 64-bit hash override callable for testing hash-collision disambiguation.

    Returns
    -------
    dict[str, Any]
        Dictionary containing 256-bucket ``array('Q')`` lists (``lo_buckets``, ``hi_buckets``,
        and optional ``lo_raw_buckets``) alongside ``id_histogram`` and ``char_histogram``.
    """
    str_base: int = 36
    cuid: Callable[[], str] = Cuid().generate if id_fn is None else id_fn
    bucket_count: int = 20

    lo_buckets: list[array[int]] = [array("Q") for _ in range(_NUM_BUCKETS)]
    hi_buckets: list[array[int]] = [array("Q") for _ in range(_NUM_BUCKETS)]
    lo_raw_buckets: list[array[int]] | None = (
        [array("Q") for _ in range(_NUM_BUCKETS)] if hash64_fn is not None else None
    )
    id_histogram: Counter[int] = Counter()
    char_histogram: Counter[str] = Counter()

    bucket_length: int = ceil(str_base**23 / bucket_count)

    for _ in range(max_ids):
        uid: str = cuid()
        full_int: int = int(uid, str_base)
        tail_int: int = int(uid[1:], str_base)
        id_histogram[tail_int // bucket_length] += 1
        char_histogram.update(uid[1:])

        lo_raw: int = full_int & _MASK64
        lo64: int = hash64_fn(uid, full_int) & _MASK64 if hash64_fn is not None else lo_raw
        hi64: int = full_int >> 64
        bucket_idx: int = lo64 >> 56

        lo_buckets[bucket_idx].append(lo64)
        hi_buckets[bucket_idx].append(hi64)
        if lo_raw_buckets is not None:
            lo_raw_buckets[bucket_idx].append(lo_raw)

    return {
        "lo_buckets": lo_buckets,
        "hi_buckets": hi_buckets,
        "lo_raw_buckets": lo_raw_buckets,
        "id_histogram": id_histogram,
        "char_histogram": char_histogram,
    }


def find_verified_collisions(worker_results: Sequence[dict[str, Any]]) -> set[str]:
    """Find and losslessly verify duplicate CUID strings across worker batches bucket-by-bucket.

    Parameters
    ----------
    worker_results : Sequence[dict[str, Any]]
        Sequence of dictionaries returned by ``cuid_generator``.

    Returns
    -------
    set[str]
        Set of genuinely duplicated CUID strings (empty if no duplicates occurred).
    """
    verified_collisions: set[str] = set()

    for bucket_idx in range(_NUM_BUCKETS):
        bucket_hashes: array[int] = array("Q")
        for r in worker_results:
            bucket_hashes.extend(r["lo_buckets"][bucket_idx])

        if len(bucket_hashes) < 2:
            continue

        sorted_hashes: list[int] = sorted(bucket_hashes)
        candidate_hashes: set[int] = {
            sorted_hashes[i] for i in range(1, len(sorted_hashes)) if sorted_hashes[i] == sorted_hashes[i - 1]
        }
        if not candidate_hashes:
            continue

        seen_ids: set[str] = set()
        for r in worker_results:
            lo_bucket: array[int] = r["lo_buckets"][bucket_idx]
            hi_bucket: array[int] = r["hi_buckets"][bucket_idx]
            lo_raw_bucket: array[int] = (
                r["lo_raw_buckets"][bucket_idx] if r["lo_raw_buckets"] is not None else lo_bucket
            )
            for lo64, lo_raw, hi64 in zip(lo_bucket, lo_raw_bucket, hi_bucket, strict=True):
                if lo64 in candidate_hashes:
                    reconstructed: str = base36_encode((hi64 << 64) | lo_raw)
                    if reconstructed in seen_ids:
                        verified_collisions.add(reconstructed)
                    else:
                        seen_ids.add(reconstructed)

    return verified_collisions


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


@pytest.mark.slow
@pytest.mark.parametrize(
    ("num_ids", "num_pools"),
    [
        (1_000_000, 1),  # 1M total IDs across 1 task (~20s on 1 worker)
        (100_000, 10),  # 1M total IDs across 10 tasks (~5s capped at os.cpu_count() workers)
        (10_000, 100),  # 1M total IDs across 100 tasks (~5s capped at os.cpu_count() workers)
        pytest.param(
            10_000_000,
            10,
            marks=pytest.mark.heavy,
        ),  # 100M total IDs across 10 tasks (~60m in CI; requires --run-heavy)
        pytest.param(
            1_000_000,
            100,
            marks=pytest.mark.heavy,
        ),  # 100M total IDs across 100 tasks (~60m in CI; requires --run-heavy)
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
        result = pool.map(cuid_generator, (total_num_ids // num_pools,) * num_pools)

    # should: generate no collisions
    assert find_verified_collisions(result) == set()

    # should: represent all 36 character values
    for r in result:
        assert len(r["char_histogram"].keys()) == 36

    # should: produce even character frequency
    sum_char_histograms: Counter[str] = sum((r["char_histogram"] for r in result), Counter())
    expected_char_bin_size: int = ceil((23 * total_num_ids) / 36)
    assert is_histogram_evenly_distributed(sum_char_histograms.values(), expected_char_bin_size)

    # should: produce a histogram with even distribution tolerance
    sum_id_histograms: Counter[int] = sum((r["id_histogram"] for r in result), Counter())
    expected_id_bin_size: int = ceil(total_num_ids / len(sum_id_histograms.keys()))
    assert is_histogram_evenly_distributed(sum_id_histograms.values(), expected_id_bin_size)


def _colliding_hash64(_uid: str, _full_int: int) -> int:
    return 0xDEAD_BEEF_CAFE_BABE


class TestCollisionHarness:
    def test_cuid_generator_and_no_collisions_small_batch(self: TestCollisionHarness) -> None:
        result = [cuid_generator(200), cuid_generator(200)]
        assert find_verified_collisions(result) == set()
        alphabet_set = set(BASE36_ALPHABET)
        for batch in result:
            assert batch["lo_raw_buckets"] is None
            assert set(batch["char_histogram"]).issubset(alphabet_set)
            assert sum(batch["char_histogram"].values()) == 23 * 200
            assert sum(batch["id_histogram"].values()) == 200

    def test_find_verified_collisions_detects_intra_and_cross_worker_duplicates(self: TestCollisionHarness) -> None:
        dup_id = "a" + "0" * 23
        other_id = "b" + "0" * 23
        third_id = "c" + "0" * 23

        intra_ids = iter([dup_id, other_id, dup_id])
        intra_batch = cuid_generator(3, id_fn=lambda: next(intra_ids))
        assert find_verified_collisions([intra_batch]) == {dup_id}

        worker1_ids = iter([dup_id, other_id])
        worker2_ids = iter([third_id, dup_id])
        batch1 = cuid_generator(2, id_fn=lambda: next(worker1_ids))
        batch2 = cuid_generator(2, id_fn=lambda: next(worker2_ids))
        assert find_verified_collisions([batch1, batch2]) == {dup_id}

    def test_find_verified_collisions_ignores_false_positive_64bit_hash_collision(self: TestCollisionHarness) -> None:
        id_a = "a" + "0" * 23
        id_b = "b" + "0" * 23

        distinct_ids = iter([id_a, id_b])
        distinct_batch = cuid_generator(2, id_fn=lambda: next(distinct_ids), hash64_fn=_colliding_hash64)
        assert distinct_batch["lo_raw_buckets"] is not None
        assert find_verified_collisions([distinct_batch]) == set()

        same_ids = iter([id_a, id_a])
        same_batch = cuid_generator(2, id_fn=lambda: next(same_ids), hash64_fn=_colliding_hash64)
        assert find_verified_collisions([same_batch]) == {id_a}

    def test_is_histogram_evenly_distributed_bounds(self: TestCollisionHarness) -> None:
        assert is_histogram_evenly_distributed([97, 100, 103], expected_bin_size=100, tolerance=0.04) is True
        assert is_histogram_evenly_distributed([96, 100], expected_bin_size=100, tolerance=0.04) is False
        assert is_histogram_evenly_distributed([100, 104], expected_bin_size=100, tolerance=0.04) is False
        assert is_histogram_evenly_distributed([90, 100], expected_bin_size=100, tolerance=0.04) is False
        assert is_histogram_evenly_distributed([100, 110], expected_bin_size=100, tolerance=0.04) is False

    def test_conftest_slow_and_heavy_marker_gating(self: TestCollisionHarness, mocker: Mock) -> None:
        def _make_item(keywords: set[str]) -> Mock:
            item: Mock = mocker.MagicMock()
            item.keywords = dict.fromkeys(keywords, True)
            return item

        def _make_config(*, runslow: bool, run_heavy: bool) -> Mock:
            config: Mock = mocker.MagicMock()
            options = {"--runslow": runslow, "--run-heavy": run_heavy}
            config.getoption.side_effect = lambda name: options[name]
            return config

        # 1. Neither --runslow nor --run-heavy set: skips both slow and heavy
        fast_item = _make_item(set())
        slow_item = _make_item({"slow"})
        heavy_item = _make_item({"slow", "heavy"})
        pytest_collection_modifyitems(_make_config(runslow=False, run_heavy=False), [fast_item, slow_item, heavy_item])
        fast_item.add_marker.assert_not_called()
        assert slow_item.add_marker.call_count == 1
        assert slow_item.add_marker.call_args.args[0].kwargs["reason"] == "need --runslow option to run"
        assert heavy_item.add_marker.call_count == 2

        # 2. Only --runslow set: runs slow, still skips heavy
        slow_only = _make_item({"slow"})
        heavy_when_slow = _make_item({"slow", "heavy"})
        pytest_collection_modifyitems(_make_config(runslow=True, run_heavy=False), [slow_only, heavy_when_slow])
        slow_only.add_marker.assert_not_called()
        assert heavy_when_slow.add_marker.call_count == 1
        assert heavy_when_slow.add_marker.call_args.args[0].kwargs["reason"] == "need --run-heavy option to run"

        # 3. Both --runslow and --run-heavy set: runs both slow and heavy
        slow_both = _make_item({"slow"})
        heavy_both = _make_item({"slow", "heavy"})
        pytest_collection_modifyitems(_make_config(runslow=True, run_heavy=True), [slow_both, heavy_both])
        slow_both.add_marker.assert_not_called()
        heavy_both.add_marker.assert_not_called()
