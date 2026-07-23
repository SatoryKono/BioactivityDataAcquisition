"""Best-effort workflow run report attachment helpers."""

from __future__ import annotations

from dataclasses import replace

from bioetl.application.services.workflow_runner_models import WorkflowRunExecutionResult
from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig


def attach_workflow_run_report(
    *,
    config: WorkflowConfig,
    result: WorkflowRunExecutionResult,
) -> WorkflowRunExecutionResult:
    """Build and persist workflow_run_report_v1 (best-effort)."""
    try:
        from bioetl.application.services.run_reports.writer import (
            write_workflow_run_report,
        )
        from bioetl.domain.run_reports.workflow_builder import (
            build_workflow_run_report,
        )

        plan_steps = []
        for step_id in config.topological_step_ids:
            step = config.get_step(step_id)
            if step is None:
                continue
            kind = "pipeline" if isinstance(step, WorkflowStepConfig) else "transform"
            plan_steps.append(
                {
                    "step_id": step.step_id,
                    "kind": kind,
                    "pipeline_name": getattr(step, "pipeline_name", None),
                    "transform_name": getattr(step, "transform_name", None)
                    or getattr(step, "name", None),
                    "depends_on": list(getattr(step, "depends_on", ()) or ()),
                }
            )
        execution_rows = []
        for step in result.steps:
            pipeline_name = None
            report_ref = None
            payload = step.payload
            if payload is not None:
                pipeline_name = getattr(payload, "pipeline_name", None)
                report_ref = getattr(payload, "run_report_json_path", None)
            # Prefer plan pipeline name when payload is transform-only.
            if pipeline_name is None:
                for planned in plan_steps:
                    if planned["step_id"] == step.step_id:
                        pipeline_name = planned.get("pipeline_name")
                        break
            execution_rows.append(
                {
                    "step_id": step.step_id,
                    "kind": step.step_kind,
                    "status": step.status,
                    "pipeline_name": pipeline_name,
                    "payload": payload,
                    "child_run_id": step.child_run_id,
                    "child_manifest_id": step.child_manifest_id,
                    "pipeline_report_ref": report_ref,
                    "error_type": step.error_type,
                    "error_message": step.error_message,
                }
            )
        report = build_workflow_run_report(
            identity={
                "workflow_name": result.workflow_name,
                "workflow_version": getattr(config, "version", None),
                "workflow_run_id": result.workflow_run_id,
                "manifest_id": result.manifest_id,
                "execution_fingerprint": result.execution_fingerprint,
                "status": result.status,
                "started_at": None,
                "completed_at": None,
                "duration_seconds": None,
                "resumed": result.resumed,
            },
            plan_steps=plan_steps,
            execution_steps=execution_rows,
        )
        written = write_workflow_run_report(report)
        return replace(
            result,
            run_report_json_path=str(written.json_path),
            run_report_markdown_path=str(written.markdown_path),
        )
    except Exception as exc:
        return replace(
            result,
            run_report_error=f"{type(exc).__name__}: {exc}",
        )
