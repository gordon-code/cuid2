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

* **Polyglot ORM Compatibility**: Generate and validate 24-character base36 primary keys in Python services that share databases with TypeScript/Node.js applications using Prisma (`@default(cuid(2))`) or Drizzle (`@paralleldrive/cuid2`).
* **Opaque, HTML/CSS-Safe Public IDs**: Unlike time-ordered identifiers such as `uuid.uuid7()` and ULID—which embed a 48-bit millisecond creation timestamp in their prefix—CUID2 hashes all entropy, time, counter, and fingerprint inputs through SHA3-512 so IDs do not leak creation timestamps or sequential creation rates, and always start with a lowercase ASCII letter (`[a-z]`) safe for HTML element IDs and CSS selectors.

## Install
```
pip install cuid2
```

## Usage

For most use cases, use the top-level `create_id` and `is_cuid` helpers directly:
```python
from cuid2 import create_id, is_cuid

my_cuid: str = create_id()
short_cuid: str = create_id(length=10)

print(is_cuid(my_cuid))  # True
```

You can also generate CUIDs directly in the terminal (optionally specifying a custom length):
```bash
$ cuid2
$ cuid2 10
```

Or you can rely on a CUID wrapper if you want a pre-configured generator function:
```python
from typing import Callable
from cuid2 import cuid_wrapper

cuid_generator: Callable[[], str] = cuid_wrapper()
short_cuid_generator: Callable[[], str] = cuid_wrapper(length=10)


def main():
    my_cuid: str = cuid_generator()
    short_cuid: str = short_cuid_generator()
```

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
