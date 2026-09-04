"""
SHA-256 Hashing Module.
Calculates deterministic content hashes for document deduplication and versioning.
"""

import hashlib


def compute_sha256(content: bytes) -> str:
    """Computes SHA-256 hex digest for given binary content."""
    if not isinstance(content, bytes):
        raise TypeError("Expected bytes input for SHA-256 hashing")
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()
