"""Canonical control-plane service seams.

Responsibility-focused subpackage facades are available under:
`manifest`, `ledger`, `replay`, `effective_config`, and `workflow`.
The package root remains the compatibility-preserving lazy export surface.
"""

from __future__ import annotations

from bioetl.application.services.control_plane._lazy_export_facade import (
    install_lazy_export_facade,
)

_LAZY_ATTR_EXPORTS = {
    "EffectiveConfigService": (
        "bioetl.application.services.control_plane.effective_config.service",
        "EffectiveConfigService",
    ),
    "ForensicRunDiffResult": (
        "bioetl.application.services.control_plane.forensic_diff_service",
        "ForensicRunDiffResult",
    ),
    "ForensicRunDiffService": (
        "bioetl.application.services.control_plane.forensic_diff_service",
        "ForensicRunDiffService",
    ),
    "HistoricalReplayCertificationResult": (
        "bioetl.application.services.control_plane.replay.historical_certification_service",
        "HistoricalReplayCertificationResult",
    ),
    "HistoricalReplayCertificationService": (
        "bioetl.application.services.control_plane.replay.historical_certification_service",
        "HistoricalReplayCertificationService",
    ),
    "HistoricalReplaySnapshotCertification": (
        "bioetl.application.services.control_plane.replay.historical_certification_service",
        "HistoricalReplaySnapshotCertification",
    ),
    "RunLedgerService": (
        "bioetl.application.services.control_plane.ledger.service",
        "RunLedgerService",
    ),
    "RunManifestCreateSpec": (
        "bioetl.application.services.control_plane.manifest.service",
        "RunManifestCreateSpec",
    ),
    "RunManifestDiffEntry": (
        "bioetl.application.services.control_plane.manifest.inspection_service",
        "RunManifestDiffEntry",
    ),
    "RunManifestDiffResult": (
        "bioetl.application.services.control_plane.manifest.inspection_service",
        "RunManifestDiffResult",
    ),
    "RunManifestInspectionResult": (
        "bioetl.application.services.control_plane.manifest.inspection_service",
        "RunManifestInspectionResult",
    ),
    "RunManifestInspectionService": (
        "bioetl.application.services.control_plane.manifest.inspection_service",
        "RunManifestInspectionService",
    ),
    "RunManifestService": (
        "bioetl.application.services.control_plane.manifest.service",
        "RunManifestService",
    ),
    "RunManifestVerifyResult": (
        "bioetl.application.services.control_plane.manifest.inspection_service",
        "RunManifestVerifyResult",
    ),
    "RunReplayBundleDescriptorRecord": (
        "bioetl.application.services.control_plane.replay.bundle_descriptor_service",
        "RunReplayBundleDescriptorRecord",
    ),
    "WorkflowExecutionService": (
        "bioetl.application.services.control_plane.workflow.execution_service",
        "WorkflowExecutionService",
    ),
    "WorkflowInspectionResult": (
        "bioetl.application.services.control_plane.workflow.inspection_service",
        "WorkflowInspectionResult",
    ),
    "WorkflowInspectionService": (
        "bioetl.application.services.control_plane.workflow.inspection_service",
        "WorkflowInspectionService",
    ),
    "WorkflowLedgerService": (
        "bioetl.application.services.control_plane.workflow.ledger_service",
        "WorkflowLedgerService",
    ),
    "WorkflowManifestCreateSpec": (
        "bioetl.application.services.control_plane.workflow.manifest_models",
        "WorkflowManifestCreateSpec",
    ),
    "WorkflowManifestService": (
        "bioetl.application.services.control_plane.workflow.manifest_service",
        "WorkflowManifestService",
    ),
    "build_diagnostics_summary": (
        "bioetl.application.services.control_plane.manifest.diagnostics",
        "build_diagnostics_summary",
    ),
    "build_run_replay_bundle_descriptor": (
        "bioetl.application.services.control_plane.replay.bundle_descriptor_service",
        "build_run_replay_bundle_descriptor",
    ),
}

install_lazy_export_facade(globals(), __name__, _LAZY_ATTR_EXPORTS)

__all__: list[str]
