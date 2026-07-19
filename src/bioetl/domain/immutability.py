"""Immutable JSON-compatible containers for domain snapshots."""

from __future__ import annotations

from copy import deepcopy
from typing import Never

__all__ = [
    "FrozenDict",
    "FrozenList",
    "deep_freeze_json",
    "deep_thaw_json",
    "freeze_fields",
]


def _immutable(*_args: object, **_kwargs: object) -> Never:
    raise TypeError("nested state is immutable")


class FrozenList(list[object]):
    """List-compatible snapshot that rejects mutation."""

    __setitem__ = _immutable
    __delitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable

    def __copy__(self) -> FrozenList:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> FrozenList:
        del memo
        return self


class FrozenDict(dict[str, object]):
    """Dict-compatible snapshot that rejects mutation."""

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable

    def __copy__(self) -> FrozenDict:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> FrozenDict:
        del memo
        return self


def _freeze_list(value: list[object]) -> FrozenList:
    return FrozenList(deep_freeze_json(item) for item in value)


def _freeze_tuple(value: tuple[object, ...]) -> tuple[object, ...]:
    return tuple(deep_freeze_json(item) for item in value)


def _freeze_set(value: set[object]) -> frozenset[object]:
    return frozenset(deep_freeze_json(item) for item in value)


def _deep_freeze_sequence(value: object) -> object:
    """Freeze supported sequence/set containers or copy a scalar value."""
    if isinstance(value, list):
        return _freeze_list(value)
    if isinstance(value, tuple):
        return _freeze_tuple(value)
    if isinstance(value, set):
        return _freeze_set(value)
    return deepcopy(value)


def deep_freeze_json(value: object) -> object:
    """Snapshot JSON-like nested state into mutation-resistant containers."""
    if isinstance(value, dict):
        return FrozenDict(
            {str(key): deep_freeze_json(item) for key, item in value.items()}
        )
    return _deep_freeze_sequence(value)


def _deep_thaw_sequence(value: object) -> object:
    """Thaw supported sequence/set containers or copy a scalar value."""
    if isinstance(value, (list, tuple)):
        return [deep_thaw_json(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [deep_thaw_json(item) for item in value]
    return deepcopy(value)


def deep_thaw_json(value: object) -> object:
    """Return a detached mutable JSON-compatible copy of a frozen snapshot."""
    if isinstance(value, dict):
        return {str(key): deep_thaw_json(item) for key, item in value.items()}
    return _deep_thaw_sequence(value)


def freeze_fields(instance: object, field_names: tuple[str, ...]) -> None:
    """Replace selected frozen-dataclass fields with deep immutable snapshots."""
    for field_name in field_names:
        object.__setattr__(
            instance,
            field_name,
            deep_freeze_json(getattr(instance, field_name)),
        )
