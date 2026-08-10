"""Run-manifest application service seam.

Public names are resolved lazily so this package facade does not contribute
static fan-in to leaf collaborator modules (ARCH-REF-04 / #6818).
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "ControlPlaneIntegrityMetricsService",
    "ManifestLedgerIntegrityScope",
    "RunManifestCreateSpec",
    "RunManifestDiffEntry",
    "RunManifestDiffResult",
    "RunManifestInspectionResult",
    "RunManifestInspectionService",
    "RunManifestService",
    "RunManifestVerifyResult",
]

_INSPECTION_MODELS = (
    "bioetl.application.services.control_plane.manifest.inspection_models"
)
_EXPORTS: dict[str, tuple[str, str]] = {
    "ControlPlaneIntegrityMetricsService": (
        "bioetl.application.services.control_plane.manifest.integrity_metrics",
        "ControlPlaneIntegrityMetricsService",
    ),
    "ManifestLedgerIntegrityScope": (
        "bioetl.application.services.control_plane.manifest.integrity_metrics",
        "ManifestLedgerIntegrityScope",
    ),
    "RunManifestCreateSpec": (
        "bioetl.application.services.control_plane.manifest.models",
        "RunManifestCreateSpec",
    ),
    "RunManifestDiffEntry": (
        _INSPECTION_MODELS,
        "RunManifestDiffEntry",
    ),
    "RunManifestDiffResult": (
        _INSPECTION_MODELS,
        "RunManifestDiffResult",
    ),
    "RunManifestInspectionResult": (
        _INSPECTION_MODELS,
        "RunManifestInspectionResult",
    ),
    "RunManifestVerifyResult": (
        _INSPECTION_MODELS,
        "RunManifestVerifyResult",
    ),
    "RunManifestInspectionService": (
        "bioetl.application.services.control_plane.manifest.inspection_service",
        "RunManifestInspectionService",
    ),
    "RunManifestService": (
        "bioetl.application.services.control_plane.manifest.service",
        "RunManifestService",
    ),
}


def __getattr__(name: str) -> Any:  # Any: lazy module exports have heterogeneous types.
    """Lazily resolve public run-manifest symbols."""
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr = target
    value = getattr(import_module(module_name), attr)
    globals()[name] = value
    return value
