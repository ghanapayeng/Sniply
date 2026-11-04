"""
Custom short-code generation logic.

No pyshorteners / hashids / shortuuid — this is a hand-rolled base62
encoder built on top of MongoDB's auto-incrementing counter, plus a
random-string fallback for custom-length codes.
"""

import random
import string
import time

ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase  # 0-9 a-z A-Z
BASE = len(ALPHABET)  # 62


def encode_base62(num: int) -> str:
    """Convert a non-negative integer into a base62 string using our own alphabet."""
    if num == 0:
        return ALPHABET[0]

    digits = []
    while num > 0:
        num, remainder = divmod(num, BASE)
        digits.append(ALPHABET[remainder])

    return "".join(reversed(digits))


def decode_base62(code: str) -> int:
    """Reverse of encode_base62 — turns a short code back into its integer id."""
    num = 0
    for char in code:
        num = num * BASE + ALPHABET.index(char)
    return num


def generate_code_from_counter(counter_value: int, min_length: int = 6) -> str:
    """
    Turn a MongoDB counter value into a short code.

    We salt the counter a bit so codes don't look like 1, 2, 3, 4... in
    sequence (which would leak how many links exist and let people guess
    neighbouring links). Padded to min_length by mixing in the current
    time's low bits.
    """
    salted = (counter_value * 1_299_709) ^ (int(time.time()) & 0xFFFF)
    code = encode_base62(salted)

    while len(code) < min_length:
        code = ALPHABET[random.randrange(BASE)] + code

    return code[:max(min_length, len(code))]


def generate_random_code(length: int = 6) -> str:
    """Pure random fallback, used mainly for collision retries."""
    return "".join(random.choice(ALPHABET) for _ in range(length))


def is_valid_custom_alias(alias: str) -> bool:
    """Custom aliases: 3-20 chars, alphanumeric + underscore/hyphen only."""
    if not (3 <= len(alias) <= 20):
        return False
    return all(c in ALPHABET + "-_" for c in alias)
