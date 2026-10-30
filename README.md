# cuid2

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://pypi.org/project/cuid2/)
[![PyPi](https://img.shields.io/pypi/v/cuid2.svg)](https://pypi.org/project/cuid2/)
[![PyPi](https://img.shields.io/pypi/dm/cuid2.svg)](https://pypi.org/project/cuid2/)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/gordon-code/cuid2/badge)](https://scorecard.dev/viewer/?uri=github.com/gordon-code/cuid2)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/16036/badge)](https://www.bestpractices.dev/projects/16036)

CUID2 for Python 3. Next generation GUIDs. Collision-resistant ids optimized for
horizontal scaling and performance.

A port of the [CUID2 reference implementation](https://github.com/paralleldrive/cuid2)
by [Parallel Drive](https://github.com/paralleldrive) to Python 3.

> :memo: Note: Originally taken from <https://github.com/overflowdigital> before it
> was unpublished. Thank you to @joshuathompsonlindley for your original contribution!

## What is CUID2?

* Secure: It's not feasible to guess the next ID (unguessability derives from the `secrets.SystemRandom` CSPRNG salt; per [RFC 9562 §8](https://www.rfc-editor.org/rfc/rfc9562.html#section-8), IDs are identifiers, not capability tokens or secrets).
* Collision resistant: It's extremely unlikely to generate the same ID twice.
* Horizontally scalable: Generate IDs on multiple machines without coordination.
* Offline-compatible: Generate IDs without a network connection.
* URL and name-friendly: No special characters.

## Why?

For more information on the theory and usage of CUID2, see the
[following](https://github.com/paralleldrive/cuid2#why).

## Improvements Over CUID

For more information on the improvements of CUID2 over CUID, see the
[following](https://github.com/paralleldrive/cuid2#improvements-over-cuid).

## When to Use CUID2

* **Zero Timestamp or Creation-Rate Leakage**: Time-ordered formats (`uuid.uuid7()` in Python 3.14, PostgreSQL 18 `uuidv7()`, ULID) embed a 48-bit millisecond timestamp in their prefix, allowing anyone with a public ID to read exact creation times and infer business volume or request velocity ([RFC 9562 §8](https://www.rfc-editor.org/rfc/rfc9562.html#section-8)). CUID2 hashes nanosecond time, CSPRNG salt, a monotonic counter, and a host fingerprint through **SHA3-512**, revealing nothing about when or where an ID was generated.
* **HTML, CSS, and Lexical Safety (`[a-z][0-9a-z]+`)**: Every CUID2 is guaranteed to start with a lowercase ASCII letter (`[a-z]`) and contain only `[0-9a-z]`. By contrast, time-ordered **UUIDv7** (`019...`) starts with `0` until the year 2527 (and `0–9` until year 7541), **ULID** always starts with a timestamp digit (`0–7`), **UUIDv4** starts with a numeric digit (`0–9`) 62.5% of the time (`10/16` hex values), and **NanoID** starts with `0–9`, `_`, or `-` 18.75% of the time (`12/64` alphabet chars). CUID2 IDs are always valid unescaped HTML `id` attributes and CSS selectors, and copy cleanly with a single double-click.
* **Collision Resistance & Entropy Math**:
  * **123.6-Bit Default Keyspace (`length=24`)**: 1 leading lowercase letter ($26$) followed by 23 base36 characters ($36^{23}$) yields $26 \times 36^{23} \approx \mathbf{1.61 \times 10^{37}}$ possible IDs ($\approx \mathbf{123.6\text{ bits}}$ of entropy)—slightly more than UUIDv4's 122 random bits in a 33% shorter string (24 vs. 36 chars). Reaching a 50% birthday-bound collision probability requires $\sqrt{2 \ln(2) \times 26 \times 36^{23}} \approx \mathbf{4.7 \times 10^{18}}$ IDs (generating **149 million IDs/sec continuously for 1,000 years**).
  * **Up to 165.0 Bits (`BIG_LENGTH = 32`)**: At `length=32`, the keyspace expands to $26 \times 36^{31} \approx \mathbf{4.54 \times 10^{49}}$ IDs ($\approx \mathbf{165.0\text{ bits}}$; 50% collision bound at $\approx 7.9 \times 10^{24}$ IDs).
  * **Histogram De-Biasing**: Because $2^{512} \approx 1.34 \times 10^{154}$ is not an exact power of 36, the most-significant base36 digit of a 512-bit SHA3-512 digest is biased toward low digits; CUID2 drops that leading hash character (`[1:]`) and prepends an independent uniform `[a-z]` letter so every character position has a uniform distribution.
* **Thread, Pre-Fork, & Container Snapshot Resilience**: `Cuid`, `create_id`, `cuid_wrapper`, and `create_counter` are thread-safe (including on free-threaded Python, tested on `3.14t` and `3.15t`). Each generator records the process ID (`os.getpid()`) that built its state; the first ID generated in a forked child process (`multiprocessing`, Gunicorn, Celery prefork, and uWSGI workers, including uWSGI's default mode, which skips Python's `os.register_at_fork` hooks) rebuilds that state with a fresh lock, RNG state, random initial counter (`INITIAL_COUNT_MAX = 476,782,367`, giving $\approx 25,700$ concurrent hosts before a 50% chance of two hosts starting at the same counter value), and child-PID fingerprints (`os.getpid()`, `socket.gethostname()`, and environment variable keys). For cloned VM/container snapshots where no `fork()` syscall occurs, per-call `secrets.SystemRandom` (`os.urandom`) salt and `time.time_ns()` provide defense-in-depth against state collisions.
* **Polyglot ORM Compatibility (Prisma & Drizzle)**: Generates 24-character base36 primary keys compatible with TypeScript/Node.js services using Prisma (`@default(cuid(2))` / `@onCreate(cuid(2))`) or Drizzle (`@paralleldrive/cuid2`), and replaces the deprecated CUIDv1 (`cuid`) format.

| Property | CUID2 (`cuid2`) | UUIDv7 (`uuid.uuid7`) | UUIDv4 (`uuid.uuid4`) | ULID (`python-ulid`) | NanoID (`nanoid`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Default Length** | **24 chars** (`2..32`) | 36 chars | 36 chars | 26 chars | 21 chars |
| **Alphabet** | `[a-z0-9]` (base36) | `[0-9a-f-]` (hex) | `[0-9a-f-]` (hex) | Crockford Base32 | `[A-Za-z0-9_-]` (url64) |
| **Starts with Letter?** | **Yes (100% `[a-z]`)** | **No** (`0` until yr 2527) | Not guaranteed (37.5% `a–f`) | **No** (always `0–7`) | Not guaranteed (81.25%) |
| **Double-Click Copyable?** | **Yes** | No (hyphens) | No (hyphens) | **Yes** | No (`-` breaks word) |
| **Entropy / Random Bits** | **~123.6 bits** (`165.0` at 32) | 74 bits / ms | 122 bits | 80 bits / ms | 126 bits |
| **50% Collision Bound** | **~4.7 × 10¹⁸** (`~7.9 × 10²⁴` at 32) | ~1.6 × 10¹¹ / ms | ~2.7 × 10¹⁸ | ~1.3 × 10¹² / ms | ~1.1 × 10¹⁹ |
| **Hides Creation Timestamp?** | **Yes (SHA3-512)** | No (leaks 48-bit ms) | **Yes** | No (leaks 48-bit ms) | **Yes** |
| **Fork / Snapshot Safe?** | **Yes (per-PID state + CSPRNG)** | Counter can collide | OS CSPRNG only | Counter can collide | OS CSPRNG only |
| **B-Tree Index Locality** | Low (uniform hash) | **High (time-ordered)** | Low (uniform random) | **High (time-ordered)** | Low (uniform random) |

> **When to choose UUIDv7 instead:** Because CUID2 hashes its inputs via SHA3-512, IDs are uniformly distributed across the key space. For write-heavy relational tables where B-tree insert locality and 16-byte binary `UUID` storage matter more than hiding creation timestamps, prefer Python 3.14's `uuid.uuid7()` or PostgreSQL 18's `uuidv7()`.

## Install

```bash
pip install cuid2
```

## Usage

For most use cases—including Django, SQLAlchemy, and Pydantic model defaults—use the top-level `create_id` and `is_cuid` functions directly:

```python
from cuid2 import create_id, is_cuid

my_cuid: str = create_id()
short_cuid: str = create_id(length=10)

print(is_cuid(my_cuid))  # True
```

> **Tip for Django & ORM defaults:** Pass `default=create_id` directly on model fields (e.g., `models.CharField(max_length=24, default=create_id)`). Because `create_id` is a top-level function backed by a lazy singleton generator, Django `makemigrations` can serialize it directly and `Cuid()` initialization is deferred until the first ID is generated in each worker process.

You can also generate and validate CUIDs directly in the terminal:

```bash
cuid2                        # Generate a 24-character CUID2
cuid2 -l 10                  # Generate a 10-character CUID2 (or positional: cuid2 10)
cuid2 --slug                 # Generate a 5-character short ID slug
cuid2 -n 5                   # Generate 5 CUID2s in a batch
cuid2 -f server-1            # Use "server-1" verbatim as the fingerprint (IDs stay random)
cuid2 --check <id>           # Validate an ID (prints "<id>: valid" or "<id>: invalid"; -q for exit code only)
cuid2 -n 5 | cuid2 --check - # Validate newline-delimited IDs from stdin (blank lines are skipped)
python -m cuid2              # Run via module execution
```

If a framework, dataclass, or Django migration requires a zero-argument callable with a custom length, use `cuid_wrapper` (which returns `functools.partial(create_id, length=10)` directly, making it picklable for `multiprocessing` and serializable by Django `makemigrations`):

```python
from collections.abc import Callable

from cuid2 import cuid_wrapper

short_cuid_generator: Callable[[], str] = cuid_wrapper(length=10)


def main() -> None:
    short_cuid: str = short_cuid_generator()
```

Finally, for more explicit control of the CUID generator, you can instantiate the class directly:

```python
from cuid2 import Cuid

CUID_GENERATOR: Cuid = Cuid(length=10)


def main() -> None:
    my_cuid: str = CUID_GENERATOR.generate()
    next_cuid: str = CUID_GENERATOR.generate()

    # Validate CUID
    print(Cuid.is_cuid(my_cuid))  # True
```

`is_cuid` (and `Cuid.is_cuid`) also accepts optional `min_length` and `max_length` arguments to tighten the allowed length.
The bounds are clamped to 2 and 98 characters, so they can narrow but never widen what is considered valid.

## Changelog

See [CHANGELOG.md](https://github.com/gordon-code/cuid2/blob/main/CHANGELOG.md) for release history.
