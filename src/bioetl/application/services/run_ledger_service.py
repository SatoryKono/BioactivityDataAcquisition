"""Facade for the canonical control-plane seam."""

from __future__ import annotations

from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)

__all__ = [
    "RunLedgerService",
]
