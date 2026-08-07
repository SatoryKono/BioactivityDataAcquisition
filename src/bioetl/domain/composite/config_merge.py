"""Merge-related composite configuration models."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bioetl.domain.composite.config_validators import _require_non_empty
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

__all__ = [
    "ColumnGroupConfig",
    "MergeConfig",
]


@dataclass(frozen=True, slots=True)
class ColumnGroupConfig:
    """Configuration for a column group in output ordering.

    Defines how columns are grouped and ordered in the merged output.
    Columns can be matched by explicit field names or regex patterns.

    Attributes:
        name: Group name for logging/debugging.
        fields: Explicit list of field names to include in this group.
            Matches both exact field names and prefixed versions
            (e.g., "title" matches "title" and "crossref.title").
        pattern: Regex pattern to match field names.
            Applied after explicit field matching.
        provider_order: Order of providers within this group.
            Seed columns (no prefix) always come first.

    Example:
        >>> group = ColumnGroupConfig(
        ...     name="title",
        ...     fields=("title", "vernacular_title"),
        ...     provider_order=("chembl", "crossref", "openalex"),
        ... )
    """

    name: str
    fields: tuple[str, ...] = ()
    pattern: str | None = None
    provider_order: tuple[str, ...] = (
        "chembl",
        "crossref",
        "openalex",
        "pubmed",
        "semanticscholar",
    )

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.fields, list):
            object.__setattr__(self, "fields", tuple(self.fields))
        if isinstance(self.provider_order, list):
            object.__setattr__(self, "provider_order", tuple(self.provider_order))
        if self.pattern is not None:
            try:
                re.compile(self.pattern)
            except re.error as exc:
                raise ValueError(
                    f"Column group '{self.name}' has invalid pattern: {exc}"
                ) from exc
        self._validate()

    def _validate(self) -> None:
        """Validate configuration invariants."""
        _require_non_empty(self.name, "column group name")
        if not self.fields and not self.pattern:
            raise ValueError(
                f"Column group '{self.name}' must have either fields or pattern"
            )


@dataclass(frozen=True, slots=True)
class MergeConfig:
    """Configuration for merge step.

    Defines how enriched data is combined into a unified output.

    Attributes:
        strategy: Join strategy for merging (left_outer, inner, union).
        conflict_resolution: Strategy for field conflicts.
        output_silver_path: Path for merged Silver table.
        output_gold_path: Path for merged Gold table.
        field_priorities: Mapping of field to source priority list.
            Used with EXPLICIT_RULES conflict resolution.
            Example: {"title": ["chembl", "crossref"]}
        field_mappings: Mapping to rename fields during merge.
            Example: {"crossref_title": "title"}
        exclude_fields: Columns to drop from merged output.
            Supports exact names and glob patterns.
        preserve_all_sources: If True, keep all provider-qualified columns
            for common fields instead of coalescing them. Default: False.
            When enabled, columns like chembl.publication.title and
            crossref.publication.title are both preserved in the output.

    Example:
        >>> config = MergeConfig(
        ...     strategy=MergeStrategy.LEFT_OUTER,
        ...     conflict_resolution=ConflictResolution.SEED_PRIORITY,
        ...     output_silver_path="silver/composite/publication",
        ...     output_gold_path="gold/publication_enriched",
        ...     preserve_all_sources=True,  # Keep all provider columns
        ... )
    """

    strategy: MergeStrategy
    conflict_resolution: ConflictResolution
    output_silver_path: str
    output_gold_path: str
    sort_by_silver: tuple[str, ...] = ()
    sort_by_gold: tuple[str, ...] = ()
    field_priorities: dict[str, tuple[str, ...]] = field(default_factory=dict)
    normalization_compatibility_overrides: dict[str, str] = field(default_factory=dict)
    field_mappings: dict[str, str] = field(default_factory=dict)
    column_groups: tuple[ColumnGroupConfig, ...] = ()
    exclude_fields: tuple[str, ...] = ()
    preserve_all_sources: bool = False

    def __post_init__(self) -> None:
        """Validate and convert types."""
        self._convert_strategy()
        self._convert_conflict_resolution()
        self._convert_sort_policies()
        self._convert_field_priorities()
        self._convert_normalization_compatibility_overrides()
        self._convert_column_groups()
        self._convert_exclude_fields()
        self._validate()

    def _convert_strategy(self) -> None:
        """Convert strategy string to enum if needed."""
        if isinstance(self.strategy, str):
            object.__setattr__(
                self, "strategy", MergeStrategy.from_string(self.strategy)
            )

    def _convert_conflict_resolution(self) -> None:
        """Convert conflict_resolution string to enum if needed."""
        if isinstance(self.conflict_resolution, str):
            object.__setattr__(
                self,
                "conflict_resolution",
                ConflictResolution.from_string(self.conflict_resolution),
            )

    def _convert_field_priorities(self) -> None:
        """Convert list values in field_priorities to tuples."""
        if not self.field_priorities:
            return
        converted = {
            k: tuple(v) if isinstance(v, list) else v
            for k, v in self.field_priorities.items()
        }
        object.__setattr__(self, "field_priorities", converted)

    def _convert_normalization_compatibility_overrides(self) -> None:
        """Convert normalization compatibility override keys and values to strings."""
        if self.normalization_compatibility_overrides:
            object.__setattr__(
                self,
                "normalization_compatibility_overrides",
                {
                    str(key): str(value)
                    for key, value in self.normalization_compatibility_overrides.items()
                },
            )

    def _convert_sort_policies(self) -> None:
        """Convert sort policy lists to tuples for immutability."""
        if isinstance(self.sort_by_silver, list):
            object.__setattr__(self, "sort_by_silver", tuple(self.sort_by_silver))
        if isinstance(self.sort_by_gold, list):
            object.__setattr__(self, "sort_by_gold", tuple(self.sort_by_gold))

    def _convert_column_groups(self) -> None:
        """Convert list/tuple of column groups to tuple of ColumnGroupConfig."""
        if isinstance(self.column_groups, list | tuple):
            converted = tuple(
                ColumnGroupConfig(**g) if isinstance(g, dict) else g
                for g in self.column_groups
            )
            object.__setattr__(self, "column_groups", converted)

    def _convert_exclude_fields(self) -> None:
        """Convert list/tuple of exclude_fields to tuple."""
        if isinstance(self.exclude_fields, list | tuple):
            object.__setattr__(self, "exclude_fields", tuple(self.exclude_fields))

    def _validate(self) -> None:
        """Validate configuration invariants."""
        if not self.output_silver_path:
            raise ValueError("merge output_silver_path cannot be empty")
        if not self.output_gold_path:
            raise ValueError("merge output_gold_path cannot be empty")
        self._validate_sort_policy("sort_by_silver", self.sort_by_silver)
        self._validate_sort_policy("sort_by_gold", self.sort_by_gold)
        if (
            self.conflict_resolution == ConflictResolution.EXPLICIT_RULES
            and not self.field_priorities
        ):
            raise ValueError(
                "field_priorities required when using EXPLICIT_RULES conflict resolution"
            )

    @staticmethod
    def _validate_sort_policy(field_name: str, columns: tuple[str, ...]) -> None:
        """Validate deterministic sort policy columns."""
        normalized = tuple(column.strip() for column in columns)
        if any(not column for column in normalized):
            raise ValueError(f"{field_name} must not contain empty column names")
        if len(normalized) != len(set(normalized)):
            raise ValueError(f"{field_name} must not contain duplicate columns")

    def get_field_priority(self, field_name: str) -> tuple[str, ...] | None:
        """Get source priority order for a field.

        Args:
            field_name: Name of the field.

        Returns:
            Tuple of source names in priority order, or None if not configured.
        """
        return self.field_priorities.get(field_name)

    def allows_normalization_compatibility_override(self, field_name: str) -> bool:
        """Return whether one field declares an explicit compatibility override."""
        return field_name in self.normalization_compatibility_overrides
