"""Typed extraction of Click option mappings without `cast()`."""

from __future__ import annotations

from collections.abc import Mapping

__all__ = [
    "option_bool",
    "option_int",
    "option_optional_int",
    "option_optional_str",
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


def option_bool(values: Mapping[str, object], key: str) -> bool:
    """Return a required bool option."""
    value = values[key]
    if not isinstance(value, bool):
        raise TypeError(f"option {key!r} must be bool, got {type(value).__name__}")
    return value


def option_int(values: Mapping[str, object], key: str) -> int:
    """Return a required int option."""
    value = values[key]
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
