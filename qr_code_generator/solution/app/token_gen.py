import hashlib
import string
import time

BASE62_CHARS = string.digits + string.ascii_letters
TOKEN_LENGTH = 7
MAX_RETRIES = 20


def base62_encode(data: bytes) -> str:
    num = int.from_bytes(data, "big")
    if num == 0:
        return BASE62_CHARS[0]

    result = []
    while num > 0:
        num, remainder = divmod(num, 62)
        result.append(BASE62_CHARS[remainder])

    return "".join(reversed(result))


def generate_token(url: str) -> str:
    for attempt in range(MAX_RETRIES):
        nonce = f"{int(time.time())}_{attempt}"
        hash_input = url + nonce
        raw_hash = hashlib.sha256(hash_input.encode()).digest()
        return base62_encode(raw_hash)[:TOKEN_LENGTH]

    raise RuntimeError(f"Failed to generate unique token after {MAX_RETRIES} retries")
