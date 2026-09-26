"""Composite pipeline strategy enums.

Defines strategies for merge operations and conflict resolution
in composite pipelines.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "ConflictResolution",
    "FallbackStrategy",
    "MergeStrategy",
]


class MergeStrategy(StrEnum):
    """Strategy for merging enriched data from multiple sources.

    Defines how records from seed and enricher pipelines are combined.

    Attributes:
        LEFT_OUTER: All seed records preserved, enrichments nullable.
            Use when all seed records must appear in output regardless
            of enrichment success.
        INNER: Only records found in ALL required enrichers.
            Use when complete enrichment is mandatory for downstream use.
        UNION: All records from any source with deduplication.
            Use when maximizing coverage is more important than completeness.

    Example:
        >>> strategy = MergeStrategy.LEFT_OUTER
        >>> strategy.value
        'left_outer'
        >>> MergeStrategy.from_string("inner")
        <MergeStrategy.INNER: 'inner'>
    """

    LEFT_OUTER = "left_outer"
    INNER = "inner"
    UNION = "union"

    @classmethod
    def from_string(cls, value: str) -> MergeStrategy:
        """Create MergeStrategy from string value.

        Args:
            value: String representation of strategy.

        Returns:
            MergeStrategy enum value.

        Raises:
            ValueError: If value is not a valid strategy.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(
                f"Invalid merge strategy: {value}. Valid: {valid}"
            ) from None


class ConflictResolution(StrEnum):
    """Strategy for resolving field conflicts between sources.

    When the same field is populated by multiple sources (e.g., 'title'
    from both ChEMBL and CrossRef), this strategy determines which
    value to use.

    Attributes:
        SEED_PRIORITY: Seed pipeline value wins. Use when seed is
            authoritative and enrichers provide supplemental data.
        ENRICHER_PRIORITY: Most recent enricher value wins. Use when
            enrichers have more up-to-date information.
        LATEST_TIMESTAMP: Value from source with latest extraction timestamp.
            Not yet implemented; currently falls back to SEED_PRIORITY.
        EXPLICIT_RULES: Use field_priorities mapping in config. Allows
            field-by-field control over priority order.
        COALESCE: First non-null value in order: seed, then enrichers.
            Use when any source is acceptable.

    Example:
        >>> resolution = ConflictResolution.SEED_PRIORITY
        >>> resolution.value
        'seed_priority'
    """

    SEED_PRIORITY = "seed_priority"
    ENRICHER_PRIORITY = "enricher"
    LATEST_TIMESTAMP = "latest"
    EXPLICIT_RULES = "explicit"
    COALESCE = "coalesce"

    @classmethod
    def from_string(cls, value: str) -> ConflictResolution:
        """Create ConflictResolution from string value.

        Args:
            value: String representation of resolution strategy.

        Returns:
            ConflictResolution enum value.

        Raises:
            ValueError: If value is not a valid resolution.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(
                f"Invalid conflict resolution: {value}. Valid: {valid}"
            ) from None


class FallbackStrategy(StrEnum):
    """Strategy for handling enricher failures.

    Defines behavior when an optional enricher fails or times out.

    Attributes:
        SKIP: Skip the enricher, continue without its data. Use when
            enrichment is purely supplemental.
        USE_CACHED: Use previously cached enrichment data if available.
            Requires caching infrastructure.
        FAIL: Treat failure as composite failure. Use when enricher
            data is critical even if marked optional.

    Example:
        >>> fallback = FallbackStrategy.SKIP
        >>> fallback.value
        'skip'
    """

    SKIP = "skip"
    USE_CACHED = "use_cached"
    FAIL = "fail"

    @classmethod
    def from_string(cls, value: str) -> FallbackStrategy:
        """Create FallbackStrategy from string value.

        Args:
            value: String representation of fallback strategy.

        Returns:
            FallbackStrategy enum value.

        Raises:
            ValueError: If value is not a valid strategy.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(
                f"Invalid fallback strategy: {value}. Valid: {valid}"
            ) from None
