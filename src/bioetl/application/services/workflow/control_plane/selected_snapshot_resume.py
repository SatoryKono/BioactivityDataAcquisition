"""Restore bounded reconciliation inputs from durable completion evidence."""

from collections.abc import Mapping
from typing import TypedDict

from bioetl.domain.control_plane import WorkflowExecutionState
from bioetl.domain.workflow import TransformStepConfig, WorkflowConfig


class SelectedSnapshotResumeOptions(TypedDict, total=False):
    """Optional runner extension, omitted for legacy execution adapters."""

    restored_step_outputs: Mapping[str, object]


def restore_selected_snapshot_outputs(
    config: WorkflowConfig,
    state: WorkflowExecutionState,
    completed_step_ids: frozenset[str],
) -> dict[str, object]:
    """Reject missing evidence rather than capturing new versions during resume."""
    producers = {
        step.step_id
        for step in config.pipeline_steps
        if step.run_options.reconciliation_mode == "selected-snapshot"
    }
    if not producers and config.defaults.reconciliation_mode != "selected-snapshot":
        return {}
    restored: dict[str, object] = {}
    for step in state.steps:
        if step.step_id not in completed_step_ids:
            continue
        details = step.output_details or {}
        if step.step_kind == "pipeline":
            payload = {
                "run_id": details.get("child_run_id"),
                "manifest_id": details.get("child_manifest_id"),
                "selected_snapshots": details.get("selected_snapshots"),
            }
        else:
            summary = details.get("transform_result_summary")
            payload = dict(summary) if isinstance(summary, dict) else {}
        definition = config.get_step(step.step_id)
        unrelated_pipeline = (
            step.step_kind == "pipeline"
            and step.step_id not in producers
            and config.defaults.reconciliation_mode != "selected-snapshot"
        )
        unrelated_transform = (
            isinstance(definition, TransformStepConfig)
            and definition.transform_name != "reconcile_foreign_keys"
        )
        if not (unrelated_pipeline or unrelated_transform) and not payload.get(
            "selected_snapshots"
        ):
            raise ValueError(
                f"selected-snapshot resume lacks producer evidence: {step.step_id}"
            )
        restored[step.step_id] = payload
    if set(completed_step_ids) != set(restored):
        raise ValueError("selected-snapshot resume lacks completed step evidence")
    return restored
