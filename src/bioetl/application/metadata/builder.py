"""Default implementation of RunMetadataBuilderProtocol.

This module provides a default metadata builder implementation for use
when a container doesn't provide a custom builder.
"""

from __future__ import annotations

from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
    WriteResult,
)
from bioetl.domain.models import RunContext


class DefaultRunMetadataBuilder:
    """Default implementation of RunMetadataBuilderProtocol.

    Provides basic metadata building without external dependencies.
    Used as fallback when container doesn't provide a builder.
    """

    def build_run_metadata(
        self, context: RunContext, write_result: WriteResult
    ) -> dict[str, object]:
        """Build metadata for a completed pipeline run.

        Args:
            context: The run context with pipeline execution details.
            write_result: The result from writing data.

        Returns:
            Dictionary containing run metadata.
        """
        return {
            "run_id": context.run_id,
            "provider": context.provider,
            "entity": context.entity_name,
            "row_count": write_result.row_count,
            "dry_run": False,
        }

    def build_dry_run_metadata(
        self, context: RunContext, row_count: int
    ) -> dict[str, object]:
        """Build metadata for a dry run.

        Args:
            context: The run context with pipeline execution details.
            row_count: Number of rows that would be written.

        Returns:
            Dictionary containing dry run metadata.
        """
        return {
            "run_id": context.run_id,
            "provider": context.provider,
            "entity": context.entity_name,
            "row_count": row_count,
            "dry_run": True,
        }


# Type assertion to ensure DefaultRunMetadataBuilder conforms to protocol
_: RunMetadataBuilderProtocol = DefaultRunMetadataBuilder()

__all__ = ["DefaultRunMetadataBuilder"]
