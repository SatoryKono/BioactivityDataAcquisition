"""Lazy composition seams for declarative workflow CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.workflow.inspection_service import (
        WorkflowInspectionService,
    )
    from bioetl.application.services.workflow.control_plane.execution_service import (
        WorkflowExecutionService,
    )
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.workflow import WorkflowConfig

__all__ = [
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "load_workflow_config",
]


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load one declarative workflow config through composition seams."""
    from bioetl.composition.control_plane_service_access import (
        load_workflow_config as _impl,
    )

    return _impl(name)


def get_workflow_execution_service(
    registry: PipelineRegistry | None = None,
) -> WorkflowExecutionService:
    """Resolve workflow execution orchestration through composition seams."""
    from bioetl.composition.control_plane_service_access import (
        get_workflow_execution_service as _impl,
    )

    return _impl(registry=registry)


def get_workflow_inspection_service() -> WorkflowInspectionService:
    """Resolve workflow inspection through composition seams."""
    from bioetl.composition.control_plane_service_access import (
        get_workflow_inspection_service as _impl,
    )

    return _impl()
