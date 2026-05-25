"""Canonical control-plane service seams.

Responsibility-focused subpackage facades are available under:
`manifest`, `ledger`, `replay`, `effective_config`, and `workflow`.
The package root remains the compatibility-preserving lazy export surface.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "EffectiveConfigService",
    "ForensicRunDiffResult",
    "ForensicRunDiffService",
    "HistoricalReplayCertificationResult",
    "HistoricalReplayCertificationService",
    "HistoricalReplaySnapshotCertification",
    "RunLedgerService",
    "RunManifestCreateSpec",
    "RunManifestDiffEntry",
    "RunManifestDiffResult",
    "RunManifestInspectionResult",
    "RunManifestInspectionService",
    "RunManifestService",
    "RunManifestVerifyResult",
    "RunReplayBundleDescriptorRecord",
    "WorkflowExecutionService",
    "WorkflowInspectionResult",
    "WorkflowInspectionService",
    "WorkflowLedgerService",
    "WorkflowManifestCreateSpec",
    "WorkflowManifestService",
    "build_diagnostics_summary",
    "build_run_replay_bundle_descriptor",
]

_LAZY_ATTR_EXPORTS: dict[str, tuple[str, str]] = {
    "EffectiveConfigService": (
        "bioetl.application.services.control_plane.effective_config_service",
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
        "bioetl.application.services.control_plane.historical_replay_certification_service",
        "HistoricalReplayCertificationResult",
    ),
    "HistoricalReplayCertificationService": (
        "bioetl.application.services.control_plane.historical_replay_certification_service",
        "HistoricalReplayCertificationService",
    ),
    "HistoricalReplaySnapshotCertification": (
        "bioetl.application.services.control_plane.historical_replay_certification_service",
        "HistoricalReplaySnapshotCertification",
    ),
    "RunLedgerService": (
        "bioetl.application.services.control_plane.run_ledger_service",
        "RunLedgerService",
    ),
    "RunManifestCreateSpec": (
        "bioetl.application.services.control_plane.run_manifest_service",
        "RunManifestCreateSpec",
    ),
    "RunManifestDiffEntry": (
        "bioetl.application.services.control_plane.run_manifest_inspection_service",
        "RunManifestDiffEntry",
    ),
    "RunManifestDiffResult": (
        "bioetl.application.services.control_plane.run_manifest_inspection_service",
        "RunManifestDiffResult",
    ),
    "RunManifestInspectionResult": (
        "bioetl.application.services.control_plane.run_manifest_inspection_service",
        "RunManifestInspectionResult",
    ),
    "RunManifestInspectionService": (
        "bioetl.application.services.control_plane.run_manifest_inspection_service",
        "RunManifestInspectionService",
    ),
    "RunManifestService": (
        "bioetl.application.services.control_plane.run_manifest_service",
        "RunManifestService",
    ),
    "RunManifestVerifyResult": (
        "bioetl.application.services.control_plane.run_manifest_inspection_service",
        "RunManifestVerifyResult",
    ),
    "RunReplayBundleDescriptorRecord": (
        "bioetl.application.services.control_plane.replay_bundle_descriptor_service",
        "RunReplayBundleDescriptorRecord",
    ),
    "WorkflowExecutionService": (
        "bioetl.application.services.control_plane.workflow_execution_service",
        "WorkflowExecutionService",
    ),
    "WorkflowInspectionResult": (
        "bioetl.application.services.control_plane.workflow_inspection_service",
        "WorkflowInspectionResult",
    ),
    "WorkflowInspectionService": (
        "bioetl.application.services.control_plane.workflow_inspection_service",
        "WorkflowInspectionService",
    ),
    "WorkflowLedgerService": (
        "bioetl.application.services.control_plane.workflow_ledger_service",
        "WorkflowLedgerService",
    ),
    "WorkflowManifestCreateSpec": (
        "bioetl.application.services.control_plane.workflow_manifest_models",
        "WorkflowManifestCreateSpec",
    ),
    "WorkflowManifestService": (
        "bioetl.application.services.control_plane.workflow_manifest_service",
        "WorkflowManifestService",
    ),
    "build_diagnostics_summary": (
        "bioetl.application.services.control_plane.run_manifest_diagnostics",
        "build_diagnostics_summary",
    ),
    "build_run_replay_bundle_descriptor": (
        "bioetl.application.services.control_plane.replay_bundle_descriptor_service",
        "build_run_replay_bundle_descriptor",
    ),
}


def __getattr__(name: str) -> object:
    """Lazily expose control-plane services without importing the full family."""
    try:
        module_name, attr_name = _LAZY_ATTR_EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable exports for shell introspection and help()."""
    return sorted(set(globals()) | set(__all__))
