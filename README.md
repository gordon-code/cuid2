# cuid2.py

[![Python](https://img.shields.io/badge/python-3.6.1-blue.svg)](https://img.shields.io/badge/python-3.6.1-blue.svg)
[![PyPi](https://img.shields.io/pypi/v/cuid2.svg)](https://pypi.python.org/pypi/cuid2)
[![PyPi](https://img.shields.io/pypi/dm/cuid2.svg)](https://pypi.python.org/pypi/cuid2)
[![cuid2](https://snyk.io/advisor/python/cuid2/badge.svg)](https://snyk.io/advisor/python/cuid2)

CUID2 for Python 3. Next generation GUIDs. Collision-resistant ids optimized for horizontal scaling and performance.

A port of the [CUID2 reference implementation](https://github.com/paralleldrive/cuid2) by [Parallel Drive](https://github.com/paralleldrive) to Python 3.


## What is CUID2?

* Secure: It's not possible to guess the next ID.
* Collision resistant: It's extremely unlikely to generate the same ID twice.
* Horizontally scalable: Generate IDs on multiple machines without coordination.
* Offline-compatible: Generate IDs without a network connection.
* URL and name-friendly: No special characters.

## Why?

For more information on the theory and usage of CUID2, see the [following](https://github.com/paralleldrive/cuid2#why).

## Improvements Over CUID

For more information on the improvements of CUID2 over CUID, see the [following](https://github.com/paralleldrive/cuid2#improvements-over-cuid).


## Install
```
pip install cuid2
```

## Usage
You can generate CUIDs with the following:
```python
from cuid2 import cuid

def main():
  my_cuid: str = cuid()
```

