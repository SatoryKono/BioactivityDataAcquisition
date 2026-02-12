"""Silver filter configuration.

Provides SilverFilterConfig — a semantically distinct type for Silver layer
filtering.  Structurally identical to GoldFilterConfig but typed separately
so that mypy can catch accidental assignment of a Silver-layer filter to a
Gold-layer slot (and vice versa).
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.filtering.gold_config import GoldFilterConfig


@dataclass(frozen=True, slots=True)
class SilverFilterConfig(GoldFilterConfig):
    """Filters applied during Silver layer processing.

    Structurally identical to :class:`GoldFilterConfig` but kept as a
    separate type so that the type checker can distinguish between
    Silver-layer and Gold-layer filter configurations.

    Attributes:
        column_filters: Column value filters (IN / NOT_IN / IS_NULL etc.).
        range_filters: Numeric range filters.
        list_length_filters: List-length bound filters.
        list_contains_filters: List-contents filters.
        required_fields: Fields that must be non-null / non-empty.
        exclude_if_present: Fields whose presence excludes a record.
    """

    # All fields are inherited from GoldFilterConfig.
    # The class exists purely for nominal typing separation.

    @classmethod
    def from_gold_filter_config(cls, config: GoldFilterConfig) -> SilverFilterConfig:
        """Create a SilverFilterConfig from an existing GoldFilterConfig.

        Convenience factory for the migration period where infrastructure
        loaders still produce GoldFilterConfig for Silver filters.
        """
        return cls(
            column_filters=config.column_filters,
            range_filters=config.range_filters,
            list_length_filters=config.list_length_filters,
            list_contains_filters=config.list_contains_filters,
            required_fields=config.required_fields,
            exclude_if_present=config.exclude_if_present,
        )
