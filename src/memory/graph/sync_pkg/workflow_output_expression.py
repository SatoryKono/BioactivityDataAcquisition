"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re

from memory.graph.sync_pkg.graph_contexts import WorkflowContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_workflow_surface",
    "_claim_modality",
    "_cli_side_effect_class",
    "_extract_cli_options",
    "_job_step_counts",
    "_workflow_artifact_specs",
    "_workflow_concurrency_group",
    "_workflow_output_expression",
]


def _workflow_output_expression(output_value: object) -> str | None:
    if isinstance(output_value, str):
        return output_value
    if not isinstance(output_value, dict):
        return None
    raw_value = output_value.get("value")
    if isinstance(raw_value, str):
        return raw_value
    description = output_value.get("description")
    return description if isinstance(description, str) else None


def _workflow_concurrency_group(payload: dict[str, object]) -> str | None:
    concurrency_payload = payload.get("concurrency")
    if isinstance(concurrency_payload, str):
        return concurrency_payload
    if isinstance(concurrency_payload, dict):
        group = concurrency_payload.get("group")
        if isinstance(group, str):
            return group
    return None


def _workflow_artifact_specs(
    workflow_name: str,
    job_id: str,
    step: dict[str, object],
) -> tuple[tuple[str, str, str | None], ...]:
    uses_ref = step.get("uses")
    if not isinstance(uses_ref, str):
        return ()
    normalized_uses = uses_ref.lower()
    if (
        "upload-artifact" not in normalized_uses
        and "download-artifact" not in normalized_uses
    ):
        return ()
    relation_type = (
        "PUBLISHES_ARTIFACT" if "upload-artifact" in normalized_uses else "DEPENDS_ON"
    )
    with_payload = step.get("with")
    artifact_name = None
    artifact_path = None
    if isinstance(with_payload, dict):
        raw_name = with_payload.get("name")
        if isinstance(raw_name, str):
            artifact_name = raw_name
        raw_path = with_payload.get("path")
        if isinstance(raw_path, str):
            artifact_path = raw_path
    if artifact_name is None:
        step_name = step.get("name")
        artifact_name = (
            step_name
            if isinstance(step_name, str) and step_name
            else f"{job_id}-artifact"
        )
    return ((f"{workflow_name}::{artifact_name}", relation_type, artifact_path),)


def _extract_cli_options(raw_command: str) -> tuple[str, ...]:
    options = re.findall(r"(?<![\w-])(--[\w][\w-]*)", raw_command)
    return tuple(sorted(dict.fromkeys(options)))


def _cli_side_effect_class(command_name: str) -> str:
    lowered = command_name.lower()
    if any(
        token in lowered
        for token in (
            " check",
            " lint",
            " verify",
            "validate",
            "status",
            "show",
            "list",
        )
    ):
        return "read_only"
    if any(
        token in lowered
        for token in ("run", "sync", "generate", "update", "write", "create", "cleanup")
    ):
        return "mutating"
    return "mixed"


def _claim_modality(text: str) -> str:
    lowered = text.lower()
    if (
        "must not" in lowered
        or "never" in lowered
        or "forbidden" in lowered
        or "should not" in lowered
    ):
        return "forbidden"
    if "must" in lowered or "required" in lowered or "require" in lowered:
        return "required"
    return "guidance"


def _job_step_counts(steps: object) -> tuple[int, int]:
    if not isinstance(steps, list):
        return 0, 0
    inline_run_step_count = sum(
        1
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("run"), str)
    )
    uses_step_count = sum(
        1
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("uses"), str)
    )
    return inline_run_step_count, uses_step_count


def _add_workflow_surface(
    snapshot: GraphSnapshot,
    *,
    workflow_name: str,
    title: str,
    relative_path: str,
    today: str,
) -> WorkflowContext:
    workflow = snapshot.add_node(
        "workflow_surface",
        workflow_name,
        summary=f"GitHub Actions workflow `{title}`.",
        source_path=relative_path,
        source_kind="github_actions_workflow",
        workflow_title=title,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    return WorkflowContext(
        workflow_name=workflow_name,
        title=title,
        relative_path=relative_path,
        today=today,
        workflow=workflow,
    )
