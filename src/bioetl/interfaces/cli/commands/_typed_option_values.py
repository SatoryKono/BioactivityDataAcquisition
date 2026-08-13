"""Runtime narrowing helpers for values supplied by Click."""

from __future__ import annotations

from collections.abc import Mapping


def require_option[T](
    options: Mapping[str, object],
    name: str,
    expected_type: type[T],
) -> T:
    """Return a required Click option after runtime type narrowing."""
    value = options[name]
    if not isinstance(value, expected_type):
        raise TypeError(
            f"CLI option {name!r} must be {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )
    if expected_type is int and isinstance(value, bool):
        raise TypeError(f"CLI option {name!r} must be int, got bool")
    return value


def optional_option[T](
    options: Mapping[str, object],
    name: str,
    expected_type: type[T],
) -> T | None:
    """Return an optional Click option after runtime type narrowing."""
    value = options.get(name)
    if value is None:
        return None
    if not isinstance(value, expected_type):
        raise TypeError(
            f"CLI option {name!r} must be {expected_type.__name__} or None, "
            f"got {type(value).__name__}"
        )
    if expected_type is int and isinstance(value, bool):
        raise TypeError(f"CLI option {name!r} must be int or None, got bool")
    return value


def option_or_default[T](
    options: Mapping[str, object],
    name: str,
    default: T,
    expected_type: type[T],
) -> T:
    """Return a Click option or its typed default after runtime narrowing."""
    value = options.get(name, default)
    if not isinstance(value, expected_type):
        raise TypeError(
            f"CLI option {name!r} must be {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )
    if expected_type is int and isinstance(value, bool):
        raise TypeError(f"CLI option {name!r} must be int, got bool")
    return value


def string_tuple_option(
    options: Mapping[str, object],
    name: str,
) -> tuple[str, ...]:
    """Return a repeatable string option after validating every item."""
    value = options.get(name, ())
    if not isinstance(value, tuple):
        raise TypeError(f"CLI option {name!r} must be a tuple of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"CLI option {name!r} must be a tuple of strings")
        result.append(item)
    return tuple(result)


__all__ = [
    "option_or_default",
    "optional_option",
    "require_option",
    "string_tuple_option",
]
