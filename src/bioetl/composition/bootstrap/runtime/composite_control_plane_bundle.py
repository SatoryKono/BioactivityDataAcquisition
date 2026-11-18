"""Control-plane artifact bundle for composite runtime bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.ports import PipelineControlPlaneArtifacts as ControlPlaneArtifacts

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )


@dataclass(frozen=True, slots=True)
class CompositeControlPlaneBundle(ControlPlaneArtifacts):
    """Optional control-plane artifacts materialized for one composite run."""

    run_ledger_service: RunLedgerService | None = None
    contract_ref: str | None = None
    contract_version: str | None = None


__all__ = ["CompositeControlPlaneBundle"]
