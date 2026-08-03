"""Data models used by the run manifest inspection service."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import UUID

from bioetl.application.services.control_plane.manifest.inspection_result_model import (
    RunManifestInspectionResult as RunManifestInspectionResult,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID


class RunManifestInspectionCorruptionError(ValueError):
    """Raised when manifest storage is structurally corrupted during inspection."""

    def __init__(self, identifier: str, reason: str) -> None:
        self.identifier = identifier
        self.reason = reason
        super().__init__(
            f"Run manifest store corruption while resolving {identifier!r}: {reason}"
        )


@dataclass(frozen=True, slots=True)
class RunManifestDiffEntry:
    """One top-level manifest field difference."""

    field: str
    left: object
    right: object

    def to_dict(self) -> dict[str, object]:
        """Return JSON/YAML-safe payload for CLI presentation."""
        return {"field": self.field, "left": self.left, "right": self.right}


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


@dataclass(frozen=True, slots=True)
class RunManifestVerifyResult:
    """Cross-store replay evidence verification for two resolved manifests."""

    left_manifest_id: str
    right_manifest_id: str
    left_run_id: str
    right_run_id: str
    verdict: str
    verified: bool
    semantic_equivalent: bool
    occurrence_only: bool
    manifest_diff: dict[str, object]
    effective_config: dict[str, object]
    missing_evidence: tuple[str, ...] = ()
    left_authoritative_replay_dossier: dict[str, object] = field(default_factory=dict)
    right_authoritative_replay_dossier: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return JSON/YAML-safe payload for CLI presentation."""
        return {
            "left_manifest_id": self.left_manifest_id,
            "right_manifest_id": self.right_manifest_id,
            "left_run_id": self.left_run_id,
            "right_run_id": self.right_run_id,
            "verdict": self.verdict,
            "verified": self.verified,
            "semantic_equivalent": self.semantic_equivalent,
            "occurrence_only": self.occurrence_only,
            "missing_evidence": list(self.missing_evidence),
            "manifest_diff": self.manifest_diff,
            "effective_config": self.effective_config,
            "left_authoritative_replay_dossier": (
                self.left_authoritative_replay_dossier
            ),
            "right_authoritative_replay_dossier": (
                self.right_authoritative_replay_dossier
            ),
        }


_RUN_MANIFEST_INSPECTION_MODEL_EXPORTS = (
    "RunManifestDiffEntry",
    "RunManifestDiffResult",
    "RunManifestInspectionCorruptionError",
    "RunManifestInspectionResult",
    "RunManifestVerifyResult",
    "effective_config_artifact_anchor",
    "effective_config_missing_evidence",
    "json_equal",
    "manifest_effective_config_anchor",
    "parse_run_id",
    "resolve_verify_verdict",
)

__all__ = list(_RUN_MANIFEST_INSPECTION_MODEL_EXPORTS)


def effective_config_missing_evidence(
    *,
    left_artifact: dict[str, object] | None,
    right_artifact: dict[str, object] | None,
    left_occurrence: dict[str, object] | None,
    right_occurrence: dict[str, object] | None,
) -> tuple[str, ...]:
    """Return missing-evidence codes for effective-config store verification."""
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


def manifest_effective_config_anchor(manifest: RunManifest) -> dict[str, object]:
    """Project the effective-config anchor fields from a run manifest."""
    code_provenance = manifest.code_provenance
    return {
        "artifact_id": code_provenance.effective_config_artifact_id,
        "effective_config_hash": code_provenance.effective_config_hash,
    }


def effective_config_artifact_anchor(
    artifact: dict[str, object] | None,
) -> dict[str, object]:
    """Project the effective-config anchor fields from a stored artifact payload."""
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
