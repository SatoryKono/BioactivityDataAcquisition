"""Bounded mode, persisted producer lineage and backward-compatible resume."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest
import yaml
from pydantic import ValidationError

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.execution.workflow_runner_step_execution import (
    execute_pipeline_step,
)
from bioetl.application.services.workflow.control_plane.execution_recording_state import (
    _apply_completed_step_state,
)
from bioetl.application.services.workflow.control_plane.execution_recording_payloads import (
    build_step_completion_details,
)
from bioetl.application.services.workflow.control_plane.selected_snapshot_resume import (
    restore_selected_snapshot_outputs,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowStepExecutionResult,
)
from bioetl.application.workflow.transforms.selected_snapshot_inputs import (
    selected_snapshot_inputs,
)
from bioetl.domain.control_plane import WorkflowExecutionState, WorkflowStepState
from bioetl.domain.run_reports.workflow_builder import _reconciliation_details
from bioetl.domain.workflow import (
    WorkflowConfig,
    TransformStepConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from bioetl.domain.workflow.config import WorkflowReferenceCohort
from bioetl.infrastructure.schemas.workflow_config import (
    WorkflowConfigFileSchema,
    WorkflowRunOptionsSchema,
)
from bioetl.interfaces.cli.commands._workflow_override_support import (
    apply_cli_overrides,
)
from tests.unit.application.services.control_plane.workflow.test_execution_resume_support import (
    _state,
)

pytestmark = pytest.mark.integration


def config():
    payload = yaml.safe_load(Path("configs/workflows/chembl_baseline.yaml").read_text())
    return WorkflowConfigFileSchema.model_validate(payload).to_domain()


def pin(version=0, ancestors=(), run="producer"):
    return {
        "gold:chembl.assay": {
            "version": version,
            "ancestor_versions": list(ancestors),
            "run_ids": [run],
        }
    }


def test_selected_mode_roundtrip_and_cli_overrides_bind_scope():
    options = WorkflowRunOptionsSchema(
        reconciliation_mode="selected-snapshot", limit=1000
    )
    assert (
        WorkflowRunOptionsSchema.model_validate(options.to_domain().to_mapping())
        == options
    )
    selected = apply_cli_overrides(
        config(), reconciliation_mode="selected-snapshot", limit=1000
    )
    assert selected.defaults.reconciliation_mode == "selected-snapshot"
    assert all(s.run_options.limit == 1000 for s in selected.pipeline_steps)
    assert all(
        s.config["source_scope"] == "current_run"
        for s in [s for s in selected.steps if isinstance(s, TransformStepConfig)]
    )
    assert all(
        s.config["reconciliation_mode"] == "selected-snapshot"
        for s in [s for s in selected.steps if isinstance(s, TransformStepConfig)]
    )
    complete = apply_cli_overrides(
        selected, reconciliation_mode="complete-reference", limit=1000
    )
    assert complete.defaults.reconciliation_mode == "complete-reference"
    independent = replace(
        selected,
        steps=tuple(
            replace(step, reference_cohort=None)
            if isinstance(step, WorkflowStepConfig)
            else step
            for step in selected.steps
        ),
    )
    with pytest.raises(ValueError, match="independently bounded"):
        apply_cli_overrides(
            independent, reconciliation_mode="complete-reference", limit=1000
        )


def test_selected_yaml_defaults_bind_pipeline_and_transform_modes():
    payload = yaml.safe_load(Path("configs/workflows/chembl_baseline.yaml").read_text())
    payload["workflow"]["defaults"]["run_options"].update(
        reconciliation_mode="selected-snapshot", limit=1000
    )
    selected = WorkflowConfigFileSchema.model_validate(payload).to_domain()
    assert all(
        s.run_options.reconciliation_mode == "selected-snapshot"
        for s in selected.pipeline_steps
    )
    assert all(
        s.config["source_scope"] == "current_run"
        for s in [s for s in selected.steps if isinstance(s, TransformStepConfig)]
    )


@pytest.mark.parametrize("mode", ["selected_snapshot", "unknown", ""])
def test_invalid_mode_rejected_in_schema_and_domain(mode):
    with pytest.raises(ValidationError):
        WorkflowRunOptionsSchema(reconciliation_mode=mode)
    with pytest.raises(ValueError):
        WorkflowRunOptionsConfig(reconciliation_mode=mode)


def test_lineage_combination_is_order_independent():
    older = {"selected_snapshots": pin()}
    newer = {"selected_snapshots": pin(1, (0,))}
    assert selected_snapshot_inputs({"a": older, "b": newer}) == pin(1, (0,))
    assert selected_snapshot_inputs({"b": newer, "a": older}) == pin(1, (0,))


@pytest.mark.parametrize(
    "candidate",
    [
        pin(2),
        pin(1, (0,), "other"),
        {"gold:chembl.assay": {"ancestor_versions": "bad"}},
    ],
)
def test_ambiguous_producer_lineage_rejected(candidate):
    with pytest.raises(ValueError):
        selected_snapshot_inputs(
            {"a": {"selected_snapshots": pin()}, "b": {"selected_snapshots": candidate}}
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("bound_cohort", [False, True])
@pytest.mark.parametrize("mode", ["selected-snapshot", "complete-reference"])
async def test_pipeline_captures_version_and_limits_before_completion(
    bound_cohort, mode
):
    selected = apply_cli_overrides(config(), reconciliation_mode=mode, limit=1000)
    result = RunResult(
        PipelineRunResult.SUCCESS,
        "chembl_assay",
        "producer",
        "backfill",
        manifest_id="child",
    )
    capture = AsyncMock(return_value=pin())
    producer = selected.pipeline_steps[0]
    if bound_cohort:
        producer = replace(
            producer,
            reference_cohort=WorkflowReferenceCohort(
                "upstream", "chembl.target", "target_id", "target_id"
            ),
        )
    resolved = replace(
        producer,
        run_options=replace(producer.run_options, filter_ids=("selected-target",)),
    )
    resolver = AsyncMock(return_value=resolved)
    runner = SimpleNamespace(run=AsyncMock(return_value=result))
    upstream = {"upstream": {"run_id": "upstream-producer"}}
    completed = await execute_pipeline_step(
        pipeline_runner=runner,
        metrics=MagicMock(),
        monotonic=lambda: 1.0,
        workflow_name=selected.name,
        step=producer,
        workflow_context_labels={},
        step_started_callback=None,
        workflow_run_id="workflow",
        snapshot_reader=capture,
        cohort_resolver=resolver,
        upstream_outputs=upstream,
        capture_producer_snapshot=mode == "complete-reference",
    )
    assert completed.status == "success"
    capture.assert_has_awaits(
        [call("chembl_assay", ""), call("chembl_assay", "producer")]
    )
    assert completed.payload.selected_snapshots["gold:chembl.assay"]["limit"] == 1000
    assert producer.run_options.reconciliation_mode == mode
    if bound_cohort:
        resolver.assert_awaited_once_with(producer, upstream)
        assert runner.run.await_args.kwargs["options"].filter_ids == ["selected-target"]
    else:
        resolver.assert_not_awaited()


def test_durable_state_restores_producer_and_transform_snapshots():
    selected = WorkflowConfig(
        "resume",
        steps=(
            WorkflowStepConfig("seed", "chembl_assay"),
            TransformStepConfig(
                "clean", "reconcile_foreign_keys", depends_on=("seed",)
            ),
        ),
        defaults=WorkflowRunOptionsConfig(reconciliation_mode="selected-snapshot"),
    )
    snapshots = {
        key: {**entry, "producer_pipeline": "chembl_assay", "table_id": "table"}
        for key, entry in pin().items()
    }
    original = RunResult(
        PipelineRunResult.SUCCESS,
        "chembl_assay",
        "producer",
        "backfill",
        manifest_id="child-manifest",
        records_gold=10,
        selected_snapshots=snapshots,
    )
    completion = build_step_completion_details(
        WorkflowStepExecutionResult(
            "seed",
            "pipeline",
            "success",
            payload=original,
            child_run_id="producer",
            child_manifest_id="child-manifest",
        )
    )
    producer = WorkflowStepState(
        "seed",
        "pipeline",
        "success",
        output_details=completion,
    )
    transform = WorkflowStepState(
        "clean",
        "transform",
        "success",
        output_details={
            "transform_result_summary": {
                "selected_snapshots": {
                    key: {**entry, "version": 1, "ancestor_versions": [0]}
                    for key, entry in snapshots.items()
                },
                "source_run_ids": ["producer"],
                "reconciliation_mode": "selected-snapshot",
            }
        },
    )
    state = replace(_state(), steps=(producer, transform))
    restored_state = WorkflowExecutionState.from_dict(state.to_dict())
    outputs = restore_selected_snapshot_outputs(
        selected, restored_state, frozenset({"seed", "clean"})
    )
    assert isinstance(outputs["seed"], RunResult)
    assert outputs["seed"].run_id == "producer"
    assert outputs["seed"].records_gold == original.records_gold == 10
    assert outputs["seed"].selected_snapshots == snapshots
    assert (
        selected_snapshot_inputs(outputs)
        == transform.output_details["transform_result_summary"]["selected_snapshots"]
    )
    skipped = WorkflowStepExecutionResult(
        step_id="seed",
        step_kind="pipeline",
        status="skipped",
        error_type="AlreadyCompletedOnResume",
    )
    preserved = _apply_completed_step_state(
        restored_state,
        result=skipped,
        fingerprint=None,
        updated_at=state.updated_at,
        last_event_id="resume",
    )
    assert preserved.steps[0].output_details == producer.output_details


def test_legacy_resume_does_not_invent_selected_snapshot_evidence():
    legacy = _state()
    unbound = WorkflowConfig(
        "legacy", steps=(WorkflowStepConfig("seed", "chembl_assay"),)
    )
    assert restore_selected_snapshot_outputs(unbound, legacy, frozenset({"seed"})) == {}
    selected = apply_cli_overrides(unbound, reconciliation_mode="selected-snapshot")
    with pytest.raises(ValueError, match="lacks producer evidence"):
        restore_selected_snapshot_outputs(selected, legacy, frozenset({"seed"}))
    assert "output_details" not in legacy.steps[0].to_dict()


def test_report_whitelist_preserves_mode_scope_and_versions_without_inventing_completeness():
    payload = {
        "transform_name": "reconcile_foreign_keys",
        "reconciliation_mode": "selected-snapshot",
        "source_scope": "current_run",
        "reference_scope": "current_run",
        "input_snapshots": pin(),
        "selected_snapshots": pin(1, (0,)),
        "reference_completeness": "unproven",
        "scanned_rows": 10,
        "orphan_rows_deleted": 10,
        "retained_rows": 0,
    }
    details = _reconciliation_details(payload)
    assert details == {k: v for k, v in payload.items() if k != "transform_name"}
    legacy = _reconciliation_details({"transform_name": "reconcile_foreign_keys"})
    assert legacy == {}


def test_selected_snapshot_mode_changes_resume_fingerprint():
    from bioetl.application.services.control_plane.workflow.manifest_service import (
        WorkflowManifestService,
    )
    from bioetl.application.services.control_plane.workflow.manifest_models import (
        WorkflowManifestCreateSpec,
    )
    from bioetl.application.services.workflow.control_plane._execution_resume_support import (
        _validate_execution_fingerprint,
    )

    service = WorkflowManifestService(manifest_port=MagicMock())
    original = config()
    selected = apply_cli_overrides(original, reconciliation_mode="selected-snapshot")
    spec = WorkflowManifestCreateSpec(
        workflow_run_id=_state().workflow_run_id, config=original, launch_context={}
    )
    original_hash = service.compute_execution_fingerprint(spec)
    selected_hash = service.compute_execution_fingerprint(
        replace(spec, config=selected)
    )
    assert original_hash != selected_hash
    with pytest.raises(RuntimeError, match="same execution fingerprint"):
        _validate_execution_fingerprint(
            replace(_state(), execution_fingerprint=original_hash), selected_hash
        )


def test_failed_confirmation_keeps_destructive_state_and_requires_repair():
    committed = WorkflowStepState(
        "reconcile",
        "transform",
        "running",
        destructive=True,
        commit_pending_confirmation=True,
        mutation_details={
            "reconciliation_mode": "selected-snapshot",
            "input_snapshots": pin(),
        },
    )
    state = replace(
        _state(),
        steps=(committed,),
        ambiguous_step_ids=("reconcile",),
        repair_required=True,
        repair_hint="repair",
    )
    failed = WorkflowStepExecutionResult(
        step_id="reconcile",
        step_kind="transform",
        status="failed",
        error_type="RuntimeError",
    )
    updated = _apply_completed_step_state(
        state,
        result=failed,
        fingerprint=None,
        updated_at=state.updated_at,
        last_event_id="failed-confirmation",
    )
    assert updated.repair_required and updated.steps[0].commit_pending_confirmation
    assert updated.steps[0].mutation_details == committed.mutation_details


def test_selected_snapshot_totals_use_confirmed_post_commit_rows():
    from bioetl.domain.run_reports.workflow_totals import _measured_current

    details = {
        "source_scope": "current_run",
        "reconciliation_mode": "selected-snapshot",
        "source_table": "chembl.assay",
        "mutation_mode": "gold_scd2_expiry",
        "selected_snapshots": pin(1, (0,)),
        "source_snapshot": {"version": 1, "physical_rows": 1000, "current_rows": 0},
    }
    assert _measured_current(SimpleNamespace(status="success"), details) == 0
    assert (
        _measured_current(
            SimpleNamespace(status="success"), {**details, "selected_snapshots": pin(2)}
        )
        is None
    )
    assert (
        _measured_current(
            SimpleNamespace(status="success"), {**details, "dry_run": True}
        )
        is None
    )
