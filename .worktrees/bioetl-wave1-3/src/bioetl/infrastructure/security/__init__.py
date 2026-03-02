"""Security infrastructure components.

This package contains implementations for security-related operations:
- PII hashing for Silver layer compliance (RULES.md §5.4)
"""

from bioetl.infrastructure.security.pii_hasher import Sha256PiiHasher

__all__ = ["Sha256PiiHasher"]
