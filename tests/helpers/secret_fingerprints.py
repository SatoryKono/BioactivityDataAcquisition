"""Detect known historical Neo4j passwords without keeping their plaintext."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Collection

HISTORICAL_NEO4J_PASSWORD_FINGERPRINTS = (
    (21, "08d04c35b177149457a4ac85900494dbf95d19f76f79ec2afb131af2b92db305"),
    (22, "11eefeaabfdb268cb8eca67da072d97f015ba5afc14dcea3915d06c7d85fb8a8"),
)


def contains_secret_fingerprint(
    content: str, fingerprints: Collection[tuple[int, str]]
) -> bool:
    """Match ASCII word-shaped credentials, including embedded substrings."""
    by_length: dict[int, set[str]] = {}
    for length, digest in fingerprints:
        by_length.setdefault(length, set()).add(digest)
    for match in re.finditer(r"[A-Za-z0-9_-]+", content):
        token = match.group().encode("ascii")
        for length, digests in by_length.items():
            for start in range(len(token) - length + 1):
                if hashlib.sha256(token[start : start + length]).hexdigest() in digests:
                    return True
    return False


def assert_no_historical_neo4j_passwords(content: str) -> None:
    """Fail without echoing any credential or surrounding source content."""
    assert not contains_secret_fingerprint(
        content, HISTORICAL_NEO4J_PASSWORD_FINGERPRINTS
    ), "Historical Neo4j credential fingerprint present"
