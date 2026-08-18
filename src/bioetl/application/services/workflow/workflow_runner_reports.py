"""Best-effort workflow run report attachment helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def _plan_steps_from_config(config: WorkflowConfig) -> list[JsonDict]:
    plan_steps: list[JsonDict] = []
    for step_id in config.topological_step_ids:
        step = config.get_step(step_id)
        if step is None:
            continue
        if isinstance(step, WorkflowStepConfig):
            kind = "pipeline"
            pipeline_name = step.pipeline_name
            transform_name = None
        else:
            kind = "transform"
            pipeline_name = None
            transform_name = step.transform_name
        plan_steps.append(
            {
                "step_id": step.step_id,
                "kind": kind,
                "pipeline_name": pipeline_name,
                "transform_name": transform_name,
                "depends_on": list(step.depends_on),
            }
        )
    return plan_steps


def _pipeline_name_for_step(
    step: WorkflowStepExecutionResult,
    *,
    plan_steps: list[JsonDict],
    payload: object | None,
) -> object | None:
    pipeline_name: object | None = (
        getattr(payload, "pipeline_name", None) if payload is not None else None
    )
    if pipeline_name is not None:
        return pipeline_name
    for planned in plan_steps:
        if planned["step_id"] == step.step_id:
            return planned.get("pipeline_name")
    return None


def _load_child_top_reasons(report_ref: object) -> object:
    """Best-effort load of reason rows at the application filesystem boundary."""
    if not isinstance(report_ref, str) or not report_ref:
        return ()
    try:
        path = Path(report_ref)
        if not path.is_file():
            return ()
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()
    if not isinstance(payload, Mapping):
        return ()
    return payload.get("reasons_top_n") or ()


def _execution_rows_from_result(
    result: WorkflowRunExecutionResult,
    *,
    plan_steps: list[JsonDict],
) -> list[JsonDict]:
    execution_rows: list[JsonDict] = []
    for step in result.steps:
        payload = step.payload
        report_ref = (
            getattr(payload, "run_report_json_path", None)
            if payload is not None
            else None
        )
        execution_rows.append(
            {
                "step_id": step.step_id,
                "kind": step.step_kind,
                "status": step.status,
                "pipeline_name": _pipeline_name_for_step(
                    step, plan_steps=plan_steps, payload=payload
                ),
                "payload": payload,
                "child_run_id": step.child_run_id,
                "child_manifest_id": step.child_manifest_id,
                "pipeline_report_ref": report_ref,
                "top_reasons": _load_child_top_reasons(report_ref),
                "error_type": step.error_type,
                "error_message": step.error_message,
            }
        )
    return execution_rows


def attach_workflow_run_report(
    *,
    config: WorkflowConfig,
    result: WorkflowRunExecutionResult,
    logger: LoggerPort | None = None,
) -> WorkflowRunExecutionResult:
    """Build and persist workflow_run_report_v1 (best-effort)."""
    try:
        from bioetl.application.services.run_reports.writer import (
            write_workflow_run_report,
        )
        from bioetl.domain.run_reports.workflow_builder import (
            build_workflow_run_report,
        )

        plan_steps = _plan_steps_from_config(config)
        execution_rows = _execution_rows_from_result(result, plan_steps=plan_steps)
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
        # NOSONAR - mypy infers correct type; Sonar S5886 false positive on dataclass.replace()
        return replace(
            result,
            run_report_json_path=str(written.json_path),
            run_report_markdown_path=str(written.markdown_path),
        )
    except Exception as exc:
        if logger is not None:
            logger.warning(
                "Workflow run report build failed",
                workflow_name=result.workflow_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
        # NOSONAR - mypy infers correct type; Sonar S5886 false positive on dataclass.replace()
        return replace(
            result,
            run_report_error=f"{type(exc).__name__}: {exc}",
        )
