"""Silver filter configuration."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.filtering._base_filter_config import BaseFilterConfig


@dataclass(frozen=True, slots=True)
class SilverFilterConfig(BaseFilterConfig):
    """Filters applied during Silver layer processing."""

    @classmethod
    def from_base(cls, other: BaseFilterConfig) -> SilverFilterConfig:
        """Create a SilverFilterConfig from another base filter config."""
        return cls(
            column_filters=other.column_filters,
            range_filters=other.range_filters,
            list_length_filters=other.list_length_filters,
            list_contains_filters=other.list_contains_filters,
            required_fields=other.required_fields,
            exclude_if_present=other.exclude_if_present,
        )
