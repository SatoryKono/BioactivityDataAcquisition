"""Application service for inspecting run manifests and ledger history."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast
from uuid import UUID

from bioetl.application.services.control_plane.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
)
from bioetl.domain.ports import RunLedgerPort, RunManifestPort
from bioetl.domain.types import RunID

__all__ = [
    "RunManifestDiffEntry",
    "RunManifestDiffResult",
    "RunManifestInspectionResult",
    "RunManifestInspectionService",
]

_OCCURRENCE_ONLY_DIFF_FIELDS = frozenset({"manifest_id", "run_id", "created_at"})


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
class RunManifestInspectionService:
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
            return cast(RunManifest, manifest)
        run_id = self._parse_run_id(identifier)
        if run_id is not None:
            manifest = self.manifest_port.get_by_run_id(run_id)
            if manifest is not None:
                return cast(RunManifest, manifest)
        raise ValueError(f"Run manifest not found for identifier: {identifier}")

    @staticmethod
    def _build_identity_graph(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        """Return one operator-facing run identity graph payload."""
        existing = diagnostics.get("identity_graph")
        if isinstance(existing, dict):
            artifact_refs = diagnostics.get("artifact_refs")
            if isinstance(artifact_refs, list):
                existing["published_artifacts"] = [
                    artifact_ref
                    for artifact_ref in artifact_refs
                    if isinstance(artifact_ref, dict)
                ]
            return existing

        code_provenance = manifest.code_provenance
        canonical_execution_identity = build_execution_identity_payload(
            pipeline_name=manifest.pipeline_name,
            run_type=manifest.run_type.value,
            pipeline_version=code_provenance.pipeline_version,
            effective_config_hash=code_provenance.effective_config_hash,
            dq_contract_compatibility_hash=(
                code_provenance.dq_contract_compatibility_hash
            ),
            contract_ref=code_provenance.contract_ref,
            contract_version=code_provenance.contract_version,
            effective_config_artifact_id=code_provenance.effective_config_artifact_id,
            exact_replay=bool(manifest.launch_context.get("exact_replay")),
            input_snapshot_fingerprint=cast(
                "str | None",
                diagnostics.get("input_snapshot_identity_fingerprint"),
            ),
        )
        degraded_runtime_anchor_payload = {
            key: value
            for key, value in {
                "manifest_id": manifest.manifest_id,
                "effective_config_hash": code_provenance.effective_config_hash,
                "contract_ref": code_provenance.contract_ref,
                "contract_version": code_provenance.contract_version,
                "effective_config_artifact_id": (
                    code_provenance.effective_config_artifact_id
                ),
            }.items()
            if value is not None
        }
        return {
            "run_id": str(manifest.run_id),
            "manifest_id": manifest.manifest_id,
            "execution_fingerprint": manifest.execution_fingerprint,
            "config_hash": code_provenance.config_hash,
            "resolved_config_hash": code_provenance.resolved_config_hash,
            "effective_config_hash": code_provenance.effective_config_hash,
            "contract_ref": code_provenance.contract_ref,
            "contract_version": code_provenance.contract_version,
            "replay_of_run_id": diagnostics.get("replay_of_run_id"),
            "replay_of_manifest_id": diagnostics.get("replay_of_manifest_id"),
            "replay_parentage": diagnostics.get("replay_parentage"),
            "canonical_execution_identity": {
                "execution_fingerprint": manifest.execution_fingerprint,
                "payload": canonical_execution_identity,
            },
            "degraded_runtime_anchor": {
                "compatibility_scope": "legacy_fallback_only",
                "fingerprint": (
                    compute_execution_identity_fingerprint(
                        degraded_runtime_anchor_payload
                    )
                    if degraded_runtime_anchor_payload
                    else None
                ),
                "payload": degraded_runtime_anchor_payload,
            },
            "replay_capability": diagnostics.get(
                "replay_capability",
                manifest.replay_capability.value,
            ),
            "requested_exact_replay": diagnostics.get(
                "requested_exact_replay",
                bool(manifest.launch_context.get("exact_replay")),
            ),
            "exact_replay_support_boundary": diagnostics.get(
                "exact_replay_support_boundary",
                "snapshot_backed_source_runs_only",
            ),
            "replay_family_contract": diagnostics.get("replay_family_contract"),
            "replay_capability_reason": diagnostics.get("replay_capability_reason"),
            "exact_replay_eligible": diagnostics.get(
                "exact_replay_eligible",
                manifest.replay_capability.value == "exact_replay_supported",
            ),
            "exact_replay_blockers": diagnostics.get("exact_replay_blockers", []),
            "resume_contract": diagnostics.get("resume_contract"),
            "resume_diagnostics": diagnostics.get("resume_diagnostics"),
            "input_snapshot_ids": diagnostics.get("input_snapshot_ids", []),
            "input_snapshot_content_hashes": diagnostics.get(
                "input_snapshot_content_hashes",
                [],
            ),
            "input_snapshot_identity_fingerprint": diagnostics.get(
                "input_snapshot_identity_fingerprint"
            ),
            "replay_mode": diagnostics.get("replay_mode", "rebuild"),
            "input_snapshot_count": diagnostics.get("input_snapshot_count", 0),
            "input_snapshots": diagnostics.get("input_snapshots", []),
            "planned_artifacts": [
                {"layer": artifact.layer, "path": artifact.path}
                for artifact in manifest.planned_artifacts
            ],
            "published_artifacts": [],
            "occurrence_only_diagnostics": diagnostics.get(
                "occurrence_only_diagnostics", []
            ),
        }

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

    @staticmethod
    def _classify_manifest_diff(
        *,
        left_manifest: RunManifest,
        right_manifest: RunManifest,
        differences: tuple[RunManifestDiffEntry, ...],
    ) -> dict[str, object]:
        """Classify a manifest diff into occurrence-only vs semantic drift."""
        diff_fields = tuple(entry.field for entry in differences)
        if not diff_fields:
            return {
                "classification": "identical",
                "semantic_equivalent": True,
                "occurrence_only": False,
                "occurrence_difference_fields": (),
                "semantic_difference_fields": (),
                "noncanonical_difference_fields": (),
                "replay_relationship": "none",
            }

        occurrence_difference_fields = tuple(
            field for field in diff_fields if field in _OCCURRENCE_ONLY_DIFF_FIELDS
        )
        non_occurrence_fields = tuple(
            field for field in diff_fields if field not in _OCCURRENCE_ONLY_DIFF_FIELDS
        )
        semantic_equivalent = (
            left_manifest.execution_fingerprint == right_manifest.execution_fingerprint
        )
        replay_relationship = RunManifestInspectionService._resolve_replay_relationship(
            left_manifest=left_manifest,
            right_manifest=right_manifest,
        )
        if semantic_equivalent:
            return RunManifestInspectionService._semantic_equivalent_diff_payload(
                occurrence_difference_fields=occurrence_difference_fields,
                non_occurrence_fields=non_occurrence_fields,
                replay_relationship=replay_relationship,
            )
        return {
            "classification": "semantic_drift",
            "semantic_equivalent": False,
            "occurrence_only": False,
            "occurrence_difference_fields": occurrence_difference_fields,
            "semantic_difference_fields": non_occurrence_fields or diff_fields,
            "noncanonical_difference_fields": (),
            "replay_relationship": replay_relationship,
        }

    @staticmethod
    def _semantic_equivalent_diff_payload(
        *,
        occurrence_difference_fields: tuple[str, ...],
        non_occurrence_fields: tuple[str, ...],
        replay_relationship: str,
    ) -> dict[str, object]:
        """Return the diff payload for semantic-equivalent manifest pairs."""
        if not non_occurrence_fields:
            return {
                "classification": "occurrence_only",
                "semantic_equivalent": True,
                "occurrence_only": True,
                "occurrence_difference_fields": occurrence_difference_fields,
                "semantic_difference_fields": (),
                "noncanonical_difference_fields": (),
                "replay_relationship": replay_relationship,
            }
        return {
            "classification": "semantic_equivalent_with_noncanonical_differences",
            "semantic_equivalent": True,
            "occurrence_only": False,
            "occurrence_difference_fields": occurrence_difference_fields,
            "semantic_difference_fields": (),
            "noncanonical_difference_fields": non_occurrence_fields,
            "replay_relationship": replay_relationship,
        }

    @staticmethod
    def _manifest_replays_other(
        *,
        manifest: RunManifest,
        other: RunManifest,
    ) -> bool:
        """Return whether one manifest explicitly replays the other."""
        return (
            manifest.replay_of_manifest_id == other.manifest_id
            or manifest.replay_of_run_id == str(other.run_id)
        )

    @staticmethod
    def _resolve_replay_relationship(
        *,
        left_manifest: RunManifest,
        right_manifest: RunManifest,
    ) -> str:
        """Classify explicit replay ancestry separately from semantic equality."""
        left_replays_right = RunManifestInspectionService._manifest_replays_other(
            manifest=left_manifest,
            other=right_manifest,
        )
        right_replays_left = RunManifestInspectionService._manifest_replays_other(
            manifest=right_manifest,
            other=left_manifest,
        )
        if left_replays_right and right_replays_left:
            return "mutual_replay_cycle"
        if left_replays_right:
            return "left_is_exact_replay_of_right"
        if right_replays_left:
            return "right_is_exact_replay_of_left"
        if (
            left_manifest.replay_of_manifest_id is not None
            or left_manifest.replay_of_run_id is not None
            or right_manifest.replay_of_manifest_id is not None
            or right_manifest.replay_of_run_id is not None
        ):
            return "external_replay_parentage_present"
        return "none"
