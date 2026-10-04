"""Restore bounded reconciliation inputs from durable completion evidence."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TypedDict, cast

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.domain.control_plane import WorkflowExecutionState, WorkflowStepState
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)


class SelectedSnapshotResumeOptions(TypedDict, total=False):
    """Optional runner extension, omitted for legacy execution adapters."""

    restored_step_outputs: Mapping[str, object]


def _restore_producer(
    definition: WorkflowStepConfig, details: Mapping[str, object]
) -> RunResult:
    receipt, snapshots = (
        details.get("producer_result"),
        details.get("selected_snapshots"),
    )
    if (
        not isinstance(receipt, Mapping)
        or type(receipt.get("schema_version")) is not int
        or receipt.get("schema_version") != 1
        or not isinstance(snapshots, dict)
        or not snapshots
    ):
        raise ValueError("selected-snapshot resume lacks producer evidence receipt")
    _validate_producer_identity(definition, details, receipt)
    _validate_producer_counts(receipt)
    _validate_producer_pins(definition, receipt, snapshots)
    return _producer_result(definition, receipt, snapshots)


def _validate_producer_identity(
    definition: WorkflowStepConfig,
    details: Mapping[str, object],
    receipt: Mapping[str, object],
) -> None:
    """Require the receipt to identify the recorded successful child execution."""
    if (
        receipt.get("pipeline_name") != definition.pipeline_name
        or receipt.get("run_id") != details.get("child_run_id")
        or receipt.get("manifest_id") != details.get("child_manifest_id")
    ):
        raise ValueError("selected-snapshot resume producer identity mismatch")
    for key in ("run_id", "manifest_id", "run_type"):
        if not isinstance(receipt.get(key), str) or not receipt[key]:
            raise ValueError("selected-snapshot resume producer identity incomplete")
    if receipt.get("status") not in (
        PipelineRunResult.SUCCESS.value,
        PipelineRunResult.DRY_RUN.value,
    ):
        raise ValueError("selected-snapshot resume producer was not successful")


def _validate_producer_counts(receipt: Mapping[str, object]) -> None:
    """Keep all historical counts, including zero, without inferring new totals."""
    count_keys = (
        "records_fetched",
        "records_bronze",
        "records_silver",
        "records_gold",
        "records_gold_excluded_by_contract",
        "records_quarantined",
        "records_filtered_out",
    )
    if any(
        type(receipt.get(key)) is not int or cast(int, receipt[key]) < 0
        for key in count_keys
    ):
        raise ValueError("selected-snapshot resume producer counts incomplete")


def _validate_producer_pins(
    definition: WorkflowStepConfig,
    receipt: Mapping[str, object],
    snapshots: Mapping[str, object],
) -> None:
    """Require each selected version to belong to the same producer execution."""
    for entry in snapshots.values():
        if (
            not isinstance(entry, Mapping)
            or type(entry.get("version")) is not int
            or cast(int, entry.get("version")) < 0
            or not isinstance(entry.get("table_id"), str)
            or not entry.get("table_id")
            or entry.get("producer_pipeline") != definition.pipeline_name
            or entry.get("run_ids") != [receipt["run_id"]]
        ):
            raise ValueError("selected-snapshot resume pin producer mismatch")


def _producer_result(
    definition: WorkflowStepConfig,
    receipt: Mapping[str, object],
    snapshots: dict[str, dict[str, object]],
) -> RunResult:
    """Reconstruct the immutable producer result from validated durable evidence."""
    try:
        started = datetime.fromisoformat(cast(str, receipt["started_at"]))
        completed = datetime.fromisoformat(cast(str, receipt["completed_at"]))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "selected-snapshot resume producer timestamps incomplete"
        ) from error
    return RunResult(
        status=PipelineRunResult(cast(str, receipt["status"])),
        pipeline_name=definition.pipeline_name,
        run_id=cast(str, receipt["run_id"]),
        manifest_id=cast(str, receipt["manifest_id"]),
        run_type=cast(str, receipt["run_type"]),
        records_fetched=cast(int, receipt["records_fetched"]),
        records_bronze=cast(int, receipt["records_bronze"]),
        records_silver=cast(int, receipt["records_silver"]),
        records_gold=cast(int, receipt["records_gold"]),
        records_gold_excluded_by_contract=cast(
            int, receipt["records_gold_excluded_by_contract"]
        ),
        records_quarantined=cast(int, receipt["records_quarantined"]),
        records_filtered_out=cast(int, receipt["records_filtered_out"]),
        started_at=started,
        completed_at=completed,
        run_report_json_path=cast(str | None, receipt.get("run_report_json_path")),
        run_report_markdown_path=cast(
            str | None, receipt.get("run_report_markdown_path")
        ),
        selected_snapshots=snapshots,
    )


def _snapshot_producers(config: WorkflowConfig) -> set[str]:
    """Find producers requiring pinned snapshots directly or through a cohort."""
    producers = {
        step.step_id
        for step in config.pipeline_steps
        if step.run_options.reconciliation_mode == "selected-snapshot"
    }
    producers.update(
        step.reference_cohort.step_id
        for step in config.pipeline_steps
        if step.reference_cohort is not None
    )
    return producers


def restore_selected_snapshot_outputs(
    config: WorkflowConfig,
    state: WorkflowExecutionState,
    completed_step_ids: frozenset[str],
) -> dict[str, object]:
    """Reject missing evidence rather than capturing new versions during resume."""
    producers = _snapshot_producers(config)
    if not producers and config.defaults.reconciliation_mode != "selected-snapshot":
        return {}
    restored: dict[str, object] = {}
    for step in state.steps:
        if step.step_id not in completed_step_ids:
            continue
        if step.step_kind == "pipeline" and _requires_snapshot(step, config, producers):
            restored[step.step_id] = _restore_producer_step(config, step)
            continue
        payload = _resume_payload(step)
        if _requires_snapshot(step, config, producers) and not payload.get(
            "selected_snapshots"
        ):
            raise ValueError(
                f"selected-snapshot resume lacks producer evidence: {step.step_id}"
            )
        restored[step.step_id] = payload
    if set(completed_step_ids) != set(restored):
        raise ValueError("selected-snapshot resume lacks completed step evidence")
    return restored


def _restore_producer_step(
    config: WorkflowConfig, step: WorkflowStepState
) -> RunResult:
    """Reject failed or undefined producers before restoring their receipts."""
    if step.status != "success":
        raise ValueError("selected-snapshot resume producer was not successful")
    definition = config.get_step(step.step_id)
    if not isinstance(definition, WorkflowStepConfig):
        raise ValueError("selected-snapshot resume lacks producer evidence definition")
    return _restore_producer(definition, step.output_details or {})


def _resume_payload(step: WorkflowStepState) -> dict[str, object]:
    """Restore the original completion payload without reading live storage."""
    details = step.output_details or {}
    if step.step_kind == "pipeline":
        return {
            "run_id": details.get("child_run_id"),
            "manifest_id": details.get("child_manifest_id"),
            "selected_snapshots": details.get("selected_snapshots"),
        }
    summary = details.get("transform_result_summary")
    return dict(summary) if isinstance(summary, dict) else {}


def _requires_snapshot(
    step: WorkflowStepState, config: WorkflowConfig, producers: set[str]
) -> bool:
    """Exclude unrelated pipeline and transform completions from snapshot proof."""
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
    return not (unrelated_pipeline or unrelated_transform)
