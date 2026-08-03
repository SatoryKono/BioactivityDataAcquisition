"""Run manifest inspection result model."""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest


@dataclass(frozen=True, slots=True)
class RunManifestInspectionResult:
    """Resolved control-plane view for one manifest and its ledger history."""

    manifest: RunManifest
    ledger_entries: tuple[RunLedgerEntry, ...] = ()
    diagnostics: dict[str, object] = field(default_factory=dict)
    identity_graph: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return JSON/YAML-safe payload for CLI presentation."""
        return {
            "manifest": self.manifest.to_dict(),
            "ledger_entries": [entry.to_dict() for entry in self.ledger_entries],
            "diagnostics": self.diagnostics,
            "identity_graph": self.identity_graph,
        }


__all__ = ["RunManifestInspectionResult"]
