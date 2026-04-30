"""Application service for inspecting run manifests and ledger history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from bioetl.application.services.control_plane._run_manifest_inspection_mixins import (
    RunManifestInspectionDiffClassificationMixin,
    RunManifestInspectionIdentityGraphMixin,
)
from bioetl.application.services.control_plane.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.application.services.control_plane.run_manifest_inspection_helpers import (
    build_checkpoint_anchor_diff_payload,
    build_checkpoint_anchor_matches,
    build_effective_config_diff_payload,
    build_lineage_diff_payload,
    build_manifest_diff_payload,
    build_run_artifact_diff_payload,
)
from bioetl.application.services.control_plane.run_manifest_inspection_models import (
    RunManifestDiffEntry,
    RunManifestDiffResult,
    RunManifestInspectionCorruptionError,
    RunManifestInspectionResult,
    RunManifestVerifyResult,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.ports import (
    EffectiveConfigArtifactStorePort,
    RunLedgerPort,
    RunManifestPort,
)
from bioetl.domain.types import RunID

__all__ = [
    "RunManifestDiffEntry",
    "RunManifestDiffResult",
    "RunManifestInspectionCorruptionError",
    "RunManifestInspectionResult",
    "RunManifestInspectionService",
    "RunManifestVerifyResult",
]


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
    checkpoint_anchor_matches = build_checkpoint_anchor_matches(
        left_manifest=left_manifest,
        right_manifest=right_manifest,
    )
    checkpoint_compatible = all(checkpoint_anchor_matches.values())
    semantic_equivalent = bool(classification["semantic_equivalent"])
    occurrence_only = bool(classification["occurrence_only"])
    verdict = _resolve_cross_surface_replay_verdict(
        semantic_equivalent=semantic_equivalent,
        occurrence_only=occurrence_only,
        checkpoint_compatible=checkpoint_compatible,
    )
    return {
        "verdict": verdict,
        "manifest": build_manifest_diff_payload(
            classification=classification,
            semantic_equivalent=semantic_equivalent,
            occurrence_only=occurrence_only,
        ),
        "effective_config": build_effective_config_diff_payload(
            left_manifest=left_manifest,
            right_manifest=right_manifest,
            effective_config_match=effective_config_match,
        ),
        "checkpoint_anchors": build_checkpoint_anchor_diff_payload(
            checkpoint_anchor_matches=checkpoint_anchor_matches,
            checkpoint_compatible=checkpoint_compatible,
        ),
        "lineage": build_lineage_diff_payload(
            left_manifest=left_manifest,
            right_manifest=right_manifest,
        ),
        "run_artifacts": build_run_artifact_diff_payload(
            left_manifest=left_manifest,
            right_manifest=right_manifest,
        ),
    }


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


def _build_effective_config_store_verification(
    effective_config_artifact_port: EffectiveConfigArtifactStorePort | None,
    *,
    left_manifest: RunManifest,
    right_manifest: RunManifest,
) -> dict[str, object]:
    """Compare effective-config evidence loaded through the configured port."""
    if effective_config_artifact_port is None:
        return {
            "available": False,
            "semantic_equivalent": False,
            "occurrence_only": False,
            "missing_evidence": ["effective_config_store_unconfigured"],
        }

    left_artifact = effective_config_artifact_port.get_by_run_id(left_manifest.run_id)
    right_artifact = effective_config_artifact_port.get_by_run_id(right_manifest.run_id)
    left_occurrence = effective_config_artifact_port.get_occurrence_by_run_id(
        left_manifest.run_id
    )
    right_occurrence = effective_config_artifact_port.get_occurrence_by_run_id(
        right_manifest.run_id
    )
    occurrence_diff = effective_config_artifact_port.diff_occurrences_by_run_id(
        left_manifest.run_id,
        right_manifest.run_id,
    )
    missing_evidence = _effective_config_missing_evidence(
        left_artifact=left_artifact,
        right_artifact=right_artifact,
        left_occurrence=left_occurrence,
        right_occurrence=right_occurrence,
    )
    left_anchor = _effective_config_artifact_anchor(left_artifact)
    right_anchor = _effective_config_artifact_anchor(right_artifact)
    left_manifest_anchor = _manifest_effective_config_anchor(left_manifest)
    right_manifest_anchor = _manifest_effective_config_anchor(right_manifest)
    anchor_matches = {
        "left_artifact_id": (
            left_manifest_anchor["artifact_id"] == left_anchor.get("artifact_id")
        ),
        "right_artifact_id": (
            right_manifest_anchor["artifact_id"] == right_anchor.get("artifact_id")
        ),
        "left_effective_config_hash": (
            left_manifest_anchor["effective_config_hash"]
            == left_anchor.get("effective_config_hash")
        ),
        "right_effective_config_hash": (
            right_manifest_anchor["effective_config_hash"]
            == right_anchor.get("effective_config_hash")
        ),
    }
    semantic_equivalent = (
        bool(occurrence_diff.get("semantic_equivalent"))
        and all(anchor_matches.values())
        and not missing_evidence
    )
    differences = occurrence_diff.get("differences")
    return {
        **occurrence_diff,
        "available": True,
        "semantic_equivalent": semantic_equivalent,
        "occurrence_only": semantic_equivalent and bool(differences),
        "left_manifest_anchor": left_manifest_anchor,
        "right_manifest_anchor": right_manifest_anchor,
        "left_artifact_anchor": left_anchor,
        "right_artifact_anchor": right_anchor,
        "anchor_matches": anchor_matches,
        "missing_evidence": list(missing_evidence),
    }


def _effective_config_missing_evidence(
    *,
    left_artifact: dict[str, object] | None,
    right_artifact: dict[str, object] | None,
    left_occurrence: dict[str, object] | None,
    right_occurrence: dict[str, object] | None,
) -> tuple[str, ...]:
    missing: list[str] = []
    if left_artifact is None:
        missing.append("left_effective_config_artifact_missing")
    if right_artifact is None:
        missing.append("right_effective_config_artifact_missing")
    if left_occurrence is None:
        missing.append("left_effective_config_occurrence_missing")
    if right_occurrence is None:
        missing.append("right_effective_config_occurrence_missing")
    return tuple(missing)


def _manifest_effective_config_anchor(manifest: RunManifest) -> dict[str, object]:
    code_provenance = manifest.code_provenance
    return {
        "artifact_id": code_provenance.effective_config_artifact_id,
        "effective_config_hash": code_provenance.effective_config_hash,
    }


def _effective_config_artifact_anchor(
    artifact: dict[str, object] | None,
) -> dict[str, object]:
    if artifact is None:
        return {"artifact_id": None, "effective_config_hash": None}
    semantic_artifact = artifact.get("semantic_artifact")
    if not isinstance(semantic_artifact, dict):
        semantic_artifact = artifact
    return {
        "artifact_id": artifact.get("artifact_id")
        or semantic_artifact.get("artifact_id"),
        "effective_config_hash": semantic_artifact.get("effective_config_hash"),
    }


def _resolve_verify_verdict(
    *,
    manifest_classification: str,
    manifest_semantic_equivalent: bool,
    effective_config_semantic_equivalent: bool,
    missing_evidence: tuple[str, ...],
    occurrence_only: bool,
) -> str:
    if missing_evidence:
        return "missing_replay_evidence"
    if not manifest_semantic_equivalent:
        return "semantic_drift"
    if not effective_config_semantic_equivalent:
        return "effective_config_semantic_drift"
    if occurrence_only or manifest_classification == "occurrence_only":
        return "occurrence_only_replay_verified"
    return "cross_store_replay_verified"


def _parse_run_id(identifier: str) -> RunID | None:
    """Parse UUID-like run identifiers safely."""
    try:
        return RunID(UUID(identifier))
    except (TypeError, ValueError):
        return None


def _json_equal(left: object, right: object) -> bool:
    """Compare nested payloads using canonical JSON normalization."""
    return json.dumps(left, sort_keys=True, default=str) == json.dumps(
        right,
        sort_keys=True,
        default=str,
    )


@dataclass(slots=True)
class RunManifestInspectionService(
    RunManifestInspectionIdentityGraphMixin,
    RunManifestInspectionDiffClassificationMixin,
):
    """Resolve run manifests and compute CLI-facing diffs."""

    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort | None = None
    effective_config_artifact_port: EffectiveConfigArtifactStorePort | None = None

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
            if not _json_equal(left_payload.get(field), right_payload.get(field))
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
            cross_surface_replay_diff=_build_cross_surface_replay_diff(
                left_manifest=left_manifest,
                right_manifest=right_manifest,
                classification=classification,
            ),
        )

    def verify(
        self, left_identifier: str, right_identifier: str
    ) -> RunManifestVerifyResult:
        """Verify replay evidence across manifest and effective-config stores."""
        diff_result = self.diff(left_identifier, right_identifier)
        left_manifest = self._resolve_manifest(left_identifier)
        right_manifest = self._resolve_manifest(right_identifier)
        effective_config = _build_effective_config_store_verification(
            self.effective_config_artifact_port,
            left_manifest=left_manifest,
            right_manifest=right_manifest,
        )
        raw_missing_evidence = effective_config.get("missing_evidence", ())
        missing_evidence_items = (
            raw_missing_evidence
            if isinstance(raw_missing_evidence, (list, tuple))
            else ()
        )
        missing_evidence = tuple(
            item for item in missing_evidence_items if isinstance(item, str)
        )
        effective_config_semantic_equivalent = bool(
            effective_config.get("semantic_equivalent")
        )
        effective_config_occurrence_only = bool(effective_config.get("occurrence_only"))
        semantic_equivalent = (
            diff_result.semantic_equivalent and effective_config_semantic_equivalent
        )
        occurrence_only = (
            diff_result.occurrence_only or effective_config_occurrence_only
        )
        verified = semantic_equivalent and not missing_evidence
        verdict = _resolve_verify_verdict(
            manifest_classification=diff_result.classification,
            manifest_semantic_equivalent=diff_result.semantic_equivalent,
            effective_config_semantic_equivalent=effective_config_semantic_equivalent,
            missing_evidence=missing_evidence,
            occurrence_only=occurrence_only,
        )
        return RunManifestVerifyResult(
            left_manifest_id=left_manifest.manifest_id,
            right_manifest_id=right_manifest.manifest_id,
            left_run_id=str(left_manifest.run_id),
            right_run_id=str(right_manifest.run_id),
            verdict=verdict,
            verified=verified,
            semantic_equivalent=semantic_equivalent,
            occurrence_only=occurrence_only,
            missing_evidence=missing_evidence,
            manifest_diff=diff_result.to_dict(),
            effective_config=effective_config,
        )

    def _resolve_manifest(self, identifier: str) -> RunManifest:
        """Resolve manifest_id first, then run_id lookup when identifier is UUID-like."""
        try:
            manifest = self.manifest_port.get(identifier)
        except ValueError as exc:
            raise RunManifestInspectionCorruptionError(identifier, str(exc)) from exc
        if manifest is not None:
            return manifest
        run_id = _parse_run_id(identifier)
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
