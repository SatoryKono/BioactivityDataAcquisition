"""Port for workflow-level foreign-key reconciliation transforms.

Request/Result value objects live in ``bioetl.domain.workflow.foreign_key_reconciliation``.
This module re-exports those names for one-release import compatibility (#9628).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.workflow.foreign_key_reconciliation import (
    ForeignKeyReconciliationAction,
    ForeignKeyReconciliationLayer,
    ForeignKeyReconciliationMutationMode,
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
)

__all__ = [
    "ForeignKeyReconciliationAction",
    "ForeignKeyReconciliationLayer",
    "ForeignKeyReconciliationMutationMode",
    "ForeignKeyReconciliationPort",
    "ForeignKeyReconciliationRequest",
    "ForeignKeyReconciliationResult",
]


@runtime_checkable
class ForeignKeyReconciliationPort(Protocol):
    """Port for storage-backed foreign-key reconciliation actions."""

    async def reconcile_foreign_keys(
        self,
        request: ForeignKeyReconciliationRequest,
    ) -> ForeignKeyReconciliationResult:
        """Reconcile one source table against one reference table."""
        ...
