"""Port for PII (Personal Identifiable Information) hashing.

Implements RULES.md §5.4 - Sensitive Data Policy.
Silver layer MUST hash PII fields using sha256(lowercase(value) + SALT).

This port abstracts PII hashing to allow different implementations
(SHA256, Argon2) and supports salt rotation for security compliance.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = [
    "PiiHasherPort",
]


@runtime_checkable
class PiiHasherPort(Protocol):
    """Port for hashing PII fields in Silver layer.

    All PII fields (author names, affiliations) MUST be hashed before
    writing to Silver to comply with RULES.md §5.4.

    The implementation MUST:
    - Use salted hashing (BIOETL_PII_SALT_CURRENT)
    - Normalize values before hashing (lowercase, strip, NFKC)
    - Support salt rotation via BIOETL_PII_SALT_NEXT
    - Return None for None input (null-safe)

    Example:
        >>> hasher = Sha256PiiHasher(salt="secret_salt")
        >>> hasher.hash_value("John Doe")
        'a1b2c3...'  # SHA256 hex digest
        >>> hasher.hash_list(["Alice", "Bob"])
        ['d4e5f6...', 'g7h8i9...']
    """

    def hash_value(self, value: str | None) -> str | None:
        """Hash a single PII value.

        Args:
            value: The PII value to hash (e.g., author name).
                   If None, returns None.

        Returns:
            SHA256 hex digest of normalized(value) + salt,
            or None if input is None.


        """
        ...

    def hash_list(self, values: list[str] | None) -> list[str] | None:
        """Hash a list of PII values.

        Args:
            values: List of PII values (e.g., list of author names).
                    If None, returns None.

        Returns:
            List of SHA256 hex digests, or None if input is None.


        """
        ...

    def get_salt_id(self) -> str:
        """Get identifier for current salt (for audit/tracking).

        Returns:
            Short identifier of current salt (first 8 chars of salt hash).
            Used for tracking which salt version was used for hashing.


        """
        ...
