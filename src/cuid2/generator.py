import hashlib
import os
import socket
from random import SystemRandom

from cuid2.utils import base36_encode, pad_string, string_to_int


def generate_entropy(length: int = 4) -> str:
    entropy: str = ''
    primes: list[int] = [109717, 109721, 109741, 109751, 109789, 109793, 109807, 109819, 109829, 109831]
    generator: SystemRandom = SystemRandom()

    while len(entropy) < length:
        prime: int = primes[int(generator.random() * len(primes))]
        entropy += base36_encode(int(generator.random() * prime))

    return entropy


def generate_hash(data: str = '', length: int = 32) -> str:
    sha3_512: hashlib._Hash = hashlib.sha3_512()
    raw_data: bytes = (data + generate_entropy(length)).encode()

    sha3_512.update(raw_data)

    hash_result: str = sha3_512.hexdigest()

    hash_result = hash_result.lstrip('0x')
    hash_result = hash_result.split('L', maxsplit=1)[0]

    result: int = string_to_int(hash_result)

    return base36_encode(result)


def generate_fingerprint() -> str:
    generator: SystemRandom = SystemRandom()

    process_id_hash: str = base36_encode(os.getpid())
    process_id_hash = pad_string(process_id_hash, 2)

    process_id: int = string_to_int(process_id_hash)
    raw_hostname: str = socket.gethostname()
    entropy: int = int(generator.random() + 1) * 2063

    hostname: int = sum(ord(c) for c in str(raw_hostname))
    hostname_hash: str = base36_encode(hostname + len(raw_hostname) + 36)

    hostname_hash = pad_string(hostname_hash, 2)
    hostname = string_to_int(hostname_hash)

    fingerprint: str = str(entropy + process_id + hostname)
    fingerprint = generate_hash(fingerprint)

    result: int = string_to_int(fingerprint)

    return base36_encode(result)
