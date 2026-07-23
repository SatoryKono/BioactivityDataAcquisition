"""Ports for deterministic workflow row reconciliation transforms."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from bioetl.domain.exceptions.base import BioETLError

__all__ = [
    "RowReconciliationConfig",
    "RowReconciliationConfigError",
    "RowReconciliationError",
    "RowReconciliationExecutionError",
    "RowReconciliationLayer",
    "RowReconciliationMissingColumnError",
    "RowReconciliationPort",
    "RowReconciliationResult",
    "RowReconciliationTypePolicy",
    "RowReconciliationTypePolicyError",
]


class RowReconciliationError(BioETLError):
    """Base error for workflow row reconciliation failures."""


class RowReconciliationConfigError(RowReconciliationError):
    """Invalid deterministic row reconciliation configuration."""


class RowReconciliationMissingColumnError(RowReconciliationError):
    """Configured key column is absent from one side of reconciliation."""


class RowReconciliationTypePolicyError(RowReconciliationError):
    """Row key values violate the configured type policy."""


class RowReconciliationExecutionError(RowReconciliationError):
    """Infrastructure reconciliation execution failed."""


class RowReconciliationLayer(StrEnum):
    """Storage layers where row reconciliation is allowed."""

    SILVER = "silver"
    GOLD = "gold"


class RowReconciliationTypePolicy(StrEnum):
    """Supported row-key type comparison policies."""

    STRICT = "strict"


def _coerce_layer(value: RowReconciliationLayer | str) -> RowReconciliationLayer:
    if isinstance(value, RowReconciliationLayer):
        return value
    try:
        return RowReconciliationLayer(str(value).strip().lower())
    except ValueError as exc:
        raise RowReconciliationConfigError(
            "reconcile_rows supports only layer='silver' or layer='gold'"
        ) from exc


def _coerce_type_policy(
    value: RowReconciliationTypePolicy | str,
) -> RowReconciliationTypePolicy:
    if isinstance(value, RowReconciliationTypePolicy):
        return value
    try:
        return RowReconciliationTypePolicy(str(value).strip().lower())
    except ValueError as exc:
        raise RowReconciliationConfigError(
            "reconcile_rows supports only type_policy='strict'"
        ) from exc


def _required_name(value: str, field_name: str) -> str:
    rendered = str(value).strip()
    if not rendered:
        raise RowReconciliationConfigError(f"{field_name} cannot be empty")
    return rendered


def _required_name_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_required_name(value, field_name) for value in values)
    if not normalized:
        raise RowReconciliationConfigError(f"{field_name} cannot be empty")
    if len(set(normalized)) != len(normalized):
        raise RowReconciliationConfigError(f"{field_name} cannot contain duplicates")
    return normalized


def _normalize_workflow_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise RowReconciliationConfigError("workflow_name cannot be empty")
    return normalized


def _normalized_row_reconciliation_fields(
    config: RowReconciliationConfig,
) -> tuple[
    RowReconciliationLayer,
    RowReconciliationTypePolicy,
    str,
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    str | None,
]:
    left_columns = _required_name_tuple(config.left_columns, "left_columns")
    right_columns = _required_name_tuple(config.right_columns, "right_columns")
    if len(left_columns) != len(right_columns):
        raise RowReconciliationConfigError(
            "left_columns and right_columns must have the same length"
        )
    return (
        _coerce_layer(config.layer),
        _coerce_type_policy(config.type_policy),
        _required_name(config.left_table, "left_table"),
        _required_name(config.right_table, "right_table"),
        left_columns,
        right_columns,
        _required_name_tuple(config.left_primary_keys, "left_primary_keys"),
        _normalize_workflow_name(config.workflow_name),
    )


@dataclass(frozen=True, slots=True)
class RowReconciliationConfig:
    """Canonical request for one workflow row reconciliation action."""

    layer: RowReconciliationLayer | str
    left_table: str
    right_table: str
    left_columns: tuple[str, ...]
    right_columns: tuple[str, ...]
    left_primary_keys: tuple[str, ...]
    nulls_equal: bool = False
    type_policy: RowReconciliationTypePolicy | str = RowReconciliationTypePolicy.STRICT
    preserve_order: bool = True
    report_only: bool = True
    workflow_name: str | None = None

    def __post_init__(self) -> None:
        (
            layer,
            type_policy,
            left_table,
            right_table,
            left_columns,
            right_columns,
            left_primary_keys,
            workflow_name,
        ) = _normalized_row_reconciliation_fields(self)

        object.__setattr__(self, "layer", layer)
        object.__setattr__(self, "type_policy", type_policy)
        object.__setattr__(self, "left_table", left_table)
        object.__setattr__(self, "right_table", right_table)
        object.__setattr__(self, "left_columns", left_columns)
        object.__setattr__(self, "right_columns", right_columns)
        object.__setattr__(self, "left_primary_keys", left_primary_keys)
        if workflow_name is not None:
            object.__setattr__(self, "workflow_name", workflow_name)


@dataclass(frozen=True, slots=True)
class RowReconciliationResult:
    """Deterministic result of one row reconciliation action."""

    layer: RowReconciliationLayer
    left_table: str
    right_table: str
    left_columns: tuple[str, ...]
    right_columns: tuple[str, ...]
    left_primary_keys: tuple[str, ...]
    input_left_rows: int
    input_right_rows: int
    kept_rows: int
    excluded_rows: int
    null_key_rows_left: int
    null_key_rows_right: int
    distinct_right_keys: int
    rows: tuple[Mapping[str, object], ...]
    implementation: str
    nulls_equal: bool = False
    type_policy: RowReconciliationTypePolicy = RowReconciliationTypePolicy.STRICT
    preserve_order: bool = True
    report_only: bool = True
    mutated: bool = False

    def __post_init__(self) -> None:
        from bioetl.domain.immutability import deep_freeze_json

        frozen_rows = tuple(
            deep_freeze_json(dict(row) if not isinstance(row, dict) else row)
            if isinstance(row, Mapping)
            else deep_freeze_json(row)
            for row in self.rows
        )
        object.__setattr__(self, "rows", frozen_rows)


@runtime_checkable
class RowReconciliationPort(Protocol):
    """Port for storage-backed deterministic row reconciliation."""

    async def reconcile_rows(
        self,
        config: RowReconciliationConfig,
    ) -> RowReconciliationResult:
        """Reconcile left rows against right-row key existence."""
        ...
