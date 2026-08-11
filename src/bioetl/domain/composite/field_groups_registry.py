"""Field group registry and query helpers."""

from __future__ import annotations

from bioetl.domain.composite.field_groups_models import (
    DEFAULT_PROVIDER_ORDER,
    FieldGroupDefinition,
    FieldGroupId,
    FieldMapping,
)

__all__ = [
    "FieldGroupRegistry",
    "build_field_group_registry",
]


class FieldGroupRegistry:
    """Registry for lookup, filtering and ordering by semantic field groups."""

    def __init__(
        self,
        groups: tuple[FieldGroupDefinition, ...],
        provider_order: tuple[str, ...] = DEFAULT_PROVIDER_ORDER,
        default_group: FieldGroupId = FieldGroupId.TRASH,
    ) -> None:
        """Build lookup indices for field-group operations."""
        self._groups = groups
        self._provider_order = provider_order
        self._default_group = default_group
        self._field_to_group: dict[str, FieldGroupId] = {}
        self._column_to_group: dict[str, FieldGroupId] = {}
        self._field_to_mapping: dict[str, FieldMapping] = {}
        self._group_to_def: dict[FieldGroupId, FieldGroupDefinition] = {}
        self._group_rank: dict[FieldGroupId, int] = {
            group: index for index, group in enumerate(FieldGroupId)
        }

        for group_def in groups:
            self._group_to_def[group_def.group_id] = group_def
            for fm in group_def.fields:
                self._register_field_mapping(group_def.group_id, fm)

    def _register_field_mapping(self, group_id: object, fm: object) -> None:
        """Register one field mapping; reject duplicate base/column keys."""
        base_key = fm.base_name.lower()
        if base_key in self._field_to_group:
            existing = self._field_to_group[base_key]
            raise ValueError(
                f"Duplicate field-group base_name {fm.base_name!r}: "
                f"already mapped to {existing.value}, "
                f"also declared in {group_id.value}"
            )
        self._field_to_group[base_key] = group_id
        self._field_to_mapping[base_key] = fm
        for col in fm.provider_columns:
            self._register_provider_column(group_id, col)

    def _register_provider_column(self, group_id: object, col: str) -> None:
        col_key = col.lower()
        if col_key in self._column_to_group:
            existing = self._column_to_group[col_key]
            raise ValueError(
                f"Duplicate provider column {col!r}: "
                f"already mapped to {existing.value}, "
                f"also declared in {group_id.value}"
            )
        self._column_to_group[col_key] = group_id

    @property
    def groups(self) -> tuple[FieldGroupDefinition, ...]:
        """All group definitions."""
        return self._groups

    @property
    def provider_order(self) -> tuple[str, ...]:
        """Provider priority order."""
        return self._provider_order

    @property
    def field_count(self) -> int:
        """Total number of mapped base fields."""
        return len(self._field_to_group)

    @property
    def column_count(self) -> int:
        """Total number of mapped provider columns."""
        return len(self._column_to_group)

    def get_group(self, column: str) -> FieldGroupId:
        """Get semantic group for a column or field name.

        Args:
            column: Column name (qualified as 'provider.entity.field' or unqualified).

        Returns:
            FieldGroupId for the column, or the default group if unmapped.
        """
        col_lower = column.lower()
        if col_lower in self._column_to_group:
            return self._column_to_group[col_lower]
        field_name = self._extract_field(column)
        return self._field_to_group.get(field_name, self._default_group)

    def get_field_mapping(self, base_name: str) -> FieldMapping | None:
        """Get FieldMapping for a base field name.

        Args:
            base_name: Unqualified base field name to look up.

        Returns:
            FieldMapping for the field, or None if the field is not registered.
        """
        return self._field_to_mapping.get(base_name.lower())

    def get_group_definition(
        self, group_id: FieldGroupId
    ) -> FieldGroupDefinition | None:
        """Get FieldGroupDefinition for a group ID.

        Args:
            group_id: Semantic group identifier to look up.

        Returns:
            FieldGroupDefinition for the group, or None if not registered.
        """
        return self._group_to_def.get(group_id)

    def is_gold_field(self, column: str) -> bool:
        """Check if a column should be included in Gold layer.

        Args:
            column: Column name (qualified or unqualified) to check.

        Returns:
            True if the column's semantic group is marked for Gold inclusion.
            Prefers loaded ``FieldGroupDefinition.include_in_gold`` so custom
            registry overrides are respected; falls back to enum metadata.
        """
        group = self.get_group(column)
        definition = self._group_to_def.get(group)
        if definition is not None:
            return definition.include_in_gold
        return group.include_in_gold

    def get_gold_columns(self, columns: list[str]) -> list[str]:
        """Filter columns to only those included in Gold layer.

        Args:
            columns: List of column names to filter.

        Returns:
            Subset of columns that belong to Gold-eligible groups or are system columns.
        """
        return [c for c in columns if c.startswith("_") or self.is_gold_field(c)]

    def get_trash_columns(self, columns: list[str]) -> list[str]:
        """Get columns that would be excluded from Gold layer.

        Args:
            columns: List of column names to filter.

        Returns:
            Subset of columns that are not Gold-eligible and not system columns.
        """
        return [
            c for c in columns if not c.startswith("_") and not self.is_gold_field(c)
        ]

    def get_columns_by_group(
        self, columns: list[str], group: FieldGroupId
    ) -> list[str]:
        """Get columns belonging to a specific group.

        Args:
            columns: List of column names to filter.
            group: Semantic group ID to filter by.

        Returns:
            List of columns whose semantic group matches the given group ID.
        """
        return [c for c in columns if self.get_group(c) == group]

    def get_ordered_columns(self, columns: list[str]) -> list[str]:
        """Sort columns by semantic group and provider priority.

        Args:
            columns: List of column names to sort.

        Returns:
            Columns sorted by group order then provider priority, with system columns appended last.
        """
        system_cols = [c for c in columns if c.startswith("_")]
        data_cols = [c for c in columns if not c.startswith("_")]
        fallback_rank = len(self._group_rank)

        def sort_key(column: str) -> tuple[int, int, str]:
            group = self.get_group(column)
            group_idx = self._group_rank.get(group, fallback_rank)
            provider_rank = self._get_provider_rank(column)
            field_name = self._extract_field(column)
            return (group_idx, provider_rank, field_name)

        sorted_data = sorted(data_cols, key=sort_key)
        return sorted_data + sorted(system_cols)

    def validate_columns(self, columns: list[str]) -> dict[str, list[str]]:
        """Validate columns against the registry.

        Args:
            columns: List of column names to classify against the registry.

        Returns:
            Dictionary with keys 'mapped', 'unmapped', and 'system' listing columns by classification.
        """
        mapped: list[str] = []
        unmapped: list[str] = []
        system: list[str] = []

        for col in columns:
            if col.startswith("_"):
                system.append(col)
            elif self.get_group(col) != self._default_group:
                mapped.append(col)
            else:
                field_name = self._extract_field(col)
                if field_name in self._field_to_group:
                    mapped.append(col)
                else:
                    unmapped.append(col)
        return {"mapped": mapped, "unmapped": unmapped, "system": system}

    def _get_provider_rank(self, column: str) -> int:
        """Get provider rank for ordering within semantic group."""
        parts = column.split(".")
        if len(parts) == 3:
            provider = parts[0].lower()
            try:
                return self._provider_order.index(provider)
            except ValueError:
                return 999
        return -1

    @staticmethod
    def _extract_field(column: str) -> str:
        """Extract base field name from column (qualified or unqualified)."""
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2].lower()
        return column.lower()


def build_field_group_registry(
    groups: tuple[FieldGroupDefinition, ...],
    provider_order: tuple[str, ...] = DEFAULT_PROVIDER_ORDER,
    default_group: FieldGroupId = FieldGroupId.TRASH,
) -> FieldGroupRegistry:
    """Factory function to create a FieldGroupRegistry.

    Args:
        groups: Tuple of FieldGroupDefinition instances defining the semantic groups.
        provider_order: Ordered tuple of provider names for column priority. Defaults to DEFAULT_PROVIDER_ORDER.
        default_group: Fallback group for unregistered columns. Defaults to TRASH.

    Returns:
        Configured FieldGroupRegistry instance.
    """
    return FieldGroupRegistry(
        groups=groups,
        provider_order=provider_order,
        default_group=default_group,
    )
