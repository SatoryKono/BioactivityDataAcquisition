"""
Metadata helpers module for common metadata operations.
"""



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
    metadata = {"key": value}
    if not metadata:
        raise ValueError("Metadata is empty")
    return metadata
