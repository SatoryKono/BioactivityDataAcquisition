"""Pure verification helpers for run-manifest inspection workflows."""

from __future__ import annotations

import json
from typing import Protocol
from uuid import UUID

from bioetl.application.services.control_plane.run_manifest_inspection_helpers import (
    build_checkpoint_anchor_diff_payload,
    build_checkpoint_anchor_matches,
    build_effective_config_diff_payload,
    build_lineage_diff_payload,
    build_manifest_diff_payload,
    build_run_artifact_diff_payload,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID

__all__ = [
    "build_cross_surface_replay_diff",
    "build_effective_config_store_verification",
    "json_equal",
    "parse_run_id",
    "resolve_cross_surface_replay_verdict",
    "resolve_verify_verdict",
]


class EffectiveConfigArtifactStoreProtocol(Protocol):
    """Structural protocol for effective-config artifact verification."""

    def get_by_run_id(self, run_id: RunID) -> dict[str, object] | None: ...

    def get_occurrence_by_run_id(self, run_id: RunID) -> dict[str, object] | None: ...

    def diff_occurrences_by_run_id(
        self,
        left_run_id: RunID,
        right_run_id: RunID,
    ) -> dict[str, object]: ...


def build_cross_surface_replay_diff(
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
    verdict = resolve_cross_surface_replay_verdict(
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


def resolve_cross_surface_replay_verdict(
    *,
    semantic_equivalent: bool,
    occurrence_only: bool,
    checkpoint_compatible: bool,
) -> str:
    """Return replay verdict from manifest/effective-config/checkpoint state."""
    if not semantic_equivalent:
        return "semantic_drift"
    if not checkpoint_compatible:
        return "checkpoint_incompatible"
    if occurrence_only:
        return "occurrence_only_replay"
    return "semantic_equivalent_replay"


def build_effective_config_store_verification(
    effective_config_artifact_port: EffectiveConfigArtifactStoreProtocol | None,
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
    right_artifact = effective_config_artifact_port.get_by_run_id(
        right_manifest.run_id
    )
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


def resolve_verify_verdict(
    *,
    manifest_classification: str,
    manifest_semantic_equivalent: bool,
    effective_config_semantic_equivalent: bool,
    missing_evidence: tuple[str, ...],
    occurrence_only: bool,
) -> str:
    """Return final verification verdict from manifest and effective-config evidence."""
    if missing_evidence:
        return "missing_replay_evidence"
    if not manifest_semantic_equivalent:
        return "semantic_drift"
    if not effective_config_semantic_equivalent:
        return "effective_config_semantic_drift"
    if occurrence_only or manifest_classification == "occurrence_only":
        return "occurrence_only_replay_verified"
    return "cross_store_replay_verified"


def parse_run_id(identifier: str) -> RunID | None:
    """Parse UUID-like run identifiers safely."""
    try:
        return RunID(UUID(identifier))
    except (TypeError, ValueError):
        return None


def json_equal(left: object, right: object) -> bool:
    """Compare nested payloads using canonical JSON normalization."""
    return json.dumps(left, sort_keys=True, default=str) == json.dumps(
        right,
        sort_keys=True,
        default=str,
    )
