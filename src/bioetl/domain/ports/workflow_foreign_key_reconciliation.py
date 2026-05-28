"""Ports for workflow-level foreign-key reconciliation transforms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

__all__ = [
    "ForeignKeyReconciliationPort",
    "ForeignKeyReconciliationRequest",
    "ForeignKeyReconciliationResult",
]


def _require_non_empty_str(value: str, field_name: str) -> None:
    """Validate that a string is non-empty after trimming."""
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")


def _require_non_empty_primary_keys(primary_keys: tuple[str, ...]) -> None:
    """Validate that primary_keys is non-empty."""
    if not primary_keys:
        raise ValueError("primary_keys cannot be empty")


def _require_non_empty_keys_tuples(
    source_keys: tuple[str, ...],
    reference_keys: tuple[str, ...],
) -> None:
    """Validate that source_keys/reference_keys are not empty."""
    if not source_keys or not reference_keys:
        raise ValueError("source_keys and reference_keys cannot be empty")


def _require_equal_key_tuple_lengths(
    source_keys: tuple[str, ...],
    reference_keys: tuple[str, ...],
) -> None:
    """Validate that source_keys and reference_keys have equal cardinality."""
    if len(source_keys) != len(reference_keys):
        raise ValueError(
            "source_keys and reference_keys must have the same length"
        )


def _require_first_keys_match(
    *,
    source_keys: tuple[str, ...],
    reference_keys: tuple[str, ...],
    source_key: str,
    reference_key: str,
) -> None:
    """Validate that the first tuple entries match the canonical single keys."""
    if source_keys[0].strip() != source_key.strip():
        raise ValueError("source_key must match the first source_keys entry")
    if reference_keys[0].strip() != reference_key.strip():
        raise ValueError("reference_key must match the first reference_keys entry")


def _validate_optional_source_reference_keys_pair(
    *,
    source_keys: tuple[str, ...] | None,
    reference_keys: tuple[str, ...] | None,
    source_key: str,
    reference_key: str,
) -> None:
    """Validate optional tuple-form keys while preserving single-key invariants."""
    if source_keys is None:
        if reference_keys is None:
            return
        raise ValueError("source_keys and reference_keys must be provided together")

    if reference_keys is None:
        raise ValueError("source_keys and reference_keys must be provided together")

    assert source_keys is not None and reference_keys is not None
    _require_non_empty_keys_tuples(source_keys, reference_keys)
    _require_equal_key_tuple_lengths(source_keys, reference_keys)
    _require_first_keys_match(
        source_keys=source_keys,
        reference_keys=reference_keys,
        source_key=source_key,
        reference_key=reference_key,
    )


@dataclass(frozen=True, slots=True)
class ForeignKeyReconciliationRequest:
    """Canonical request for one workflow foreign-key reconciliation action."""

    source_table: str
    reference_table: str
    source_key: str
    reference_key: str
    primary_keys: tuple[str, ...]
    action: Literal["delete_orphans"] = "delete_orphans"
    source_keys: tuple[str, ...] | None = None
    reference_keys: tuple[str, ...] | None = None
    nulls_equal: bool = False

    def __post_init__(self) -> None:
        _require_non_empty_str(self.source_table, "source_table")
        _require_non_empty_str(self.reference_table, "reference_table")
        _require_non_empty_str(self.source_key, "source_key")
        _require_non_empty_str(self.reference_key, "reference_key")
        _require_non_empty_primary_keys(self.primary_keys)

        _validate_optional_source_reference_keys_pair(
            source_keys=self.source_keys,
            reference_keys=self.reference_keys,
            source_key=self.source_key,
            reference_key=self.reference_key,
        )

    @property
    def effective_source_keys(self) -> tuple[str, ...]:
        """Return the canonical source key sequence for the request."""
        return self.source_keys if self.source_keys is not None else (self.source_key,)

    @property
    def effective_reference_keys(self) -> tuple[str, ...]:
        """Return the canonical reference key sequence for the request."""
        return (
            self.reference_keys
            if self.reference_keys is not None
            else (self.reference_key,)
        )


@dataclass(frozen=True, slots=True)
class ForeignKeyReconciliationResult:
    """Deterministic result of one foreign-key reconciliation action."""

    source_table: str
    reference_table: str
    source_key: str
    reference_key: str
    action: str
    scanned_rows: int
    retained_rows: int
    orphan_rows_deleted: int
    mutated: bool


@runtime_checkable
class ForeignKeyReconciliationPort(Protocol):
    """Port for storage-backed foreign-key reconciliation actions."""

    async def reconcile_foreign_keys(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> ForeignKeyReconciliationResult:
        """Reconcile one source table against one reference table."""
        ...
