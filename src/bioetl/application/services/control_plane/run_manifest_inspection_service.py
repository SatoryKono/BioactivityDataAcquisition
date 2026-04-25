"""Application service for inspecting run manifests and ledger history."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast
from uuid import UUID

from bioetl.application.services.control_plane._run_manifest_inspection_mixins import (
    RunManifestInspectionDiffClassificationMixin,
    RunManifestInspectionIdentityGraphMixin,
)
from bioetl.application.services.control_plane.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.ports import RunLedgerPort, RunManifestPort
from bioetl.domain.types import RunID

__all__ = [
    "RunManifestDiffEntry",
    "RunManifestDiffResult",
    "RunManifestInspectionResult",
    "RunManifestInspectionService",
]


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


@dataclass(frozen=True, slots=True)
class RunManifestDiffEntry:
    """One top-level manifest field difference."""

    field: str
    left: object
    right: object

    def to_dict(self) -> dict[str, object]:
        """Return JSON/YAML-safe payload for CLI presentation."""
        return {
            "field": self.field,
            "left": self.left,
            "right": self.right,
        }


@dataclass(frozen=True, slots=True)
class RunManifestDiffResult:
    """Top-level diff between two resolved manifests."""

    left_manifest_id: str
    right_manifest_id: str
    differences: tuple[RunManifestDiffEntry, ...]
    classification: str = "identical"
    semantic_equivalent: bool = True
    occurrence_only: bool = False
    occurrence_difference_fields: tuple[str, ...] = ()
    semantic_difference_fields: tuple[str, ...] = ()
    noncanonical_difference_fields: tuple[str, ...] = ()
    replay_relationship: str = "none"

    def to_dict(self) -> dict[str, object]:
        """Return JSON/YAML-safe payload for CLI presentation."""
        return {
            "left_manifest_id": self.left_manifest_id,
            "right_manifest_id": self.right_manifest_id,
            "classification": self.classification,
            "semantic_equivalent": self.semantic_equivalent,
            "occurrence_only": self.occurrence_only,
            "occurrence_difference_fields": list(self.occurrence_difference_fields),
            "semantic_difference_fields": list(self.semantic_difference_fields),
            "noncanonical_difference_fields": list(self.noncanonical_difference_fields),
            "replay_relationship": self.replay_relationship,
            "differences": [entry.to_dict() for entry in self.differences],
        }


@dataclass(slots=True)
class RunManifestInspectionService(
    RunManifestInspectionIdentityGraphMixin,
    RunManifestInspectionDiffClassificationMixin,
):
    """Resolve run manifests and compute CLI-facing diffs."""

    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort | None = None

    def show(self, identifier: str) -> RunManifestInspectionResult:
        """Resolve one manifest by manifest_id or run_id."""
        manifest = self._resolve_manifest(identifier)
        ledger_entries: tuple[RunLedgerEntry, ...] = ()
        if self.ledger_port is not None:
            ledger_entries = tuple(self.ledger_port.list_entries(manifest.manifest_id))
        diagnostics = build_diagnostics_summary(manifest, ledger_entries)
        identity_graph = self._build_identity_graph(manifest, diagnostics)
        diagnostics["identity_graph"] = identity_graph
        return RunManifestInspectionResult(
            manifest=manifest,
            ledger_entries=ledger_entries,
            diagnostics=diagnostics,
            identity_graph=identity_graph,
        )

    def diff(
        self, left_identifier: str, right_identifier: str
    ) -> RunManifestDiffResult:
        """Compute a stable top-level diff between two manifests."""
        left_manifest = self._resolve_manifest(left_identifier)
        right_manifest = self._resolve_manifest(right_identifier)
        left_payload = left_manifest.to_dict()
        right_payload = right_manifest.to_dict()
        diff_fields = tuple(
            RunManifestDiffEntry(
                field=field,
                left=left_payload.get(field),
                right=right_payload.get(field),
            )
            for field in sorted(set(left_payload) | set(right_payload))
            if not self._json_equal(left_payload.get(field), right_payload.get(field))
        )
        classification = self._classify_manifest_diff(
            left_manifest=left_manifest,
            right_manifest=right_manifest,
            differences=diff_fields,
        )
        return RunManifestDiffResult(
            left_manifest_id=left_manifest.manifest_id,
            right_manifest_id=right_manifest.manifest_id,
            differences=diff_fields,
            classification=str(classification["classification"]),
            semantic_equivalent=bool(classification["semantic_equivalent"]),
            occurrence_only=bool(classification["occurrence_only"]),
            occurrence_difference_fields=cast(
                tuple[str, ...],
                classification["occurrence_difference_fields"],
            ),
            semantic_difference_fields=cast(
                tuple[str, ...],
                classification["semantic_difference_fields"],
            ),
            noncanonical_difference_fields=cast(
                tuple[str, ...],
                classification["noncanonical_difference_fields"],
            ),
            replay_relationship=str(classification["replay_relationship"]),
        )

    def _resolve_manifest(self, identifier: str) -> RunManifest:
        """Resolve manifest_id first, then run_id lookup when identifier is UUID-like."""
        manifest = self.manifest_port.get(identifier)
        if manifest is not None:
            return manifest
        run_id = self._parse_run_id(identifier)
        if run_id is not None:
            manifest = self.manifest_port.get_by_run_id(run_id)
            if manifest is not None:
                return manifest
        raise ValueError(f"Run manifest not found for identifier: {identifier}")

    @staticmethod
    def _parse_run_id(identifier: str) -> RunID | None:
        """Parse UUID-like run identifiers safely."""
        try:
            return RunID(UUID(identifier))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _json_equal(left: object, right: object) -> bool:
        """Compare nested payloads using canonical JSON normalization."""
        return json.dumps(left, sort_keys=True, default=str) == json.dumps(
            right,
            sort_keys=True,
            default=str,
        )
