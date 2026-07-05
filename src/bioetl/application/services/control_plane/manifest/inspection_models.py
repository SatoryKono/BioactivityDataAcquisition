"""Data models used by the run manifest inspection service."""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.application.services.control_plane.manifest.inspection_result_model import (  # noqa: F401
    RunManifestInspectionResult,
)


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
)

__all__ = list(_RUN_MANIFEST_INSPECTION_MODEL_EXPORTS)
