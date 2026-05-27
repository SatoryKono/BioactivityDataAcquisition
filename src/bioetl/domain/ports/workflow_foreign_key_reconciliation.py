"""Ports for workflow-level foreign-key reconciliation transforms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

__all__ = [
    "ForeignKeyReconciliationPort",
    "ForeignKeyReconciliationRequest",
    "ForeignKeyReconciliationResult",
]


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
        self._validate_required_fields()
        self._validate_composite_keys()

    def _validate_required_fields(self) -> None:
        if not self.source_table.strip():
            raise ValueError("source_table cannot be empty")
        if not self.reference_table.strip():
            raise ValueError("reference_table cannot be empty")
        if not self.source_key.strip():
            raise ValueError("source_key cannot be empty")
        if not self.reference_key.strip():
            raise ValueError("reference_key cannot be empty")
        if not self.primary_keys:
            raise ValueError("primary_keys cannot be empty")

    def _validate_composite_keys(self) -> None:
        if self.source_keys is None and self.reference_keys is None:
            return
        if self.source_keys is None or self.reference_keys is None:
            raise ValueError("source_keys and reference_keys must be provided together")
        if not self.source_keys or not self.reference_keys:
            raise ValueError("source_keys and reference_keys cannot be empty")
        if len(self.source_keys) != len(self.reference_keys):
            raise ValueError("source_keys and reference_keys must have the same length")
        if self.source_keys[0].strip() != self.source_key.strip():
            raise ValueError("source_key must match the first source_keys entry")
        if self.reference_keys[0].strip() != self.reference_key.strip():
            raise ValueError("reference_key must match the first reference_keys entry")

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
