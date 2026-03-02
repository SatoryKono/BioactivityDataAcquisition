"""Callback protocols for the pipeline.

Defines Protocol classes for pipeline callbacks and transformer ports.
Implements RULES.md §1 (Domain Layer - Ports).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


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


class TransformerPort(Protocol):
    """Protocol defining the contract for Bronze → Silver transformers.

    All transformer implementations MUST implement this protocol.
    Enables polymorphism and testability through dependency injection.

    Implements RULES.md §2.8 (Bronze → Silver transformation).

    Example:
        >>> class MyTransformer:
        ...     async def transform(
        ...         self, context: PipelineContext, record: BronzeRecord, index: int
        ...     ) -> SilverRecord | None:
        ...         # Transform logic here
        ...         return silver_record

    """

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform a Bronze record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from data source.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        Raises:
            ValueError: If record validation fails (handled by Template Method).

        """
        ...
