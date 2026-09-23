"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.contains_any import (
    _WORKFLOW_GATE_RULES,
    _workflow_job_surface_metadata,
)
from memory.graph.sync_pkg.create_workflow_job_surface import (
    _create_workflow_job_surface,
)
from memory.graph.sync_pkg.graph_contexts import WorkflowContext, WorkflowJobContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.python_paths import MAIN_PY

__all__ = [
    "_add_workflow_job_surface",
    "_workflow_module_script_targets",
    "_workflow_quality_gates",
    "_workflow_repo_path_targets",
]


def _workflow_module_script_targets(run_text: str) -> tuple[NodeKey, ...]:
    module_pattern = re.compile(
        r"(?:uv\s+run\s+)?python(?:3)?\s+-m\s+scripts\.([\w.]+)"
    )
    return tuple(
        NodeKey(
            "script_surface", f"scripts/{match.group(1).replace('.', '/')}/{MAIN_PY}"
        )
        for match in module_pattern.finditer(run_text)
    )


def _workflow_repo_path_targets(run_text: str) -> tuple[NodeKey, ...]:
    path_pattern = re.compile(
        r"(?<![\w./-])((?:scripts|tests|configs|src|docs|grafana|\.github)/[\w./-]+)"
    )
    targets: list[NodeKey] = []
    for match in path_pattern.finditer(run_text):
        candidate = match.group(1).rstrip(".,:)")
        targets.extend(
            (
                NodeKey("script_surface", candidate),
                NodeKey("file_surface", candidate),
                NodeKey("directory_surface", candidate),
            )
        )
    return tuple(targets)


def _workflow_quality_gates(run_text: str) -> tuple[str, ...]:
    lowered = run_text.lower()
    gates: list[str] = []
    for predicate, gate_name in _WORKFLOW_GATE_RULES:
        if predicate(lowered):
            gates.append(gate_name)
    return tuple(dict.fromkeys(gates))


def _add_workflow_job_surface(
    snapshot: GraphSnapshot,
    context: WorkflowContext,
    *,
    job_id: str,
    job_payload: dict[str, object],
) -> tuple[WorkflowJobContext, tuple[dict[str, str], ...], tuple[str, ...]]:
    (
        inline_run_step_count,
        uses_step_count,
        matrix_axes,
        matrix_variants,
        environment_name,
        concurrency_group,
        secret_usage_hints,
    ) = _workflow_job_surface_metadata(job_payload)
    job_name = f"{context.workflow_name}::{job_id}"
    job = _create_workflow_job_surface(
        snapshot,
        context,
        job_name=job_name,
        job_id=job_id,
        job_payload=job_payload,
        inline_run_step_count=inline_run_step_count,
        uses_step_count=uses_step_count,
        matrix_axes=matrix_axes,
        matrix_variants=matrix_variants,
        environment_name=environment_name,
        secret_usage_hints=secret_usage_hints,
        concurrency_group=concurrency_group,
    )
    snapshot.add_relation(
        context.workflow, "CONTAINS", job, provenance="workflow_graph"
    )
    return (
        WorkflowJobContext(
            workflow_name=context.workflow_name,
            job_id=job_id,
            job_name=job_name,
            relative_path=context.relative_path,
            today=context.today,
            job=job,
        ),
        matrix_variants,
        secret_usage_hints,
    )
