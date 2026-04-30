"""Application service for first-class workflow transform steps."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from inspect import isawaitable
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.domain.workflow import TransformStepConfig, WorkflowTransformSpec

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

__all__ = [
    "WorkflowTransformExecutionResult",
    "WorkflowTransformService",
    "should_skip_transform_step",
]

_WORKFLOW_STEP_EVENTS_TOTAL = "bioetl_workflow_step_events_total"
_WORKFLOW_STEP_DURATION_SECONDS = "bioetl_workflow_step_duration_seconds"
_STEP_KIND_TRANSFORM = "transform"


@dataclass(frozen=True, slots=True)
class WorkflowTransformExecutionResult:
    """Result of one workflow transform step execution."""

    step_id: str
    transform_name: str
    status: str
    fingerprint: str
    skipped: bool = False
    output: object | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class WorkflowTransformService:
    """Execute transform steps with deterministic fingerprint skip support."""

    registry: WorkflowTransformRegistry
    metrics: MetricsPort
    monotonic: Callable[[], float] = perf_counter

    async def run_step(
        self,
        *,
        workflow_name: str,
        step: TransformStepConfig,
        upstream_outputs: Mapping[str, object] | None = None,
        completed_fingerprints: Mapping[str, str] | None = None,
    ) -> WorkflowTransformExecutionResult:
        """Execute or skip a transform step according to its fingerprint."""
        spec = WorkflowTransformSpec.from_step(step)
        if should_skip_transform_step(
            spec,
            completed_fingerprints=completed_fingerprints,
        ):
            self._record_step_metrics(
                workflow_name=workflow_name,
                status="skipped",
                duration_seconds=0.0,
            )
            return WorkflowTransformExecutionResult(
                step_id=step.step_id,
                transform_name=step.transform_name,
                status="skipped",
                fingerprint=spec.fingerprint,
                skipped=True,
            )

        started = self.monotonic()
        try:
            executor = self.registry.get(step.transform_name)
            output = executor(spec, upstream_outputs or {})
            if isawaitable(output):
                output = await output
        except Exception as exc:
            self._record_step_metrics(
                workflow_name=workflow_name,
                status="failed",
                duration_seconds=self.monotonic() - started,
            )
            return WorkflowTransformExecutionResult(
                step_id=step.step_id,
                transform_name=step.transform_name,
                status="failed",
                fingerprint=spec.fingerprint,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        self._record_step_metrics(
            workflow_name=workflow_name,
            status="success",
            duration_seconds=self.monotonic() - started,
        )
        return WorkflowTransformExecutionResult(
            step_id=step.step_id,
            transform_name=step.transform_name,
            status="success",
            fingerprint=spec.fingerprint,
            output=output,
        )

    def _record_step_metrics(
        self,
        *,
        workflow_name: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        labels = {
            "workflow": workflow_name,
            "step_kind": _STEP_KIND_TRANSFORM,
            "status": status,
        }
        self.metrics.increment_counter(_WORKFLOW_STEP_EVENTS_TOTAL, 1, labels)
        self.metrics.observe_histogram(
            _WORKFLOW_STEP_DURATION_SECONDS,
            max(duration_seconds, 0.0),
            labels,
        )


def should_skip_transform_step(
    spec: WorkflowTransformSpec,
    *,
    completed_fingerprints: Mapping[str, str] | None,
) -> bool:
    """Return whether a completed transform fingerprint matches the current spec."""
    if not completed_fingerprints:
        return False
    return completed_fingerprints.get(spec.step_id) == spec.fingerprint
