"""
Utility functions for dictionary merging.
"""
from typing import Any


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        base: The base dictionary.
        update: The dictionary with updates.

    Returns:
        A new dictionary with merged values.
    """
    result = base.copy()
    for key, value in update.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
