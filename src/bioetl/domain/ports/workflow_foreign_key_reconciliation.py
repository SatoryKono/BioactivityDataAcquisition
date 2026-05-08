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
