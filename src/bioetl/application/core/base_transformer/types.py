"""Shared typing contracts for base transformer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.entities import BaseEntity

T = TypeVar("T", bound="BaseEntity")
V = TypeVar("V", covariant=True)


@runtime_checkable
class ValueObjectWithFromRaw(Protocol[V]):
    """Protocol for Value Objects exposing ``from_raw`` and ``value``."""

    @classmethod
    def from_raw(cls, raw: Any) -> V | None:  # Any: raw input
        ...

    @property
    def value(self) -> Any:  # Any: VO value type varies (str | int | float)
        ...
