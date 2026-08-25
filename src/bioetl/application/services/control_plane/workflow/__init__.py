"""Workflow control-plane application service seam."""

from __future__ import annotations

from bioetl.application.core.wiring.lazy_export_hooks import (
    install_lazy_export_facade,
)

# TD2-02: do not re-export ledger service/manifest spec; use modules or lazy facade.

_WORKFLOW_MODULE = "bioetl.application.services.control_plane.workflow"
_LAZY_ATTR_EXPORTS = {
    "WorkflowExecutionService": (
        f"{_WORKFLOW_MODULE}.execution_service",
        "WorkflowExecutionService",
    ),
    "WorkflowInspectionResult": (
        f"{_WORKFLOW_MODULE}.inspection_service",
        "WorkflowInspectionResult",
    ),
    "WorkflowInspectionService": (
        f"{_WORKFLOW_MODULE}.inspection_service",
        "WorkflowInspectionService",
    ),
    "WorkflowManifestService": (
        f"{_WORKFLOW_MODULE}.manifest_service",
        "WorkflowManifestService",
    ),
}

install_lazy_export_facade(globals(), __name__, _LAZY_ATTR_EXPORTS)

__all__: list[str]
