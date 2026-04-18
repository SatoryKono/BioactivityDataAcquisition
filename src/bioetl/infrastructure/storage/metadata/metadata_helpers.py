"""
Metadata helpers module for common metadata operations.
"""

from typing import Any, Dict


def build_and_validate_metadata(key: str, value: str) -> Dict[str, str]:
    """Build and validate metadata dictionary.

    Args:
        key: Metadata key.
        value: Metadata value.

    Returns:
        Validated metadata dictionary.

    Raises:
        ValueError: If metadata is empty.
    """
    metadata = {"key": value}
    if not metadata:
        raise ValueError("Metadata is empty")
    return metadata
