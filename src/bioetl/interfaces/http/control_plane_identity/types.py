"""Shared types for Control Plane identity evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry

IDENTITY_EVIDENCE_CONTRACT = "control_plane_identity_evidence_v1"


class LedgerEntryProvider(Protocol):
    """Minimal ledger surface required by identity evidence assembly."""

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]: ...


@dataclass(frozen=True, slots=True)
class AnchorSpec:
    """Static presentation and policy metadata for one identity anchor."""

    priority: str
    name: str
    label: str
    source: str
    value_format: str
    why: str
    rendering: str
    copy: bool
    drilldown: str
    missing_severity: str


@dataclass(frozen=True, slots=True)
class AnchorSourceModel:
    """Machine-readable source classification for one identity anchor."""

    source_type: str
    source_quality: str


@dataclass(frozen=True, slots=True)
class DrilldownTarget:
    """Machine-readable drilldown target metadata for one identity anchor."""

    target_type: str
    target_template: str
    label: str
