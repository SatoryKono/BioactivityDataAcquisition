"""Canonical control-plane service seams.

Responsibility-focused subpackage facades are available under:
`manifest`, `ledger`, `replay`, `effective_config`, `forensic`, and `workflow`.
The package root remains the compatibility-preserving lazy export surface.
"""

from __future__ import annotations

from types import MappingProxyType

from bioetl.application.services.control_plane._lazy_export_facade import (
    install_lazy_export_facade,
)

RESPONSIBILITY_SEAMS = MappingProxyType(
    {
        "effective_config": (
            "Configuration materialization and effective-config serialization."
        ),
        "forensic": "Operator-facing replay and manifest diff interpretation.",
        "ledger": "Run-ledger persistence and event ownership.",
        "manifest": "Run-manifest creation, inspection, and diagnostics ownership.",
        "replay": "Historical replay certification and replay-bundle ownership.",
        "workflow": "Workflow orchestration, manifests, and execution inspection.",
    }
)

_LAZY_ATTR_EXPORTS = {
    "EffectiveConfigService": (
        "bioetl.application.services.control_plane.effective_config",
        "EffectiveConfigService",
    ),
    "ForensicRunDiffResult": (
        "bioetl.application.services.control_plane.forensic",
        "ForensicRunDiffResult",
    ),
    "ForensicRunDiffService": (
        "bioetl.application.services.control_plane.forensic",
        "ForensicRunDiffService",
    ),
    "HistoricalReplayCertificationResult": (
        "bioetl.application.services.control_plane.replay",
        "HistoricalReplayCertificationResult",
    ),
    "HistoricalReplayCertificationService": (
        "bioetl.application.services.control_plane.replay",
        "HistoricalReplayCertificationService",
    ),
    "HistoricalReplaySnapshotCertification": (
        "bioetl.application.services.control_plane.replay",
        "HistoricalReplaySnapshotCertification",
    ),
    "RunLedgerService": (
        "bioetl.application.services.control_plane.ledger",
        "RunLedgerService",
    ),
    "RunManifestCreateSpec": (
        "bioetl.application.services.control_plane.manifest",
        "RunManifestCreateSpec",
    ),
    "RunManifestDiffEntry": (
        "bioetl.application.services.control_plane.manifest",
        "RunManifestDiffEntry",
    ),
    "RunManifestDiffResult": (
        "bioetl.application.services.control_plane.manifest",
        "RunManifestDiffResult",
    ),
    "RunManifestInspectionResult": (
        "bioetl.application.services.control_plane.manifest",
        "RunManifestInspectionResult",
    ),
    "RunManifestInspectionService": (
        "bioetl.application.services.control_plane.manifest",
        "RunManifestInspectionService",
    ),
    "RunManifestService": (
        "bioetl.application.services.control_plane.manifest",
        "RunManifestService",
    ),
    "RunManifestVerifyResult": (
        "bioetl.application.services.control_plane.manifest",
        "RunManifestVerifyResult",
    ),
    "RunReplayBundleDescriptorRecord": (
        "bioetl.application.services.control_plane.replay",
        "RunReplayBundleDescriptorRecord",
    ),
    "WorkflowExecutionService": (
        "bioetl.application.services.control_plane.workflow",
        "WorkflowExecutionService",
    ),
    "WorkflowInspectionResult": (
        "bioetl.application.services.control_plane.workflow",
        "WorkflowInspectionResult",
    ),
    "WorkflowInspectionService": (
        "bioetl.application.services.control_plane.workflow",
        "WorkflowInspectionService",
    ),
    "WorkflowLedgerService": (
        "bioetl.application.services.control_plane.workflow",
        "WorkflowLedgerService",
    ),
    "WorkflowManifestCreateSpec": (
        "bioetl.application.services.control_plane.workflow",
        "WorkflowManifestCreateSpec",
    ),
    "WorkflowManifestService": (
        "bioetl.application.services.control_plane.workflow",
        "WorkflowManifestService",
    ),
    "build_diagnostics_summary": (
        "bioetl.application.services.control_plane.manifest.diagnostics",
        "build_diagnostics_summary",
    ),
    "build_run_replay_bundle_descriptor": (
        "bioetl.application.services.control_plane.replay",
        "build_run_replay_bundle_descriptor",
    ),
}

install_lazy_export_facade(globals(), __name__, _LAZY_ATTR_EXPORTS)

__all__: list[str]
