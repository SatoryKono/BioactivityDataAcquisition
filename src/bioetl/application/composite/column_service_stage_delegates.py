"""Static column-service delegates kept off the ordering service module."""

from __future__ import annotations

from bioetl.application.composite.column_orderer_group_flow import apply_renames
from bioetl.application.composite.column_priority_orderer import get_enricher_prefix
from bioetl.application.composite.join_planner_helpers import parse_pipeline_name

__all__ = ["ColumnOrderStageDelegates"]


class ColumnOrderStageDelegates:
    """Rename, enricher-prefix, and pipeline-name helpers for column ordering."""

    @staticmethod
    def _apply_renames_stage(
        columns: list[str],
        rename_map: dict[str, str],
    ) -> list[str]:
        """Delegate legacy service-level rename calls to the focused helper."""
        return apply_renames(columns, rename_map)

    @staticmethod
    def get_enricher_prefix(enricher_pipeline: str) -> str:
        """Get enricher prefix with trailing separator."""
        return get_enricher_prefix(enricher_pipeline)

    @staticmethod
    def _parse_pipeline_name(pipeline: str) -> tuple[str, str]:
        """Parse provider_entity pipeline name into tuple."""
        return parse_pipeline_name(pipeline)
