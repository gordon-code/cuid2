from __future__ import annotations

import os
import socket
import string
from math import floor
from typing import TYPE_CHECKING, Callable, Final, Optional

try:
    from hashlib import sha3_512 as sha512
except ImportError:
    import warnings

    warnings.warn("sha3_512 is not available, falling back to sha512, this is less secure!", UserWarning, stacklevel=2)
    from hashlib import sha512  # type: ignore[assignment] # pylint: disable=ungrouped-imports


BIG_LENGTH: Final = 32


if TYPE_CHECKING:
    from hashlib import _Hash

    from _random import Random


def create_counter(count: int) -> Callable[[], int]:
    """Creates a counter that returns an incremented value each time it is called.

    Parameters
    ----------
    count : int
        Initial count value for the counter.

    Returns
    -------
    Callable[[], int]
        Closure function `counter` that takes no arguments and returns an integer. The closure function keeps track
        of a count variable that is initialized with the value passed as an argument to `create_counter`. Each time
        the closure function is called, it increments the count variable and returns its new value.
    """

    def counter() -> int:
        nonlocal count
        count += 1
        return count

    return counter


def create_fingerprint(random_generator: Random, fingerprint_data: Optional[str] = "") -> str:
    """Creates a fingerprint, by default combining process ID, hostname, and environment variables
    with entropy and then hashing the result.

    Parameters
    ----------
    random_generator : "Random"
        Used as the base generator to generate some entropy.
    fingerprint_data : str, optional
        An optional parameter that contains data to be included in the fingerprint.
        If it is not provided, the function combines process ID, hostname, and environment variables

    Returns
    -------
    str
        The hashed value of the input `fingerprint_data` or default value concatenated with a randomly generated
        entropy string.
        The length of the returned string is trimmed to the constant `BIG_LENGTH` (32 characters).
    """
    if not fingerprint_data:
        process_id: int = os.getpid()
        hostname: str = socket.gethostname()
        env_variables: str = "".join(os.environ.keys())

        fingerprint_data: str = str(process_id) + hostname + env_variables  # type: ignore[no-redef]

    fingerprint: str = str(fingerprint_data) + create_entropy(random_generator, BIG_LENGTH)
    return create_hash(fingerprint)[0:BIG_LENGTH]


def create_entropy(random_generator: Random, length: int = 4) -> str:
    """Creates a random string of specified length using a base36 encoding.

    Parameters
    ----------
    random_generator : "Random"
        Used as the base generator to generate a random string.
    length : int, default=4
        The length parameter is an integer that specifies the length of the entropy string to be generated.
        The default value is 4, but it can be set to any positive integer value.

    Returns
    -------
    str
        Random characters encoded as a base36 string. The length of the string is determined by
        the `length` parameter passed to the function.

    Raises
    ------
    ValueError
        If the input integer is less than 1.
    """
    if length < 1:
        msg = "Cannot create entropy without a length >= 1."
        raise ValueError(msg)

    entropy: str = ""

    while len(entropy) < length:
        entropy += base36_encode(floor(random_generator.random() * 36))

    return entropy


def create_hash(data: str = "") -> str:
    """Creates a hash value for a given string using the SHA-512 algorithm (prefers SHA3) and returns
    it in base36 encoding format after dropping the first character.

    Parameters
    ----------
    data : str, default=""
        Data to be hashed. It is an optional parameter with a default value of an empty string.
        If no value is provided for `data`, an empty string will be hashed.

    Returns
    -------
    str
        Base36 encoding of the SHA-512 hash of the input string `data`, with the first character dropped.

    """
    hashed_value: _Hash = sha512(data.encode())
    hashed_int: int = int.from_bytes(hashed_value.digest(), byteorder="big")

    # Drop the first character because it will bias the histogram to the left.
    return base36_encode(hashed_int)[1:]


def create_letter(random_generator: Random) -> str:
    """Generates a random lowercase letter using a given random number generator.

    Parameters
    ----------
    random_generator : "Random"
        Used as the base generator to generate a random letter.

    Returns
    -------
    str
        a randomly generated lowercase letter from the English alphabet.
    """
    alphabet: str = string.ascii_lowercase
    return alphabet[floor(random_generator.random() * len(alphabet))]


def base36_encode(number: int) -> str:
    """Encodes a positive integer into a base36 string.

    Parameters
    ----------
    number : int
        Integer to be encoded as a base36 string.

    Returns
    -------
    str
        A string that represents the base36 encoded input integer.
        If the input integer is negative, a ValueError is raised.
        If the input integer is 0, the function returns the string "0".

    Raises
    ------
    ValueError
        If the input integer is negative.
    """
    if number < 0:
        msg = "Cannot encode negative integers."
        raise ValueError(msg)

    encoded_string: str = ""
    alphabet: str = string.digits + string.ascii_lowercase
    alphabet_length: int = len(alphabet)

    while number != 0:
        number, mod = divmod(number, alphabet_length)
        encoded_string = alphabet[mod] + encoded_string

    return encoded_string or "0"
