"""Pipeline transform/filter callbacks in domain vocabulary."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.types import JsonDict

    PipelineContext = object


@runtime_checkable
class TransformCallback(Protocol):
    """Bronze-to-Silver transformation callback contract."""

    def __call__(
        self,
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> Awaitable[object | None]:
        """Transform one bronze record."""
        ...


@runtime_checkable
class GoldFilterCallback(Protocol):
    """Gold-write predicate callback contract."""

    def __call__(self, context: PipelineContext, record: JsonDict) -> bool:
        """Decide whether one silver record should flow to Gold."""
        ...


@runtime_checkable
class GoldTransformCallback(Protocol):
    """Silver-to-Gold transformation callback contract."""

    def __call__(self, context: PipelineContext, record: JsonDict) -> JsonDict:
        """Transform one silver record for Gold output."""
        ...
