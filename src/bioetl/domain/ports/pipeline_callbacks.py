"""Pipeline transform/filter callbacks in domain vocabulary."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.types import JsonDict

    PipelineContext = object


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


class GoldFilterCallback(Protocol):
    """Gold-write predicate callback contract."""

    def __call__(self, context: PipelineContext, record: JsonDict) -> bool:
        """Decide whether one silver record should flow to Gold."""
        ...


class GoldTransformCallback(Protocol):
    """Silver-to-Gold transformation callback contract."""

    def __call__(self, context: PipelineContext, record: JsonDict) -> JsonDict:
        """Transform one silver record for Gold output."""
        ...
