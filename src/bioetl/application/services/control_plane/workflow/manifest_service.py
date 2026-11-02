"""Application service for immutable workflow-manifest creation."""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime

from bioetl.application.services.control_plane.workflow.manifest_models import (
    WorkflowManifestCreateSpec as WorkflowManifestCreateSpec,
)
from bioetl.domain.context_time import ClockLike, resolve_manifest_created_at
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
    {
        "resume_last",
        "resume_manifest_id",
        "resume_run_id",
        "force_steps",
        "repair_steps",
    }
)


def _missing_manifest_id_factory() -> str:
    raise RuntimeError("manifest_id_factory must be supplied by composition root")


@dataclass(slots=True, kw_only=True)
class WorkflowManifestService:
    """Create and persist immutable workflow manifests."""

    manifest_port: WorkflowManifestPort
    clock: ClockLike | None = None
    created_at_factory: Callable[[], datetime] | None = None
    schema_version: str = "1.0"
    _manifest_id_factory: Callable[[], str] = field(
        default_factory=lambda: _missing_manifest_id_factory
    )
    # RF-004: optional post-save locator publisher (Composition-injected).
    # May return an outcome object with ``code``/``detail`` for soft diagnostics.
    evidence_location_register: Callable[[WorkflowManifest], object | None] | None = (
        None
    )

    def _resolve_created_at(self) -> datetime:
        """Resolve workflow manifest creation time through the configured seam."""
        return resolve_manifest_created_at(
            clock=self.clock,
            created_at_factory=self.created_at_factory,
        )

    def create_manifest(self, request: WorkflowManifestCreateSpec) -> WorkflowManifest:
        """Build fingerprinted workflow manifest and persist it through the port."""
        launch_context, defaults, steps = self._isolated_manifest_payloads(request)
        manifest = WorkflowManifest(
            manifest_id=self._manifest_id_factory(),
            workflow_run_id=request.workflow_run_id,
            execution_fingerprint=self._fingerprint_isolated_payloads(
                request,
                launch_context=launch_context,
                defaults=defaults,
                steps=steps,
            ),
            schema_version=self.schema_version,
            created_at=self._resolve_created_at(),
            workflow_name=request.config.name,
            workflow_version=request.config.version,
            launch_context=launch_context,
            defaults=defaults,
            selected_step_ids=request.config.topological_step_ids,
            steps=steps,
            resumed_from_manifest_id=request.resumed_from_manifest_id,
        )
        self.manifest_port.save(manifest)
        if self.evidence_location_register is not None:
            try:
                outcome = self.evidence_location_register(manifest)
            except Exception as exc:
                # Locator publication must not mask workflow processing success.
                from bioetl.application.services.control_plane.evidence_location.registration import (
                    record_registration_soft_failure_observation,
                )

                record_registration_soft_failure_observation(
                    code="registration_exception",
                    detail=f"{type(exc).__name__}: {exc}",
                    facts={
                        "kind": "workflow",
                        "owner": str(manifest.workflow_name),
                        "run_id": str(manifest.workflow_run_id),
                    },
                )
            else:
                # Callbacks may return an outcome or None; surface non-success.
                if outcome is not None:
                    from bioetl.application.services.control_plane.evidence_location.registration import (
                        record_registration_soft_failure_observation,
                    )

                    code = getattr(outcome, "code", None)
                    if isinstance(code, str):
                        record_registration_soft_failure_observation(
                            code=code,
                            detail=getattr(outcome, "detail", None),
                            facts={
                                "kind": "workflow",
                                "owner": str(manifest.workflow_name),
                                "run_id": str(manifest.workflow_run_id),
                                "revision": getattr(outcome, "revision", None),
                            },
                        )
        return manifest

    def compute_execution_fingerprint(self, request: WorkflowManifestCreateSpec) -> str:
        """Compute the canonical workflow execution fingerprint."""
        launch_context, defaults, steps = self._isolated_manifest_payloads(request)
        return self._fingerprint_isolated_payloads(
            request,
            launch_context=launch_context,
            defaults=defaults,
            steps=steps,
        )

    def _isolated_manifest_payloads(
        self,
        request: WorkflowManifestCreateSpec,
    ) -> tuple[dict[str, object], dict[str, object], tuple[WorkflowManifestStep, ...]]:
        """Copy nested launch/default/step payloads before fingerprinting."""
        return (
            copy.deepcopy(dict(request.launch_context)),
            copy.deepcopy(request.config.defaults.to_mapping()),
            self._serialize_steps(request.config),
        )

    def _fingerprint_isolated_payloads(
        self,
        request: WorkflowManifestCreateSpec,
        *,
        launch_context: dict[str, object],
        defaults: dict[str, object],
        steps: tuple[WorkflowManifestStep, ...],
    ) -> str:
        payload = {
            "workflow_name": request.config.name,
            "workflow_version": request.config.version,
            "launch_context": self._normalize_fingerprint_launch_context(
                launch_context
            ),
            "defaults": defaults,
            "selected_step_ids": list(request.config.topological_step_ids),
            "steps": [step.to_dict() for step in steps],
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
                    copy.deepcopy(step.run_options.to_mapping())
                    if isinstance(step, WorkflowStepConfig)
                    else None
                ),
                config=(
                    copy.deepcopy(step.config)
                    if isinstance(step, TransformStepConfig)
                    else (
                        {"reference_cohort": asdict(step.reference_cohort)}
                        if step.reference_cohort
                        else None
                    )
                ),
            )
            for step in config.steps
        )
