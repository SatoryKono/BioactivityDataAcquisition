"""Metadata helpers module for common metadata operations."""

from __future__ import annotations


def _build_metadata(key: str, value: str) -> dict[str, str]:
    """Build the raw metadata payload before validation."""
    return {"key": value}


def build_and_validate_metadata(key: str, value: str) -> dict[str, str]:
    """Build and validate metadata dictionary.

    Args:
        key: Metadata key.
        value: Metadata value.

    Returns:
        Validated metadata dictionary.

    Raises:
        ValueError: If metadata is empty.
    """
    metadata = _build_metadata(key, value)
    if not metadata:
        raise ValueError("Metadata is empty")
    return metadata
