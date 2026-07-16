"""Immutable JSON-compatible containers for domain snapshots."""

from __future__ import annotations

from copy import deepcopy


def _immutable(*_args: object, **_kwargs: object) -> None:
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


def deep_freeze_json(value: object) -> object:
    """Snapshot JSON-like nested state into mutation-resistant containers."""
    if isinstance(value, dict):
        return FrozenDict(
            {str(key): deep_freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return FrozenList(deep_freeze_json(item) for item in value)
    if isinstance(value, set):
        return frozenset(deep_freeze_json(item) for item in value)
    return deepcopy(value)


def freeze_fields(instance: object, field_names: tuple[str, ...]) -> None:
    """Replace selected frozen-dataclass fields with deep immutable snapshots."""
    for field_name in field_names:
        object.__setattr__(
            instance,
            field_name,
            deep_freeze_json(getattr(instance, field_name)),
        )
