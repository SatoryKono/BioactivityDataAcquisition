"""Shared parsing helpers for composite config serialization."""

from __future__ import annotations

__all__ = [
    "optional_bool",
    "optional_int",
    "optional_str",
    "optional_str_tuple",
    "require_object_dict",
    "require_object_dict_sequence",
    "require_str",
    "require_str_tuple",
]


def require_object_dict(value: object, field_name: str) -> dict[str, object]:
    """Validate and normalize mapping-like values.

    Args:
        value: Input value to validate as a dictionary.
        field_name: Name of the field, used in error messages.

    Returns:
        Dictionary with string keys validated from the input mapping.
    """
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dictionary")
    return {str(key): item for key, item in value.items()}


def require_object_dict_sequence(
    value: object,
    field_name: str,
) -> tuple[dict[str, object], ...]:
    """Validate and normalize a sequence of dictionaries.

    Args:
        value: Input value to validate as a list or tuple of dictionaries.
        field_name: Name of the field, used in error messages.

    Returns:
        Tuple of dictionaries with string keys validated from the input sequence.
    """
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list")
    result: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{field_name} must contain dictionaries")
        result.append({str(key): element for key, element in item.items()})
    return tuple(result)


def require_str(value: object, field_name: str) -> str:
    """Validate required string field.

    Args:
        value: Input value to validate as a non-empty string.
        field_name: Name of the field, used in error messages.

    Returns:
        Validated non-empty string value.
    """
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def optional_str(value: object, field_name: str) -> str | None:
    """Validate optional string field.

    Args:
        value: Input value to validate, or None to indicate absence.
        field_name: Name of the field, used in error messages.

    Returns:
        Validated non-empty string if provided, None otherwise.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string when provided")
    return value


def optional_bool(value: object, default: bool, field_name: str) -> bool:
    """Validate optional bool field.

    Args:
        value: Input value to validate as a boolean, or None to use default.
        default: Fallback value returned when value is None.
        field_name: Name of the field, used in error messages.

    Returns:
        Validated boolean value, or default if not provided.
    """
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def optional_int(
    value: object,
    field_name: str,
    default: int | None = None,
) -> int | None:
    """Validate optional int field.

    Args:
        value: Input value to validate as an integer, or None to use default.
        field_name: Name of the field, used in error messages.
        default: Fallback value returned when value is None. Defaults to None.

    Returns:
        Validated integer if provided, or default (None) otherwise.
    """
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value


def require_str_tuple(value: object, field_name: str) -> tuple[str, ...]:
    """Validate required list/tuple of strings.

    Args:
        value: Input value to validate as a list or tuple of non-empty strings.
        field_name: Name of the field, used in error messages.

    Returns:
        Tuple of validated non-empty strings from the input sequence.
    """
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{field_name} must contain non-empty strings")
    return tuple(value)


def optional_str_tuple(value: object, field_name: str) -> tuple[str, ...] | None:
    """Validate optional list/tuple of strings.

    Args:
        value: Input value to validate as a list or tuple of strings, or None.
        field_name: Name of the field, used in error messages.

    Returns:
        Tuple of validated non-empty strings if provided, None otherwise.
    """
    if value is None:
        return None
    return require_str_tuple(value, field_name)
