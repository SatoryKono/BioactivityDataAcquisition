"""Context building utilities for ETL pipelines.

This module provides the ContextBuilder class that handles creation
and normalization of run contexts and metadata.

Extracted from PipelineBase to reduce class size and improve separation
of concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.domain.models import RunContext
from bioetl.domain.providers import ProviderId
from bioetl.domain.value_objects import EntityName

if TYPE_CHECKING:
    from bioetl.domain.configs import PipelineConfig


class ContextBuilder:
    """Builds and normalizes pipeline run contexts.

    Encapsulates the logic for creating RunContext instances and
    normalizing metadata dictionaries.
    """

    def __init__(
        self,
        config: PipelineConfig,
        provider_id: ProviderId,
    ) -> None:
        """Initialize context builder.

        Args:
            config: Pipeline configuration.
            provider_id: Provider identifier.
        """
        self._config = config
        self._provider_id = provider_id

    def build_context(self, dry_run: bool) -> RunContext:
        """Build a new run context.

        Args:
            dry_run: Whether this is a dry run.

        Returns:
            New RunContext instance.
        """
        return RunContext(
            entity_name=EntityName(self._config.entity_name),
            provider=self._provider_id,
            config=self._config.model_dump(),
            dry_run=dry_run,
        )

    def normalize_meta(
        self,
        meta: dict[str, Any],
        context: RunContext,
        row_count: int,
        dry_run: bool,
    ) -> dict[str, Any]:
        """Normalize metadata ensuring required fields are present.

        Args:
            meta: Raw metadata from builder.
            context: Run context.
            row_count: Number of rows processed.
            dry_run: Whether this is a dry run.

        Returns:
            Normalized metadata dictionary.

        Raises:
            TypeError: If meta is not a dict.
        """
        if not isinstance(meta, dict):
            raise TypeError("Metadata builder must return a dict.")

        normalized_meta = dict(meta)
        normalized_meta.setdefault("run_id", context.run_id)
        normalized_meta.setdefault("provider", context.provider)
        normalized_meta.setdefault("entity", context.entity_name)
        normalized_meta.setdefault("row_count", row_count)
        if dry_run:
            normalized_meta["dry_run"] = True
        else:
            normalized_meta.setdefault("dry_run", False)

        return normalized_meta


__all__ = ["ContextBuilder"]
