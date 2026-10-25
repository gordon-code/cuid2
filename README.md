# cuid2

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://pypi.org/project/cuid2/)
[![PyPi](https://img.shields.io/pypi/v/cuid2.svg)](https://pypi.org/project/cuid2/)
[![PyPi](https://img.shields.io/pypi/dm/cuid2.svg)](https://pypi.org/project/cuid2/)

CUID2 for Python 3. Next generation GUIDs. Collision-resistant ids optimized for 
horizontal scaling and performance.

A port of the [CUID2 reference implementation](https://github.com/paralleldrive/cuid2) 
by [Parallel Drive](https://github.com/paralleldrive) to Python 3.

> :memo: Note: Originally taken from https://github.com/overflowdigital before it 
> was unpublished. Thank you to @joshuathompsonlindley for your original contribution!

## What is CUID2?

* Secure: It's not possible to guess the next ID.
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
* **HTML, CSS, and Lexical Safety (`[a-z][0-9a-z]+`)**: Unlike UUIDs (hyphenated hex starting with `0-9a-f`), ULIDs (starting with `0-7`), or NanoIDs (containing `_` and `-`), every CUID2 starts with a lowercase ASCII letter and contains only `[0-9a-z]`. IDs are valid unescaped HTML `id` attributes and CSS selectors, and copy cleanly with a single double-click.
* **Pre-Fork & Container Snapshot Resilience**: Combining `os.getpid()`, `socket.gethostname()`, environment variable keys, `time.time_ns()`, a randomly initialized monotonic counter, and `secrets.SystemRandom` (`os.urandom`) provides defense-in-depth against PRNG or counter state collisions across forked worker processes (Gunicorn, uWSGI, Celery) and cloned VM/container snapshots.
* **Polyglot ORM Compatibility (Prisma & Drizzle)**: Generates 24-character base36 primary keys compatible with TypeScript/Node.js services using Prisma (`@default(cuid(2))` / `@onCreate(cuid(2))`) or Drizzle (`@paralleldrive/cuid2`), and replaces the deprecated CUIDv1 (`cuid`) format.

| Property | CUID2 (`cuid2`) | UUIDv7 (`uuid.uuid7`) | UUIDv4 (`uuid.uuid4`) | ULID (`python-ulid`) | NanoID (`nanoid`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Default Length** | **24 chars** (`2..32`) | 36 chars | 36 chars | 26 chars | 21 chars |
| **Alphabet** | `[a-z0-9]` (base36) | `[0-9a-f-]` | `[0-9a-f-]` | Crockford Base32 | `[A-Za-z0-9_-]` |
| **Starts with Letter (`[a-z]`)?** | **Yes (HTML/CSS safe)** | No | No | No (`0-7`) | Not guaranteed |
| **Double-Click Copyable?** | **Yes** | No (hyphens) | No (hyphens) | **Yes** | No (`-` breaks word) |
| **Hides Creation Timestamp?** | **Yes (SHA3-512)** | No (leaks 48-bit ms) | **Yes** | No (leaks 48-bit ms) | **Yes** |
| **Fork / Snapshot Safe?** | **Yes (PID + host + CSPRNG)** | Counter can collide | OS CSPRNG only | Counter can collide | OS CSPRNG only |
| **B-Tree Index Locality** | Low (uniform hash) | **High (time-ordered)** | Low (uniform random) | **High (time-ordered)** | Low (uniform random) |

> **When to choose UUIDv7 instead:** Because CUID2 hashes its inputs via SHA3-512, IDs are uniformly distributed across the key space. For write-heavy relational tables where B-tree insert locality and 16-byte binary `UUID` storage matter more than hiding creation timestamps, prefer Python 3.14's `uuid.uuid7()` or PostgreSQL 18's `uuidv7()`.

## Install
```
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

You can also generate CUIDs directly in the terminal (optionally specifying a custom length):
```bash
$ cuid2
$ cuid2 10
```

If a framework, dataclass, or Django migration requires a zero-argument callable with a custom length, use `functools.partial` with `create_id`:
```python
from functools import partial
from typing import Callable
from cuid2 import create_id

short_cuid_generator: Callable[[], str] = partial(create_id, length=10)


def main():
    short_cuid: str = short_cuid_generator()
```

> **Note:** `cuid_wrapper()` is deprecated as of `v2.1.0` and will be removed in `v3.0.0`. Use `create_id` directly for default 24-character IDs or `functools.partial(create_id, length=...)` for pre-configured custom lengths.

Finally, for more explicit control of the CUID generator, you can instantiate the class directly:
```python
from cuid2 import Cuid

CUID_GENERATOR: Cuid = Cuid(length=10)


def main():
    my_cuid: str = CUID_GENERATOR.generate()
    next_cuid: str = CUID_GENERATOR.generate()

    # Validate CUID
    print(Cuid.is_cuid(my_cuid))  # True
```

`is_cuid` (and `Cuid.is_cuid`) also accepts optional `min_length` and `max_length` arguments to tighten the allowed length.
The bounds are clamped to 2 and 98 characters, so they can narrow but never widen what is considered valid.
