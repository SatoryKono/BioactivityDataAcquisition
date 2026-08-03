"""Helper functions for quarantine operations.

Contains utility functions used across quarantine modules.
"""

from __future__ import annotations

__all__ = ["MAX_PAYLOAD_SIZE", "calculate_hash", "quote_literal"]


import hashlib


def quote_literal(value: object) -> str:
    """Safely quote a literal value for a Delta Lake predicate.

    Args:
        value: Value to quote

    Returns:
        Quoted string safe for Delta Lake predicates

    """
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return f"'{value!s}'"


def calculate_hash(payload_json: str) -> str:
    """Calculate SHA256 hash of payload for deduplication.

    Args:
        payload_json: JSON string of payload

    Returns:
        Hex digest of SHA256 hash

    """
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


# Maximum payload size (64KB per REQ-QUARANTINE-002)
MAX_PAYLOAD_SIZE = 64 * 1024
