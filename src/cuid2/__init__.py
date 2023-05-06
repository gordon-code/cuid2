# DO NOT CHANGE MANUALLY THIS IS CHANGED IN THE PIPELINES
__version__ = '1.0.0'

from datetime import datetime
from random import SystemRandom

from cuid2.generator import (generate_entropy, generate_fingerprint,
                             generate_hash)
from cuid2.utils import base36_encode, random_letter, string_to_int


def cuid(length: int = 24) -> str:
    generator: SystemRandom = SystemRandom()
    fingerprint: str = generate_fingerprint()
    entropy: str = generate_entropy(length)
    counter: str = base36_encode(int(generator.random() * 2057) + 1)
    letter: str = random_letter()

    time: str = datetime.now().strftime('%m%d%Y%H%M%S')
    time = base36_encode(string_to_int(time))

    return letter + generate_hash(time + entropy + counter + fingerprint, length)[1:length]
