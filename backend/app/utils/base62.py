"""
Base62 encoding for sequence-id-based short codes (see Architecture
section 9.1: short_code = base62(urls.id)).

Alphabet ordering (digits, lowercase, uppercase) is the conventional
choice; any fixed bijective alphabet works, this one just reads naturally
in URLs.
"""
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)
_INDEX = {char: idx for idx, char in enumerate(ALPHABET)}


def base62_encode(num: int) -> str:
    if num < 0:
        raise ValueError("base62_encode does not support negative numbers")
    if num == 0:
        return ALPHABET[0]
    digits = []
    while num:
        num, rem = divmod(num, BASE)
        digits.append(ALPHABET[rem])
    return "".join(reversed(digits))


def base62_decode(code: str) -> int:
    num = 0
    for char in code:
        if char not in _INDEX:
            raise ValueError(f"Invalid base62 character: {char!r}")
        num = num * BASE + _INDEX[char]
    return num
