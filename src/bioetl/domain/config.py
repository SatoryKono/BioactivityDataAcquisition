"""Domain configuration objects.

This module defines configuration value objects used within the Domain and Application layers.
These are distinct from Infrastructure configuration schemas (Pydantic) to maintain
strict layer separation.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DQConfig:
    """Configuration for Data Quality thresholds."""
    soft_fail_threshold: float = 0.05
    hard_fail_threshold: float = 0.20

    def __post_init__(self) -> None:
        """Validate threshold invariants on creation."""
        self.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )

    @staticmethod
    def validate_thresholds(
        *, soft_fail_threshold: float, hard_fail_threshold: float
    ) -> None:
        """Validate ordering and bounds for DQ thresholds."""
        if not 0.0 <= soft_fail_threshold <= 1.0:
            raise ValueError(
                "soft_fail_threshold must be between 0.0 and 1.0 inclusive"
            )
        if not 0.0 <= hard_fail_threshold <= 1.0:
            raise ValueError(
                "hard_fail_threshold must be between 0.0 and 1.0 inclusive"
            )
        if soft_fail_threshold >= hard_fail_threshold:
            raise ValueError(
                "soft_fail_threshold must be strictly less than hard_fail_threshold"
            )


@dataclass(frozen=True)
class TableConfig:
    """Configuration for database tables and keys."""
    primary_keys: list[str] = field(default_factory=lambda: ["entity_id"])
    silver_table: str | None = None
    gold_table: str | None = None
