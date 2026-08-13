"""Typed extraction of Click option mappings without `cast()`."""

from __future__ import annotations

from collections.abc import Mapping

__all__ = [
    "option_bool",
    "option_bool_get",
    "option_int",
    "option_int_get",
    "option_optional_bool_get",
    "option_optional_int",
    "option_optional_int_get",
    "option_optional_str",
    "option_optional_str_get",
    "option_str",
]


def option_str(values: Mapping[str, object], key: str) -> str:
    """Return a required string option."""
    value = values[key]
    if not isinstance(value, str):
        raise TypeError(f"option {key!r} must be str, got {type(value).__name__}")
    return value


def option_optional_str(values: Mapping[str, object], key: str) -> str | None:
    """Return an optional string option."""
    value = values[key]
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"option {key!r} must be str | None, got {type(value).__name__}")
    return value


def option_optional_str_get(values: Mapping[str, object], key: str) -> str | None:
    """Return an optional string option, or None when the key is absent."""
    if key not in values:
        return None
    return option_optional_str(values, key)


def option_bool(values: Mapping[str, object], key: str) -> bool:
    """Return a required bool option."""
    value = values[key]
    if not isinstance(value, bool):
        raise TypeError(f"option {key!r} must be bool, got {type(value).__name__}")
    return value


def option_bool_get(values: Mapping[str, object], key: str, default: bool) -> bool:
    """Return a bool option, or ``default`` when the key is absent/None."""
    if key not in values:
        return default
    value = values[key]
    if value is None:
        return default
    if not isinstance(value, bool):
        raise TypeError(f"option {key!r} must be bool, got {type(value).__name__}")
    return value


def option_optional_bool_get(values: Mapping[str, object], key: str) -> bool | None:
    """Return an optional bool option, or None when the key is absent."""
    if key not in values:
        return None
    value = values[key]
    if value is None:
        return None
    if not isinstance(value, bool):
        raise TypeError(f"option {key!r} must be bool | None, got {type(value).__name__}")
    return value


def option_int(values: Mapping[str, object], key: str) -> int:
    """Return a required int option."""
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"option {key!r} must be int, got {type(value).__name__}")
    return value


def option_int_get(values: Mapping[str, object], key: str, default: int) -> int:
    """Return an int option, or ``default`` when the key is absent/None."""
    if key not in values:
        return default
    value = values[key]
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"option {key!r} must be int, got {type(value).__name__}")
    return value


def option_optional_int(values: Mapping[str, object], key: str) -> int | None:
    """Return an optional int option."""
    value = values[key]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"option {key!r} must be int | None, got {type(value).__name__}")
    return value


def option_optional_int_get(values: Mapping[str, object], key: str) -> int | None:
    """Return an optional int option, or None when the key is absent."""
    if key not in values:
        return None
    return option_optional_int(values, key)
