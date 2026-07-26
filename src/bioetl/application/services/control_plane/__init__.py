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

_EFFECTIVE_CONFIG_MODULE = "bioetl.application.services.control_plane.effective_config"
_FORENSIC_MODULE = "bioetl.application.services.control_plane.forensic"
_LEDGER_MODULE = "bioetl.application.services.control_plane.ledger"
_MANIFEST_MODULE = "bioetl.application.services.control_plane.manifest"
_MANIFEST_DIAGNOSTICS_MODULE = (
    "bioetl.application.services.control_plane.manifest.diagnostics"
)
_REPLAY_MODULE = "bioetl.application.services.control_plane.replay"
_WORKFLOW_MODULE = "bioetl.application.services.control_plane.workflow"

_LAZY_ATTR_EXPORTS = {
    "EffectiveConfigService": (
        _EFFECTIVE_CONFIG_MODULE,
        "EffectiveConfigService",
    ),
    "ForensicRunDiffResult": (
        _FORENSIC_MODULE,
        "ForensicRunDiffResult",
    ),
    "ForensicRunDiffService": (
        _FORENSIC_MODULE,
        "ForensicRunDiffService",
    ),
    "HistoricalReplayCertificationResult": (
        _REPLAY_MODULE,
        "HistoricalReplayCertificationResult",
    ),
    "HistoricalReplayCertificationService": (
        _REPLAY_MODULE,
        "HistoricalReplayCertificationService",
    ),
    "HistoricalReplaySnapshotCertification": (
        _REPLAY_MODULE,
        "HistoricalReplaySnapshotCertification",
    ),
    "RunLedgerService": (
        _LEDGER_MODULE,
        "RunLedgerService",
    ),
    "RunManifestCreateSpec": (
        _MANIFEST_MODULE,
        "RunManifestCreateSpec",
    ),
    "RunManifestDiffEntry": (
        _MANIFEST_MODULE,
        "RunManifestDiffEntry",
    ),
    "RunManifestDiffResult": (
        _MANIFEST_MODULE,
        "RunManifestDiffResult",
    ),
    "RunManifestInspectionResult": (
        _MANIFEST_MODULE,
        "RunManifestInspectionResult",
    ),
    "RunManifestInspectionService": (
        _MANIFEST_MODULE,
        "RunManifestInspectionService",
    ),
    "RunManifestService": (
        _MANIFEST_MODULE,
        "RunManifestService",
    ),
    "RunManifestVerifyResult": (
        _MANIFEST_MODULE,
        "RunManifestVerifyResult",
    ),
    "RunReplayBundleDescriptorRecord": (
        _REPLAY_MODULE,
        "RunReplayBundleDescriptorRecord",
    ),
    "WorkflowExecutionService": (
        _WORKFLOW_MODULE,
        "WorkflowExecutionService",
    ),
    "WorkflowInspectionResult": (
        _WORKFLOW_MODULE,
        "WorkflowInspectionResult",
    ),
    "WorkflowInspectionService": (
        _WORKFLOW_MODULE,
        "WorkflowInspectionService",
    ),
    "WorkflowLedgerService": (
        _WORKFLOW_MODULE,
        "WorkflowLedgerService",
    ),
    "WorkflowManifestCreateSpec": (
        _WORKFLOW_MODULE,
        "WorkflowManifestCreateSpec",
    ),
    "WorkflowManifestService": (
        _WORKFLOW_MODULE,
        "WorkflowManifestService",
    ),
    "build_diagnostics_summary": (
        _MANIFEST_DIAGNOSTICS_MODULE,
        "build_diagnostics_summary",
    ),
    "build_run_replay_bundle_descriptor": (
        _REPLAY_MODULE,
        "build_run_replay_bundle_descriptor",
    ),
}

install_lazy_export_facade(globals(), __name__, _LAZY_ATTR_EXPORTS)

__all__: list[str]
