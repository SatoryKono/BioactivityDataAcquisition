"""Application service for immutable workflow-manifest creation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol
from uuid import uuid4

from bioetl.application.services.control_plane.workflow_manifest_models import (
    WorkflowManifestCreateSpec,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP
from bioetl.domain.control_plane import WorkflowManifest, WorkflowManifestStep
from bioetl.domain.normalization import compute_execution_identity_fingerprint
from bioetl.domain.ports import WorkflowManifestPort
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)

__all__ = ["WorkflowManifestCreateSpec", "WorkflowManifestService"]

_EXECUTION_FINGERPRINT_IGNORED_LAUNCH_KEYS = frozenset(
    {"resume_last", "force_steps", "repair_steps"}
)


class _ClockLike(Protocol):
    def now(self) -> datetime: ...


@dataclass(slots=True)
class WorkflowManifestService:
    """Create and persist immutable workflow manifests."""

    manifest_port: WorkflowManifestPort
    clock: _ClockLike | None = None
    created_at_factory: Callable[[], datetime] | None = None
    schema_version: str = "1.0"
    _manifest_id_factory: Callable[[], str] = field(
        default_factory=lambda: lambda: str(uuid4())
    )

    def create_manifest(self, request: WorkflowManifestCreateSpec) -> WorkflowManifest:
        """Build fingerprinted workflow manifest and persist it through the port."""
        manifest = WorkflowManifest(
            manifest_id=self._manifest_id_factory(),
            workflow_run_id=request.workflow_run_id,
            execution_fingerprint=self.compute_execution_fingerprint(request),
            schema_version=self.schema_version,
            created_at=self._resolve_created_at(),
            workflow_name=request.config.name,
            workflow_version=request.config.version,
            launch_context=dict(request.launch_context),
            defaults=request.config.defaults.to_mapping(),
            selected_step_ids=request.config.topological_step_ids,
            steps=self._serialize_steps(request.config),
            resumed_from_manifest_id=request.resumed_from_manifest_id,
        )
        self.manifest_port.save(manifest)
        return manifest

    def compute_execution_fingerprint(self, request: WorkflowManifestCreateSpec) -> str:
        """Compute the canonical workflow execution fingerprint."""
        payload = {
            "workflow_name": request.config.name,
            "workflow_version": request.config.version,
            "launch_context": self._normalize_fingerprint_launch_context(
                request.launch_context
            ),
            "defaults": request.config.defaults.to_mapping(),
            "selected_step_ids": list(request.config.topological_step_ids),
            "steps": [step.to_dict() for step in self._serialize_steps(request.config)],
        }
        return compute_execution_identity_fingerprint(payload)

    def _normalize_fingerprint_launch_context(
        self,
        launch_context: dict[str, object],
    ) -> dict[str, object]:
        return {
            key: value
            for key, value in launch_context.items()
            if key not in _EXECUTION_FINGERPRINT_IGNORED_LAUNCH_KEYS
        }

    def _serialize_steps(
        self,
        config: WorkflowConfig,
    ) -> tuple[WorkflowManifestStep, ...]:
        return tuple(
            WorkflowManifestStep(
                step_id=step.step_id,
                kind=(
                    "pipeline" if isinstance(step, WorkflowStepConfig) else "transform"
                ),
                depends_on=step.depends_on,
                pipeline_name=(
                    step.pipeline_name if isinstance(step, WorkflowStepConfig) else None
                ),
                transform_name=(
                    step.transform_name
                    if isinstance(step, TransformStepConfig)
                    else None
                ),
                run_options=(
                    step.run_options.to_mapping()
                    if isinstance(step, WorkflowStepConfig)
                    else None
                ),
                config=step.config if isinstance(step, TransformStepConfig) else None,
            )
            for step in config.steps
        )

    def _resolve_created_at(self) -> datetime:
        if self.clock is not None:
            return self.clock.now()
        if self.created_at_factory is not None:
            return self.created_at_factory()
        return MISSING_RUNTIME_TIMESTAMP
