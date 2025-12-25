"""Gold Transformer Protocol.

Defines the contract for transforming Silver records to Gold records.
"""

from typing import Any, Protocol

from bioetl.domain.context import PipelineContext


class GoldTransformerPort(Protocol):
    """Protocol for transforming Silver records to Gold records.

    Handles:
    1. Filtering (should_process)
    2. Transformation (transform)
    """

    def should_process(
        self, context: PipelineContext, silver_record: dict[str, Any]
    ) -> bool:
        """Determine if a Silver record should be processed for Gold layer."""
        ...

    def transform(
        self, context: PipelineContext, silver_record: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform a Silver record to Gold format."""
        ...
