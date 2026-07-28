"""Application-layer callback and transformer protocols.

These structural protocols model internal pipeline callbacks and transformer
contracts. They are intentionally application-local helpers, not domain-layer
ports from ``bioetl.domain.ports``.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = [
    "GoldFilterCallback",
    "GoldTransformCallback",
    "TransformCallback",
    "TransformerProtocol",
]

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from bioetl.application.core.pre_silver_record import PreSilverRecord
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord

class TransformCallback(Protocol):
    """Bronze to Silver transformation callback."""

    def __call__(
        self,
        context: PipelineContext,
        record: JsonDict,  # Any: values are heterogeneous
        index: int,  # Any: values are heterogeneous
    ) -> Awaitable[JsonDict | PreSilverRecord | None]:  # Any: values are heterogeneous
        """Execute transformation."""
        ...

class GoldFilterCallback(Protocol):
    """Filter callback to determine if Silver record should go to Gold."""

    def __call__(
        self,
        context: PipelineContext,
        record: JsonDict,  # Any: values are heterogeneous
    ) -> bool:  # Any: values are heterogeneous
        """Evaluate if record should be included in Gold layer."""
        ...

class GoldTransformCallback(Protocol):
    """Silver to Gold transformation callback.

    Removes JSON string fields and prepares record for Gold layer.
    """

    def __call__(
        self,
        context: PipelineContext,
        record: JsonDict,  # Any: values are heterogeneous
    ) -> JsonDict:  # Any: values are heterogeneous
        """Execute transformation."""
        ...

class TransformerProtocol(Protocol):
    """Application-level contract for Bronze → Silver transformers.

    Transformer implementations satisfy this protocol to enable polymorphism and
    dependency injection within the application layer. Cross-layer ports remain
    defined in ``bioetl.domain.ports``.

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
    ) -> SilverRecord | PreSilverRecord | None:
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
