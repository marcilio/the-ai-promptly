import hashlib
import re
import struct

NUM_HASHES = 128
SHINGLE_SIZE = 9
MAX_HASH = (1 << 32) - 1
DEFAULT_SIMILARITY_THRESHOLD = 0.5


def _hash_coefficients():
    coeffs = []
    for i in range(NUM_HASHES):
        seed = hashlib.sha256(f"minhash-coeff-{i}".encode("utf-8")).digest()
        a, b = struct.unpack(">II", seed[:8])
        coeffs.append((a | 1, b))
    return coeffs


_COEFFS = _hash_coefficients()


def _normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _shingles(text, k=SHINGLE_SIZE):
    if not text:
        return []
    if len(text) <= k:
        return [text]
    return [text[i : i + k] for i in range(len(text) - k + 1)]


def compute_signature(text):
    shingles = _shingles(_normalize_text(text))
    if not shingles:
        return None
    base = {int.from_bytes(hashlib.sha1(s.encode("utf-8")).digest()[:4], "big") for s in shingles}
    return [min(((a * x + b) & MAX_HASH) for x in base) for a, b in _COEFFS]


def jaccard_estimate(sig_a, sig_b):
    if not sig_a or not sig_b or len(sig_a) != len(sig_b):
        return 0.0
    matches = sum(1 for x, y in zip(sig_a, sig_b) if x == y)
    return matches / len(sig_a)


def is_near_duplicate(signature, known_signatures, threshold=DEFAULT_SIMILARITY_THRESHOLD):
    if not signature:
        return False
    for other in known_signatures:
        if jaccard_estimate(signature, other) >= threshold:
            return True
    return False
