"""Filter and maintenance context objects."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "InputFilterContext",
    "VacuumSettings",
]


@dataclass(frozen=True, slots=True)
class InputFilterContext:
    """Input filter configuration for CSV-based or direct ID filtering."""

    enabled: bool
    source_path: str
    column_name: str
    filter_field: str
    filter_ids: tuple[str, ...] | None = None
    multi_filter_ids: dict[str, tuple[str, ...]] | None = None
    valid_combinations: frozenset[tuple[str, ...]] | None = None
    fallback_mapping: dict[str, str] | None = None
    fallback_column: str | None = None

    @classmethod
    def disabled(cls) -> InputFilterContext:
        """Create a disabled filter context."""
        return cls(
            enabled=False,
            source_path="",
            column_name="",
            filter_field="",
            filter_ids=None,
            multi_filter_ids=None,
            valid_combinations=None,
            fallback_mapping=None,
            fallback_column=None,
        )

    @classmethod
    def from_csv(
        cls,
        source_path: str,
        column_name: str,
        filter_field: str,
        fallback_column: str | None = None,
    ) -> InputFilterContext:
        """Create an enabled filter context from CSV parameters.

        Args:
            source_path: File system path to the CSV file containing filter IDs.
            column_name: Column in the CSV that holds the ID values.
            filter_field: Record field name to match against the CSV IDs.
            fallback_column: Optional alternative CSV column used as a secondary lookup.

        Returns:
            InputFilterContext with enabled=True and CSV-based filter settings.
        """
        return cls(
            enabled=True,
            source_path=source_path,
            column_name=column_name,
            filter_field=filter_field,
            filter_ids=None,
            multi_filter_ids=None,
            valid_combinations=None,
            fallback_mapping=None,
            fallback_column=fallback_column,
        )

    @classmethod
    def from_ids(
        cls,
        filter_ids: tuple[str, ...],
        filter_field: str,
        fallback_mapping: dict[str, str] | None = None,
    ) -> InputFilterContext:
        """Create an enabled filter context from direct IDs.

        Args:
            filter_ids: Tuple of ID strings to filter records by.
            filter_field: Record field name to match against the provided IDs.
            fallback_mapping: Optional dict mapping primary IDs to alternative IDs
                for secondary lookup. Defaults to None.

        Returns:
            InputFilterContext with enabled=True and direct ID filter settings.
        """
        return cls(
            enabled=True,
            source_path="",
            column_name="",
            filter_field=filter_field,
            filter_ids=filter_ids,
            multi_filter_ids=None,
            valid_combinations=None,
            fallback_mapping=fallback_mapping,
            fallback_column=None,
        )

    @classmethod
    def from_multi_ids(
        cls,
        multi_filter_ids: dict[str, tuple[str, ...]],
        valid_combinations: frozenset[tuple[str, ...]] | None = None,
    ) -> InputFilterContext:
        """Create an enabled filter context from multi-field IDs.

        Args:
            multi_filter_ids: Mapping from field name to a tuple of allowed values for that field.
            valid_combinations: Optional frozenset of allowed (field_value, ...) tuples restricting
                multi-field matches. Defaults to None (all combinations allowed).

        Returns:
            InputFilterContext with enabled=True and multi-field ID filter settings.
        """
        fields = list(multi_filter_ids.keys())
        return cls(
            enabled=True,
            source_path="",
            column_name="",
            filter_field=fields[0] if fields else "",
            filter_ids=None,
            multi_filter_ids=multi_filter_ids,
            valid_combinations=valid_combinations,
            fallback_mapping=None,
            fallback_column=None,
        )

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        if self.multi_filter_ids is not None:
            object.__setattr__(
                self,
                "multi_filter_ids",
                {
                    key: tuple(values)
                    for key, values in self.multi_filter_ids.items()
                },
            )
        if self.fallback_mapping is not None:
            object.__setattr__(self, "fallback_mapping", dict(self.fallback_mapping))
        if not self.enabled:
            return
        if self.multi_filter_ids is not None:
            self._validate_multi_ids_mode()
        elif self.filter_ids is not None:
            self._validate_direct_ids_mode()
        else:
            self._validate_csv_mode()

    def _validate_multi_ids_mode(self) -> None:
        """Validate multi-field IDs mode configuration."""
        if not self.multi_filter_ids:
            raise ValueError("multi_filter_ids must be non-empty when set")

    def _validate_direct_ids_mode(self) -> None:
        """Validate direct IDs mode configuration."""
        if not self.filter_field:
            raise ValueError("filter_field is required when filter_ids is set")

    def _validate_csv_mode(self) -> None:
        """Validate CSV-based filter configuration."""
        if not self.source_path:
            raise ValueError("source_path is required when filter is enabled")


@dataclass(frozen=True, slots=True)
class VacuumSettings:
    """Vacuum operation configuration with tri-state enabled flag."""

    enabled: bool | None = None
    retention_days: int = 7

    def __post_init__(self) -> None:
        """Validate vacuum configuration."""
        if self.retention_days <= 0:
            raise ValueError(
                f"retention_days must be positive, got {self.retention_days}"
            )
