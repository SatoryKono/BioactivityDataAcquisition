"""
Callback protocols for the pipeline.

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
    """Protocol for transform callback functions."""

    def __call__(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Awaitable[dict[str, Any] | None]: ...


class GoldFilterCallback(Protocol):
    """Protocol for gold layer filter callback functions."""

    def __call__(self, context: PipelineContext, record: dict[str, Any]) -> bool: ...


class TransformerPort(Protocol):
    """Protocol defining the contract for Bronze → Silver transformers.

    All transformer implementations MUST implement this protocol.
    Enables polymorphism and testability through dependency injection.

    Implements RULES.md §2.8 (Bronze → Silver transformation).

    Example:
        >>> class MyTransformer:
        ...     async def transform(
        ...         self, context: PipelineContext, record: BronzeRecord
        ...     ) -> SilverRecord | None:
        ...         # Transform logic here
        ...         return silver_record
    """

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform a Bronze record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from data source.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        Raises:
            ValueError: If record validation fails (handled by Template Method).
        """
        ...
