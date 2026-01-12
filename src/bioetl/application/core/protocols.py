"""Callback protocols for the pipeline.

Defines Protocol classes for pipeline callbacks and transformer ports.
Implements RULES.md §1 (Domain Layer - Ports).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from bioetl.domain.context import PipelineContext


class TransformCallback(Protocol):
    """Bronze to Silver transformation callback."""

    def __call__(
        self, context: PipelineContext, record: dict[str, Any], index: int
    ) -> Awaitable[dict[str, Any] | None]:
        """Execute transformation."""
        ...


class GoldFilterCallback(Protocol):
    """Filter callback to determine if Silver record should go to Gold."""

    def __call__(self, context: PipelineContext, record: dict[str, Any]) -> bool:
        """Evaluate if record should be included in Gold layer."""
        ...


class GoldTransformCallback(Protocol):
    """Silver to Gold transformation callback.

    Removes JSON string fields and prepares record for Gold layer.
    """

    def __call__(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute transformation."""
        ...
