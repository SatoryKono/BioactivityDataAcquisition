"""Validation helpers module for common validation operations."""

from __future__ import annotations


def validate_data(data: object) -> None:
    """Validate that data is present (None / empty collections only).

    Numeric zero and boolean False are valid payloads and must not fail.

    Args:
        data: Data to validate.

    Raises:
        ValueError: If data is None or an empty collection/string.
    """
    if data is None or (
        isinstance(
            data, (str, bytes, bytearray, list, tuple, set, frozenset, dict, range)
        )
        and len(data) == 0
    ):
        raise ValueError("Data is empty")
