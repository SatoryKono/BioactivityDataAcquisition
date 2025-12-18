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


@dataclass(frozen=True)
class TableConfig:
    """Configuration for database tables and keys."""
    primary_keys: list[str] = field(default_factory=lambda: ["entity_id"])
    silver_table: str | None = None
    gold_table: str | None = None
