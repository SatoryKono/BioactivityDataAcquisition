from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.composite.config import DataSchemaConfig, LayerColumnConfig, ColumnGroupConfig


def require_non_empty(value: object, field_name: str) -> None:
    """Validate that a value is not empty."""
    if not value:
        raise ValueError(f"{field_name} cannot be empty")


def validate_positive(value: int | float, field_name: str) -> None:
    """Validate that a value is positive."""
    if value <= 0:
        raise ValueError(f"{field_name} must be positive, got {value}")


def validate_positive_limit(limit: int | None, context: str) -> None:
    """Validate that an optional limit is positive if provided."""
    if limit is not None and limit <= 0:
        raise ValueError(f"{context} limit must be positive, got {limit}")


def validate_optional_threshold(value: float | None, name: str) -> None:
    """Validate that an optional threshold is in [0.0, 1.0] range."""
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")


def validate_threshold_order(soft: float | None, hard: float | None) -> None:
    """Validate that soft threshold is less than hard threshold."""
    if soft is not None and hard is not None and soft >= hard:
        raise ValueError("soft_fail_threshold must be less than hard_fail_threshold")


def normalize_data_schema_config(config: DataSchemaConfig) -> None:
    """Normalize DataSchemaConfig attributes in place."""
    from bioetl.domain.composite.config import ColumnGroupConfig, LayerColumnConfig

    # Normalize column_groups
    if isinstance(config.column_groups, list):
        groups = tuple(
            ColumnGroupConfig(**g) if isinstance(g, dict) else g
            for g in config.column_groups
        )
        object.__setattr__(config, "column_groups", groups)

    # Normalize silver config
    if isinstance(config.silver, dict):
        object.__setattr__(config, "silver", LayerColumnConfig(**config.silver))

    # Normalize gold config
    if isinstance(config.gold, dict):
        object.__setattr__(config, "gold", LayerColumnConfig(**config.gold))
