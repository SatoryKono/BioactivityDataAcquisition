"""Column orderer service for composite pipelines.

Orders columns by semantic groups for consistent output.
See ADR-026 for rationale.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.application.core.publication_aliases import (
    LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE,
    PUBLICATION_SCHEMA_FIELD_ALIASES,
)
from bioetl.domain.schemas.column_order import DQ_FIELDS_SUFFIX
from bioetl.domain.value_objects.column_order import (
    DEFAULT_COLUMN_ORDER,
    ColumnOrderConfig,
    SemanticGroup,
)
from bioetl.domain.value_objects.column_qualifier import ColumnQualifier

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from bioetl.domain.composite.config import ColumnGroupConfig, LayerColumnConfig
    from bioetl.domain.ports import LoggerPort

    _SortFn = Callable[[list[str], tuple[str, ...]], list[str]]

__all__ = ["ColumnOrdererService"]


def _collect_pattern_columns(
    available: set[str],
    used: set[str],
    group: ColumnGroupConfig,
    sort_fn: _SortFn,
    logger: LoggerPort,
) -> list[str]:
    """Collect columns matching a group regex pattern.

    Args:
        available: Set of available column names.
        used: Set of already-matched column names (mutated in-place).
        group: Column group configuration with optional pattern.
        sort_fn: Provider-sorting callable.
        logger: Logger for warnings on invalid patterns.

    Returns:
        Sorted list of pattern-matched columns not already in *used*.
    """
    if not group.pattern:
        return []
    try:
        pattern_re = re.compile(group.pattern, re.IGNORECASE)
    except re.error as e:
        logger.warning(
            "Invalid regex pattern in column group",
            group=group.name,
            pattern=group.pattern,
            error=str(e),
        )
        return []

    pattern_matches: list[str] = []
    for col in available:
        if col not in used and pattern_re.search(col):
            pattern_matches.append(col)
            used.add(col)
    return sort_fn(pattern_matches, group.provider_order)


class ColumnOrdererService:
    """Service for ordering columns by semantic groups.

    Orders DataFrame columns in a consistent, semantically meaningful way:
    1. System fields (entity_id, _run_id, ...)
    2. Identifiers (doi, pmid, ...)
    3. Title fields
    4. Abstract fields
    5. Authors fields
    6. Journal/Source fields
    7. Date fields
    8. Metrics fields
    9. Classification fields
    10. URL fields
    11. Other fields

    Within each group, columns are ordered by:
    - Provider priority (chembl first, then crossref, etc.)
    - Alphabetically for same provider

    Example:
        >>> orderer = ColumnOrdererService(logger)
        >>> result = orderer.order_columns(df)
        >>> result.columns[:5]
        ['entity_id', '_run_id', 'doi', 'pmid', 'chembl.publication.title']
    """

    def __init__(
        self,
        logger: LoggerPort,
        config: ColumnOrderConfig | None = None,
        column_groups: Sequence[ColumnGroupConfig] | None = None,
    ) -> None:
        """Initialize orderer.

        Args:
            logger: Logger port for diagnostics.
            config: Column order configuration. Uses DEFAULT_COLUMN_ORDER if None.
            column_groups: Optional YAML-based column group configuration.
                If provided, takes precedence over config.
        """
        self._logger = logger
        self._config = config or DEFAULT_COLUMN_ORDER
        self._column_groups = tuple(column_groups) if column_groups else None
        self._warned_legacy_aliases: set[str] = set()

    def order_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Order DataFrame columns by semantic groups.

        If column_groups were provided in constructor, uses YAML-based ordering.
        Otherwise falls back to hardcoded ColumnOrderConfig.

        Args:
            df: DataFrame to reorder.

        Returns:
            DataFrame with columns in semantic order.
        """
        if not df.columns:
            return df

        # Use YAML-based column groups if available
        if self._column_groups:
            ordered = self._order_by_yaml_groups(df.columns)
            self._logger.debug(
                "Ordered columns by YAML groups",
                total_columns=len(ordered),
                groups_configured=len(self._column_groups),
            )
        else:
            ordered = self.get_ordered_columns(df.columns)
            self._logger.debug(
                "Ordered columns by semantic groups",
                total_columns=len(ordered),
                groups_used=self._count_groups(ordered),
            )

        return df.select(ordered)

    def order_column_names(self, columns: Sequence[str]) -> list[str]:
        """Order column names by semantic groups.

        Uses YAML-based column groups when configured, otherwise falls back
        to the default semantic ordering.

        Args:
            columns: List of column names.

        Returns:
            Ordered result.
        """
        if not columns:
            return []

        if self._column_groups:
            return self._order_by_yaml_groups(columns)

        return self.get_ordered_columns(columns)

    def get_ordered_columns(self, columns: Sequence[str]) -> list[str]:
        """Get columns in semantic order.

        Args:
            columns: Column names to order.

        Returns:
            Ordered list of column names.
        """

        # Create sort key for each column
        def sort_key(col: str) -> tuple[int, int, str]:
            """Sort by (group, provider_rank, column_name).

            Args:
                col: Col.

            Returns:
                Sort key value for ordering.
            """
            group = self._config.get_group(col)
            provider_rank = self._config.get_provider_rank(col)
            # For alphabetical sort, use field name (not full qualified name)
            field_name = ColumnQualifier.extract_field(col)
            return (group.value, provider_rank, field_name.lower())

        return sorted(columns, key=sort_key)

    def _count_groups(self, columns: Sequence[str]) -> dict[str, int]:
        """Count columns per semantic group.

        Args:
            columns: Ordered column names.

        Returns:
            Dict mapping group name to column count.
        """
        counts: dict[str, int] = {}
        for col in columns:
            group = self._config.get_group(col)
            group_name = group.name
            counts[group_name] = counts.get(group_name, 0) + 1
        return counts

    def group_columns(self, columns: Sequence[str]) -> dict[SemanticGroup, list[str]]:
        """Group columns by semantic type.

        Useful for debugging and documentation.

        Args:
            columns: Column names to group.

        Returns:
            Dict mapping SemanticGroup to list of columns.
        """
        groups: dict[SemanticGroup, list[str]] = {}

        for col in columns:
            group = self._config.get_group(col)
            if group not in groups:
                groups[group] = []
            groups[group].append(col)

        # Sort columns within each group
        for group in groups:
            groups[group] = sorted(
                groups[group],
                key=lambda c: (
                    self._config.get_provider_rank(c),
                    ColumnQualifier.extract_field(c).lower(),
                ),
            )

        return groups

    # === YAML-based column ordering methods ===

    def _order_by_yaml_groups(self, columns: Sequence[str]) -> list[str]:
        """Order columns using YAML-configured groups.

        Args:
            columns: Column names to order.

        Returns:
            Ordered list of column names.
        """
        if not self._column_groups:
            return list(columns)

        all_columns = set(columns)
        ordered_columns: list[str] = []
        used_columns: set[str] = set()

        for group in self._column_groups:
            group_columns = self._collect_group_columns(
                all_columns - used_columns,
                group,
            )
            ordered_columns.extend(group_columns)
            used_columns.update(group_columns)

        # Add remaining columns at the end (alphabetically),
        # excluding DQ suffix fields which must come last
        dq_suffix_set = frozenset(DQ_FIELDS_SUFFIX)
        remaining = sorted(all_columns - used_columns - dq_suffix_set)
        if remaining:
            ordered_columns.extend(remaining)
            self._logger.debug(
                "Ungrouped columns added at end",
                count=len(remaining),
                sample=remaining[:5],
            )

        # DQ suffix fields MUST be last (DQ_FIELDS_SUFFIX convention)
        # Remove any DQ fields that may have been captured by groups earlier
        for dq_field in DQ_FIELDS_SUFFIX:
            if dq_field in ordered_columns:
                ordered_columns.remove(dq_field)

        # Re-append DQ fields at the very end, preserving DQ_FIELDS_SUFFIX order
        for dq_field in DQ_FIELDS_SUFFIX:
            if dq_field in all_columns:
                ordered_columns.append(dq_field)

        return ordered_columns

    def _collect_group_columns(
        self,
        available: set[str],
        group: ColumnGroupConfig,
    ) -> list[str]:
        """Collect columns for a group, preserving field order from config.

        Fields are emitted in the order they appear in ``group.fields``.
        Within each field, provider-qualified columns are sorted by
        ``group.provider_order``.  Pattern-matched columns that were not
        already captured by explicit field names are appended at the end.

        Args:
            available: Set of available column names.
            group: Column group configuration.

        Returns:
            Ordered list of columns for this group.
        """
        ordered: list[str] = []
        used: set[str] = set()

        # Match by explicit field names, preserving field order
        for field_name in group.fields:
            field_matches: list[str] = []
            aliases = self._field_aliases(field_name)
            for col in available:
                if col in used:
                    continue
                extracted = self._extract_field_from_qualified(col)
                if extracted in aliases or col in aliases:
                    field_matches.append(col)
                    used.add(col)
            ordered.extend(self._sort_by_provider(field_matches, group.provider_order))

        # Match by pattern (appended after explicit fields)
        ordered.extend(
            _collect_pattern_columns(
                available, used, group, self._sort_by_provider, self._logger
            )
        )

        return ordered

    def _sort_by_provider(
        self,
        columns: list[str],
        provider_order: tuple[str, ...],
    ) -> list[str]:
        """Sort columns by provider prefix order.

        Seed columns (no dots) come first, then by provider order.

        Args:
            columns: List of column names.
            provider_order: Tuple of provider names in desired order.

        Returns:
            Sorted list of columns.
        """

        def sort_key(col: str) -> tuple[int, str]:
            """Return (provider_index, name) placing seed columns first.

            Args:
                col: Col.

            Returns:
                Sort key value for ordering.
            """
            # Seed columns (no dot or single dot like 'field.A') come first
            parts = col.split(".")
            if len(parts) < 3:
                return (0, col.lower())

            # Extract provider from qualified name (provider.entity.field)
            provider = parts[0].lower()
            try:
                idx = provider_order.index(provider)
                return (idx + 1, col.lower())
            except ValueError:
                # Unknown provider - at the end
                return (len(provider_order) + 1, col.lower())

        return sorted(columns, key=sort_key)

    def _extract_field_from_qualified(self, column: str) -> str:
        """Extract field name from qualified column name.

        Args:
            column: Column name (qualified or unqualified).

        Returns:
            Field name (last part of qualified name, or full name if unqualified).
        """
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2]  # provider.entity.field -> field
        if len(parts) == 2:
            return parts[1]  # field.A -> A (conflict suffix) - keep original
        return column

    def _field_aliases(self, field_name: str) -> set[str]:
        """Return compatibility aliases for evolving field names."""
        aliases = {field_name}
        legacy_to_unified = PUBLICATION_SCHEMA_FIELD_ALIASES

        if field_name in legacy_to_unified:
            aliases.add(legacy_to_unified[field_name])
            if field_name not in self._warned_legacy_aliases:
                self._logger.warning(
                    "Legacy publication field alias used on read path",
                    legacy_field=field_name,
                    canonical_field=legacy_to_unified[field_name],
                    deprecation_cutoff_date=LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE,
                )
                self._warned_legacy_aliases.add(field_name)

        # Allow reverse matching when config already uses canonical names.
        for legacy, unified in legacy_to_unified.items():
            if field_name == unified:
                aliases.add(legacy)

        return aliases

    def filter_by_layer_config(
        self,
        columns: Sequence[str],
        layer_config: LayerColumnConfig,
    ) -> list[str]:
        """Filter columns by layer-specific configuration.

        Supports three filtering modes:
        1. Explicit column list (layer_config.columns)
        2. Group-based filtering (layer_config.include_groups + exclude_fields)
        3. Layer-specific groups (layer_config.column_groups)

        Also applies rename_fields mapping if specified.

        Args:
            columns: Available columns to filter.
            layer_config: Layer-specific column configuration.

        Returns:
            Filtered list of columns in semantic order (with renames applied).
        """
        from fnmatch import fnmatch

        # Mode 1: Explicit column list
        if layer_config.columns:
            # Return columns in specified order, keeping only those available
            filtered = [c for c in layer_config.columns if c in columns]
            return self._apply_renames(filtered, layer_config.rename_fields)

        # Mode 2: Group-based filtering
        if layer_config.include_groups:
            if not self._column_groups:
                self._logger.warning(
                    "include_groups specified but no column_groups configured",
                    include_groups=layer_config.include_groups,
                )
                return list(columns)

            # Filter groups by include_groups
            included_groups = [
                g for g in self._column_groups if g.name in layer_config.include_groups
            ]

            # Match columns to included groups
            all_cols = set(columns)
            matched: set[str] = set()
            for group in included_groups:
                group_columns = self._collect_group_columns(all_cols - matched, group)
                matched.update(group_columns)

            # Apply exclude_fields filter
            if layer_config.exclude_fields:
                matched = {
                    c
                    for c in matched
                    if not any(
                        fnmatch(c, pattern) for pattern in layer_config.exclude_fields
                    )
                }

            # Order by semantic groups
            ordered = self._order_by_yaml_groups(list(matched))
            return self._apply_renames(ordered, layer_config.rename_fields)

        # Mode 3: Layer-specific groups (handled by caller via constructor)
        # If we reach here, no filtering is needed
        return list(columns)

    def _apply_renames(
        self, columns: list[str], rename_map: dict[str, str]
    ) -> list[str]:
        """Apply column renames from rename_fields mapping.

        Args:
            columns: List of column names to rename.
            rename_map: Mapping of old_name -> new_name.

        Returns:
            List of columns with renames applied.
        """
        if not rename_map:
            return columns

        return [rename_map.get(col, col) for col in columns]
