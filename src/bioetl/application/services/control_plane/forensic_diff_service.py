"""Application service for operator-facing forensic run diffs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from bioetl.application.services.control_plane.forensic.diagnostics_support import (
    _artifact_completeness,
    _artifact_refs,
    _checkpoint_compatibility_payload,
    _diagnostic_snapshot,
    _forensic_diff_payload,
    _lineage_closure_payload,
    _missing_evidence,
    _replay_capability_payload,
    _string_list,
)
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestDiffResult,
    RunManifestInspectionResult,
    RunManifestInspectionService,
)
from bioetl.domain.ports import (
    ArtifactByteComparisonPort,
    RunLedgerPort,
    RunManifestPort,
)

__all__ = [
    "ForensicRunDiffResult",
    "ForensicRunDiffService",
]


def _inspection_service_factory_from_ports(
    manifest_port: RunManifestPort,
    ledger_port: RunLedgerPort | None,
    provided_factory: Callable[[], RunManifestInspectionService] | None,
) -> Callable[[], RunManifestInspectionService]:
    """Resolve the inspection-service factory without assembling in method bodies."""
    if provided_factory is not None:
        return provided_factory
    return lambda: RunManifestInspectionService(
        manifest_port=manifest_port,
        ledger_port=ledger_port,
    )


@dataclass(frozen=True, slots=True)
class ForensicRunDiffResult:
    """Unified forensic diff across manifest, replay, and artifact evidence."""

    left_manifest_id: str
    right_manifest_id: str
    manifest_diff: RunManifestDiffResult
    forensic_diff: dict[str, object]
    left_diagnostics: dict[str, object] = field(default_factory=dict)
    right_diagnostics: dict[str, object] = field(default_factory=dict)
    replay_capability: dict[str, object] = field(default_factory=dict)
    checkpoint_compatibility: dict[str, object] = field(default_factory=dict)
    artifact_byte_equivalence: dict[str, object] = field(default_factory=dict)
    artifact_completeness: dict[str, dict[str, object]] = field(default_factory=dict)
    lineage_closure: dict[str, dict[str, object]] = field(default_factory=dict)
    missing_evidence: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return JSON/YAML-safe payload for CLI/API presentation."""
        semantic_difference_fields = _string_list(
            self.manifest_diff.semantic_difference_fields
        )
        occurrence_difference_fields = _string_list(
            self.manifest_diff.occurrence_difference_fields
        )
        noncanonical_difference_fields = _string_list(
            self.manifest_diff.noncanonical_difference_fields
        )
        return {
            "left_manifest_id": self.left_manifest_id,
            "right_manifest_id": self.right_manifest_id,
            "classification": self.manifest_diff.classification,
            "semantic_equivalent": self.manifest_diff.semantic_equivalent,
            "occurrence_only": self.manifest_diff.occurrence_only,
            "semantic_difference_fields": semantic_difference_fields,
            "occurrence_difference_fields": occurrence_difference_fields,
            "noncanonical_difference_fields": noncanonical_difference_fields,
            "replay_relationship": self.manifest_diff.replay_relationship,
            "forensic_diff": self.forensic_diff,
            "left_diagnostics": self.left_diagnostics,
            "right_diagnostics": self.right_diagnostics,
            "replay_capability": self.replay_capability,
            "checkpoint_compatibility": self.checkpoint_compatibility,
            "artifact_byte_equivalence": self.artifact_byte_equivalence,
            "artifact_completeness": self.artifact_completeness,
            "lineage_closure": self.lineage_closure,
            "missing_evidence": {
                side: list(items) for side, items in self.missing_evidence.items()
            },
            "manifest_diff": self.manifest_diff.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ForensicRunDiffService:
    """Build unified forensic diffs through existing control-plane ports."""

    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort | None = None
    inspection_service_factory: Callable[[], RunManifestInspectionService] | None = None
    artifact_byte_comparison_port: ArtifactByteComparisonPort | None = None

    def compare(
        self,
        left_identifier: str,
        right_identifier: str,
    ) -> ForensicRunDiffResult:
        """Compare two run or manifest identifiers using existing inspection seams."""
        inspection = _inspection_service_factory_from_ports(
            self.manifest_port,
            self.ledger_port,
            self.inspection_service_factory,
        )()
        left = inspection.show(left_identifier)
        right = inspection.show(right_identifier)
        manifest_diff = inspection.diff(left_identifier, right_identifier)
        forensic_diff = _forensic_diff_payload(manifest_diff)
        artifact_byte_equivalence = self._build_artifact_byte_equivalence(
            left=left,
            right=right,
        )
        return ForensicRunDiffResult(
            left_manifest_id=left.manifest.manifest_id,
            right_manifest_id=right.manifest.manifest_id,
            manifest_diff=manifest_diff,
            forensic_diff=forensic_diff,
            left_diagnostics=_diagnostic_snapshot(left),
            right_diagnostics=_diagnostic_snapshot(right),
            replay_capability=_replay_capability_payload(left=left, right=right),
            checkpoint_compatibility=_checkpoint_compatibility_payload(
                forensic_diff,
            ),
            artifact_byte_equivalence=artifact_byte_equivalence,
            artifact_completeness={
                "left": _artifact_completeness(left),
                "right": _artifact_completeness(right),
            },
            lineage_closure={
                "left": _lineage_closure_payload(left),
                "right": _lineage_closure_payload(right),
            },
            missing_evidence={
                "left": _missing_evidence(left),
                "right": _missing_evidence(right),
            },
        )

    def _build_artifact_byte_equivalence(
        self,
        *,
        left: RunManifestInspectionResult,
        right: RunManifestInspectionResult,
    ) -> dict[str, object]:
        """Return byte-level artifact equivalence when a comparison port exists."""
        left_refs = _artifact_refs(left.diagnostics)
        right_refs = _artifact_refs(right.diagnostics)
        if self.artifact_byte_comparison_port is None:
            return {
                "available": False,
                "equivalent": None,
                "compared_artifacts": [],
                "missing_artifacts": [],
                "mismatched_artifacts": [],
                "comparison_scope": "unavailable_no_port",
            }
        if not left_refs or not right_refs:
            return {
                "available": False,
                "equivalent": None,
                "compared_artifacts": [],
                "missing_artifacts": [],
                "mismatched_artifacts": [],
                "comparison_scope": "unavailable_missing_refs",
            }
        return dict(
            self.artifact_byte_comparison_port.compare_artifacts(left_refs, right_refs)
        )
