"""Immutable JSON-compatible containers for domain snapshots."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from copy import deepcopy
from typing import Never, overload, override

__all__ = [
    "FrozenDict",
    "FrozenList",
    "deep_freeze_json",
    "deep_thaw_json",
    "freeze_fields",
]


def _immutable(*_args: object, **_kwargs: object) -> Never:
    raise TypeError("nested state is immutable")


class FrozenList(Sequence[object]):
    """Immutable sequence snapshot that cannot be mutated via list APIs."""

    __slots__ = ("_items",)
    _items: tuple[object, ...]

    def __init__(self, iterable: Iterable[object] = ()) -> None:
        object.__setattr__(self, "_items", tuple(iterable))

    @overload
    def __getitem__(self, index: int) -> object: ...

    @overload
    def __getitem__(self, index: slice) -> FrozenList: ...

    @override
    def __getitem__(self, index: int | slice) -> object:
        items = self._items
        if isinstance(index, slice):
            return FrozenList(items[index])
        return items[index]

    @override
    def __len__(self) -> int:
        return len(self._items)

    @override
    def __iter__(self) -> Iterator[object]:
        return iter(self._items)

    @override
    def __repr__(self) -> str:
        return f"FrozenList({list(self._items)!r})"

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, FrozenList):
            return self._items == other._items
        if isinstance(other, Sequence) and not isinstance(
            other, (str, bytes, bytearray)
        ):
            return list(self._items) == list(other)
        return NotImplemented

    @override
    def __hash__(self) -> int:
        return hash(self._items)

    def __copy__(self) -> FrozenList:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> FrozenList:
        del memo
        return self


class FrozenDict(Mapping[str, object]):
    """Immutable mapping snapshot that cannot be mutated via dict APIs."""

    __slots__ = ("_data",)
    _data: dict[str, object]

    def __init__(
        self,
        mapping: Mapping[str, object] | Iterable[tuple[str, object]] | None = None,
        **kwargs: object,
    ) -> None:
        data: dict[str, object] = {}
        if mapping is not None:
            if isinstance(mapping, Mapping):
                data.update(mapping)
            else:
                data.update(dict(mapping))
        if kwargs:
            data.update(kwargs)
        object.__setattr__(self, "_data", dict(data))

    @override
    def __getitem__(self, key: str) -> object:
        return self._data[key]

    @override
    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    @override
    def __len__(self) -> int:
        return len(self._data)

    @override
    def __repr__(self) -> str:
        return f"FrozenDict({self._data!r})"

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self._data) == dict(other)
        return NotImplemented

    @override
    def __hash__(self) -> int:
        return hash(tuple(sorted(self._data.items(), key=lambda item: item[0])))

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
    if isinstance(value, FrozenDict | FrozenList):
        return value
    if isinstance(value, dict):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            frozen[key] = deep_freeze_json(item)
        return FrozenDict(frozen)
    return _deep_freeze_sequence(value)


def _deep_thaw_sequence(value: object) -> object:
    """Thaw supported sequence/set containers or copy a scalar value."""
    if isinstance(value, (FrozenList, list, tuple, set, frozenset)):
        return [deep_thaw_json(item) for item in value]
    return deepcopy(value)


def deep_thaw_json(value: object) -> object:
    """Return a detached mutable JSON-compatible copy of a frozen snapshot."""
    if isinstance(value, FrozenDict):
        return {key: deep_thaw_json(item) for key, item in value.items()}
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
