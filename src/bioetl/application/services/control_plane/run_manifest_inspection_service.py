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
    "RunManifestInspectionCorruptionError",
    "RunManifestInspectionResult",
    "RunManifestInspectionService",
]


class RunManifestInspectionCorruptionError(ValueError):
    """Raised when manifest storage is structurally corrupted during inspection."""

    def __init__(self, identifier: str, reason: str) -> None:
        self.identifier = identifier
        self.reason = reason
        super().__init__(
            f"Run manifest store corruption while resolving {identifier!r}: {reason}"
        )


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
    cross_surface_replay_diff: dict[str, object] = field(default_factory=dict)

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
            "forensic_diff": self.cross_surface_replay_diff,
            "cross_surface_replay_diff": self.cross_surface_replay_diff,
            "differences": [entry.to_dict() for entry in self.differences],
        }


def _build_checkpoint_anchor_matches(
    *,
    left_manifest: RunManifest,
    right_manifest: RunManifest,
) -> dict[str, bool]:
    return {
        "execution_fingerprint": (
            left_manifest.execution_fingerprint == right_manifest.execution_fingerprint
        ),
        "effective_config_hash": (
            left_manifest.code_provenance.effective_config_hash
            == right_manifest.code_provenance.effective_config_hash
        ),
        "effective_config_artifact_id": (
            left_manifest.code_provenance.effective_config_artifact_id
            == right_manifest.code_provenance.effective_config_artifact_id
        ),
        "contract_ref": (
            left_manifest.code_provenance.contract_ref
            == right_manifest.code_provenance.contract_ref
        ),
        "contract_version": (
            left_manifest.code_provenance.contract_version
            == right_manifest.code_provenance.contract_version
        ),
        "input_snapshot_ids": (
            RunManifestInspectionService._manifest_snapshot_ids(left_manifest)
            == RunManifestInspectionService._manifest_snapshot_ids(right_manifest)
        ),
    }


def _build_manifest_diff_payload(
    *,
    classification: dict[str, object],
    semantic_equivalent: bool,
    occurrence_only: bool,
) -> dict[str, object]:
    return {
        "classification": classification["classification"],
        "semantic_equivalent": semantic_equivalent,
        "occurrence_only": occurrence_only,
        "semantic_difference_fields": list(
            cast(tuple[str, ...], classification["semantic_difference_fields"])
        ),
        "occurrence_difference_fields": list(
            cast(tuple[str, ...], classification["occurrence_difference_fields"])
        ),
        "noncanonical_difference_fields": list(
            cast(tuple[str, ...], classification["noncanonical_difference_fields"])
        ),
    }


def _build_effective_config_diff_payload(
    *,
    left_manifest: RunManifest,
    right_manifest: RunManifest,
    effective_config_match: bool,
) -> dict[str, object]:
    return {
        "semantic_equivalent": effective_config_match,
        "left_effective_config_hash": (
            left_manifest.code_provenance.effective_config_hash
        ),
        "right_effective_config_hash": (
            right_manifest.code_provenance.effective_config_hash
        ),
        "left_effective_config_artifact_id": (
            left_manifest.code_provenance.effective_config_artifact_id
        ),
        "right_effective_config_artifact_id": (
            right_manifest.code_provenance.effective_config_artifact_id
        ),
    }


def _build_checkpoint_anchor_diff_payload(
    *,
    checkpoint_anchor_matches: dict[str, bool],
    checkpoint_compatible: bool,
) -> dict[str, object]:
    return {
        "compatible": checkpoint_compatible,
        "matching_fields": [
            name for name, matches in checkpoint_anchor_matches.items() if matches
        ],
        "mismatched_fields": [
            name for name, matches in checkpoint_anchor_matches.items() if not matches
        ],
    }


def _build_lineage_diff_payload(
    *,
    left_manifest: RunManifest,
    right_manifest: RunManifest,
) -> dict[str, object]:
    return {
        "planned_artifacts_match": (
            RunManifestInspectionService._planned_artifact_identity(left_manifest)
            == RunManifestInspectionService._planned_artifact_identity(right_manifest)
        ),
        "left_planned_artifact_count": len(left_manifest.planned_artifacts),
        "right_planned_artifact_count": len(right_manifest.planned_artifacts),
    }


def _build_run_artifact_diff_payload(
    *,
    left_manifest: RunManifest,
    right_manifest: RunManifest,
) -> dict[str, object]:
    left_snapshots = RunManifestInspectionService._manifest_snapshot_ids(left_manifest)
    right_snapshots = RunManifestInspectionService._manifest_snapshot_ids(
        right_manifest
    )
    left_artifacts = RunManifestInspectionService._planned_artifact_identity(
        left_manifest
    )
    right_artifacts = RunManifestInspectionService._planned_artifact_identity(
        right_manifest
    )
    return {
        "input_snapshots_match": left_snapshots == right_snapshots,
        "left_input_snapshot_count": len(left_snapshots),
        "right_input_snapshot_count": len(right_snapshots),
        "planned_artifacts_match": left_artifacts == right_artifacts,
        "left_planned_artifact_count": len(left_artifacts),
        "right_planned_artifact_count": len(right_artifacts),
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

    def resolve_produced_artifacts(
        self,
        identifier: str,
    ) -> tuple[dict[str, object], ...]:
        """Resolve concrete produced artifacts from a manifest-id rooted lookup."""
        result = self.show(identifier)
        trace = result.diagnostics.get("produced_artifact_trace")
        if not isinstance(trace, dict):
            return ()
        artifacts = trace.get("artifacts")
        if not isinstance(artifacts, list):
            return ()
        return tuple(artifact for artifact in artifacts if isinstance(artifact, dict))

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
            cross_surface_replay_diff=self._build_cross_surface_replay_diff(
                left_manifest=left_manifest,
                right_manifest=right_manifest,
                classification=classification,
            ),
        )

    @staticmethod
    def _build_cross_surface_replay_diff(
        *,
        left_manifest: RunManifest,
        right_manifest: RunManifest,
        classification: dict[str, object],
    ) -> dict[str, object]:
        """Return one replay-oriented diff across manifest-adjacent surfaces."""
        effective_config_match = (
            left_manifest.code_provenance.effective_config_hash
            == right_manifest.code_provenance.effective_config_hash
            and left_manifest.code_provenance.effective_config_artifact_id
            == right_manifest.code_provenance.effective_config_artifact_id
        )
        checkpoint_anchor_matches = _build_checkpoint_anchor_matches(
            left_manifest=left_manifest,
            right_manifest=right_manifest,
        )
        checkpoint_compatible = all(checkpoint_anchor_matches.values())
        semantic_equivalent = bool(classification["semantic_equivalent"])
        occurrence_only = bool(classification["occurrence_only"])
        verdict = RunManifestInspectionService._resolve_cross_surface_replay_verdict(
            semantic_equivalent=semantic_equivalent,
            occurrence_only=occurrence_only,
            checkpoint_compatible=checkpoint_compatible,
        )
        return {
            "verdict": verdict,
            "manifest": _build_manifest_diff_payload(
                classification=classification,
                semantic_equivalent=semantic_equivalent,
                occurrence_only=occurrence_only,
            ),
            "effective_config": _build_effective_config_diff_payload(
                left_manifest=left_manifest,
                right_manifest=right_manifest,
                effective_config_match=effective_config_match,
            ),
            "checkpoint_anchors": _build_checkpoint_anchor_diff_payload(
                checkpoint_anchor_matches=checkpoint_anchor_matches,
                checkpoint_compatible=checkpoint_compatible,
            ),
            "lineage": _build_lineage_diff_payload(
                left_manifest=left_manifest,
                right_manifest=right_manifest,
            ),
            "run_artifacts": _build_run_artifact_diff_payload(
                left_manifest=left_manifest,
                right_manifest=right_manifest,
            ),
        }

    @staticmethod
    def _resolve_cross_surface_replay_verdict(
        *,
        semantic_equivalent: bool,
        occurrence_only: bool,
        checkpoint_compatible: bool,
    ) -> str:
        if not semantic_equivalent:
            return "semantic_drift"
        if not checkpoint_compatible:
            return "checkpoint_incompatible"
        if occurrence_only:
            return "occurrence_only_replay"
        return "semantic_equivalent_replay"

    @staticmethod
    def _manifest_snapshot_ids(manifest: RunManifest) -> tuple[str, ...]:
        return tuple(
            sorted(
                snapshot.snapshot_id
                for source_ref in manifest.source_refs
                for snapshot in source_ref.input_snapshots
            )
        )

    @staticmethod
    def _planned_artifact_identity(
        manifest: RunManifest,
    ) -> tuple[tuple[str, str], ...]:
        return tuple(
            sorted(
                (artifact.layer, artifact.path)
                for artifact in manifest.planned_artifacts
            )
        )

    def _resolve_manifest(self, identifier: str) -> RunManifest:
        """Resolve manifest_id first, then run_id lookup when identifier is UUID-like."""
        try:
            manifest = self.manifest_port.get(identifier)
        except ValueError as exc:
            raise RunManifestInspectionCorruptionError(identifier, str(exc)) from exc
        if manifest is not None:
            return manifest
        run_id = self._parse_run_id(identifier)
        if run_id is not None:
            try:
                manifest = self.manifest_port.get_by_run_id(run_id)
            except ValueError as exc:
                raise RunManifestInspectionCorruptionError(
                    identifier, str(exc)
                ) from exc
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
