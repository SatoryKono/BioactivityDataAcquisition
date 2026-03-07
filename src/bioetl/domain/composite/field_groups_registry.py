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

        for group_def in groups:
            self._group_to_def[group_def.group_id] = group_def
            for fm in group_def.fields:
                self._field_to_group[fm.base_name.lower()] = fm.group
                self._field_to_mapping[fm.base_name.lower()] = fm
                for col in fm.provider_columns:
                    self._column_to_group[col.lower()] = fm.group

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
        """Get semantic group for a column or field name."""
        col_lower = column.lower()
        if col_lower in self._column_to_group:
            return self._column_to_group[col_lower]
        field_name = self._extract_field(column)
        return self._field_to_group.get(field_name, self._default_group)

    def get_field_mapping(self, base_name: str) -> FieldMapping | None:
        """Get FieldMapping for a base field name."""
        return self._field_to_mapping.get(base_name.lower())

    def get_group_definition(
        self, group_id: FieldGroupId
    ) -> FieldGroupDefinition | None:
        """Get FieldGroupDefinition for a group ID."""
        return self._group_to_def.get(group_id)

    def is_gold_field(self, column: str) -> bool:
        """Check if a column should be included in Gold layer."""
        return self.get_group(column).include_in_gold

    def get_gold_columns(self, columns: list[str]) -> list[str]:
        """Filter columns to only those included in Gold layer."""
        return [c for c in columns if c.startswith("_") or self.is_gold_field(c)]

    def get_trash_columns(self, columns: list[str]) -> list[str]:
        """Get columns that would be excluded from Gold layer."""
        return [
            c for c in columns if not c.startswith("_") and not self.is_gold_field(c)
        ]

    def get_columns_by_group(
        self, columns: list[str], group: FieldGroupId
    ) -> list[str]:
        """Get columns belonging to a specific group."""
        return [c for c in columns if self.get_group(c) == group]

    def get_ordered_columns(self, columns: list[str]) -> list[str]:
        """Sort columns by semantic group and provider priority."""
        system_cols = [c for c in columns if c.startswith("_")]
        data_cols = [c for c in columns if not c.startswith("_")]
        group_order = list(FieldGroupId)

        def sort_key(column: str) -> tuple[int, int, str]:
            group = self.get_group(column)
            try:
                group_idx = group_order.index(group)
            except ValueError:
                group_idx = len(group_order)
            provider_rank = self._get_provider_rank(column)
            field_name = self._extract_field(column)
            return (group_idx, provider_rank, field_name)

        sorted_data = sorted(data_cols, key=sort_key)
        return sorted_data + sorted(system_cols)

    def validate_columns(self, columns: list[str]) -> dict[str, list[str]]:
        """Validate columns against the registry."""
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
    """Factory function to create a FieldGroupRegistry."""
    return FieldGroupRegistry(
        groups=groups,
        provider_order=provider_order,
        default_group=default_group,
    )
