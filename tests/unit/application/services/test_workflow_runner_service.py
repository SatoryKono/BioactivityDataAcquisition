# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for declarative workflow runner service."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.workflow_runner_service import WorkflowRunnerService
from bioetl.application.services.workflow_transform_service import (
    WorkflowTransformExecutionResult,
    WorkflowTransformService,
)
from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.infrastructure.config.workflow_config_api import load_workflow_config
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
    WorkflowTransformSpec,
)
from tests.helpers.clock import FIXED_TEST_TIME


pytestmark = pytest.mark.unit


@dataclass
class _RecordingMetrics:
    counters: list[tuple[str, int, dict[str, str]]] = field(default_factory=list)
    gauges: list[tuple[str, float, dict[str, str]]] = field(default_factory=list)
    histograms: list[tuple[str, float, dict[str, str]]] = field(default_factory=list)

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.counters.append((name, value, labels or {}))

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.histograms.append((name, value, labels or {}))

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.gauges.append((name, value, labels or {}))

    def close(self) -> None:
        return None


class _PipelineRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: object | None = None,
        options: object | None = None,
    ) -> RunResult:
        await asyncio.sleep(0)
        del dry_run, run_id
        self.calls.append((pipeline_name, options))
        return RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name=pipeline_name,
            run_id="00000000-0000-0000-0000-000000000101",
            run_type="incremental",
            started_at=FIXED_TEST_TIME,
            completed_at=FIXED_TEST_TIME,
        )


class _FailingPipelineRunner:
    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: object | None = None,
        options: object | None = None,
    ) -> RunResult:
        await asyncio.sleep(0)
        del pipeline_name, dry_run, run_id, options
        raise RuntimeError("pipeline boom")


class _AttributeErrorPipelineRunner:
    """Simulates unexpected AttributeError (e.g. incomplete span surface)."""

    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: object | None = None,
        options: object | None = None,
    ) -> RunResult:
        await asyncio.sleep(0)
        del pipeline_name, dry_run, run_id, options
        raise AttributeError("'NoneType' object has no attribute 'add_event'")


class _IdentifiedPipelineError(RuntimeError):
    """Failure emitted after the child run and manifest identities exist."""

    run_id = "00000000-0000-0000-0000-000000000199"
    manifest_id = "manifest-child-199"


class _IdentifiedFailingPipelineRunner:
    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: object | None = None,
        options: object | None = None,
    ) -> RunResult:
        await asyncio.sleep(0)
        del pipeline_name, dry_run, run_id, options
        raise _IdentifiedPipelineError("identified pipeline boom")


class _SelectiveFailingPipelineRunner:
    def __init__(self, failing_pipeline_name: str) -> None:
        self.calls: list[tuple[str, object]] = []
        self.failing_pipeline_name = failing_pipeline_name

    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: object | None = None,
        options: object | None = None,
    ) -> RunResult:
        await asyncio.sleep(0)
        del dry_run, run_id
        self.calls.append((pipeline_name, options))
        if pipeline_name == self.failing_pipeline_name:
            raise RuntimeError("pipeline boom")
        return RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name=pipeline_name,
            run_id="00000000-0000-0000-0000-000000000102",
            run_type="incremental",
            started_at=FIXED_TEST_TIME,
            completed_at=FIXED_TEST_TIME,
        )


@dataclass
class _RecordingTransformService:
    calls: list[tuple[str, tuple[str, ...], bool]] = field(default_factory=list)

    async def run_step(
        self,
        *,
        workflow_name: str,
        step: TransformStepConfig,
        upstream_outputs: dict[str, object] | None = None,
        context_labels: dict[str, str] | None = None,
        completed_fingerprints: dict[str, str] | None = None,
        dry_run: bool = False,
        workflow_run_id: str | None = None,
        manifest_id: str | None = None,
        debug_export_enabled: bool = False,
        debug_export_dir: str | None = None,
        artifact_sink: object | None = None,
        created_at: object | None = None,
        destructive_commit_callback: object | None = None,
    ) -> WorkflowTransformExecutionResult:
        del workflow_name, context_labels, completed_fingerprints
        del destructive_commit_callback
        del workflow_run_id, manifest_id, debug_export_enabled
        del debug_export_dir, artifact_sink, created_at
        upstream_outputs = upstream_outputs or {}
        self.calls.append((step.step_id, tuple(sorted(upstream_outputs)), dry_run))
        return WorkflowTransformExecutionResult(
            step_id=step.step_id,
            transform_name=step.transform_name,
            status="success",
            fingerprint=f"fingerprint-{step.step_id}",
            output={
                "step_id": step.step_id,
                "upstream_step_ids": tuple(sorted(upstream_outputs)),
            },
        )


def _build_chembl_baseline_config() -> WorkflowConfig:
    return load_workflow_config(
        "chembl_baseline",
        config_dir=Path("configs/workflows"),
    )


def _build_chembl_baseline_metrics_config() -> WorkflowConfig:
    return WorkflowConfig(
        name="chembl_baseline",
        defaults=WorkflowRunOptionsConfig(run_type="backfill"),
        steps=(
            WorkflowStepConfig(
                step_id="chembl_assay",
                pipeline_name="chembl_assay",
            ),
            WorkflowStepConfig(
                step_id="chembl_target",
                pipeline_name="chembl_target",
            ),
            WorkflowStepConfig(
                step_id="chembl_publication",
                pipeline_name="chembl_publication",
            ),
        ),
    )


def test_workflow_runner_records_expected_pipeline_universe_for_baseline() -> None:
    metrics = _RecordingMetrics()
    service = WorkflowRunnerService(
        pipeline_runner=_PipelineRunner(),  # type: ignore[arg-type]
        transform_service=_RecordingTransformService(),  # type: ignore[arg-type]
        metrics=metrics,
    )

    service.record_expected_pipeline_metrics(_build_chembl_baseline_metrics_config())

    assert metrics.gauges == [
        (
            "bioetl_workflow_expected",
            1.0,
            {
                "workflow": "chembl_baseline",
                "provider": "chembl",
            },
        ),
        (
            "bioetl_workflow_pipeline_expected",
            1.0,
            {
                "workflow": "chembl_baseline",
                "pipeline": "chembl_assay",
                "run_type": "backfill",
                "provider": "chembl",
            },
        ),
        (
            "bioetl_workflow_pipeline_expected",
            1.0,
            {
                "workflow": "chembl_baseline",
                "pipeline": "chembl_target",
                "run_type": "backfill",
                "provider": "chembl",
            },
        ),
        (
            "bioetl_workflow_pipeline_expected",
            1.0,
            {
                "workflow": "chembl_baseline",
                "pipeline": "chembl_publication",
                "run_type": "backfill",
                "provider": "chembl",
            },
        ),
    ]


@pytest.mark.asyncio
async def test_workflow_runner_executes_pipeline_then_transform() -> None:
    metrics = _RecordingMetrics()
    pipeline_runner = _PipelineRunner()
    registry = WorkflowTransformRegistry()
    registry.register("normalize_activity", lambda _spec, upstream: sorted(upstream))
    transform_service = WorkflowTransformService(
        registry=registry,
        metrics=metrics,
        monotonic=iter([1.0, 1.2]).__next__,
    )
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=transform_service,
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(
                    limit=25,
                    required_persistence_profile="degraded_observable",
                ),
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
            ),
        ),
    )

    result = await service.run_workflow(
        config,
        workflow_run_id="workflow-run-42",
    )

    assert result.status == "success"
    assert [step.step_id for step in result.steps] == ["extract", "normalize"]
    assert result.steps[0].child_run_id == ("00000000-0000-0000-0000-000000000101")
    assert pipeline_runner.calls[0][0] == "chembl_activity"
    assert pipeline_runner.calls[0][1].required_persistence_profile == (
        "degraded_observable"
    )
    assert pipeline_runner.calls[0][1].workflow_id == "activity_workflow"
    assert pipeline_runner.calls[0][1].workflow_run_id == "workflow-run-42"
    assert pipeline_runner.calls[0][1].workflow_name == "activity_workflow"
    assert pipeline_runner.calls[0][1].workflow_step_id == "extract"
    assert metrics.gauges[-1] == (
        "bioetl_workflow_current_status",
        0.0,
        {
            "workflow": "activity_workflow",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    )
    assert metrics.counters[-1] == (
        "bioetl_workflow_runs_total",
        1,
        {
            "workflow": "activity_workflow",
            "status": "success",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    )
    assert any(
        name == "bioetl_workflow_step_duration_seconds"
        and labels
        == {
            "workflow": "activity_workflow",
            "step_kind": "pipeline",
            "status": "success",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        }
        for name, _value, labels in metrics.histograms
    )


@pytest.mark.asyncio
async def test_workflow_runner_returns_failed_step_result_for_pipeline_error() -> None:
    metrics = _RecordingMetrics()
    transform_service = WorkflowTransformService(
        registry=WorkflowTransformRegistry(),
        metrics=metrics,
        monotonic=iter([1.0, 1.2]).__next__,
    )
    service = WorkflowRunnerService(
        pipeline_runner=_FailingPipelineRunner(),  # type: ignore[arg-type]
        transform_service=transform_service,
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(limit=25),
            ),
        ),
    )

    result = await service.run_workflow(config)

    assert result.status == "failed"
    assert metrics.gauges[-1] == (
        "bioetl_workflow_current_status",
        2.0,
        {
            "workflow": "activity_workflow",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    )
    assert result.steps[0].status == "failed"
    assert result.steps[0].error_type == "RuntimeError"
    assert metrics.counters[-1] == (
        "bioetl_workflow_runs_total",
        1,
        {
            "workflow": "activity_workflow",
            "status": "failed",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    )


@pytest.mark.asyncio
async def test_workflow_runner_terminalizes_attribute_error_step_failure() -> None:
    """AttributeError must not bypass step failure recording (#6732 / P1-WF-STATE-002)."""
    metrics = _RecordingMetrics()
    service = WorkflowRunnerService(
        pipeline_runner=_AttributeErrorPipelineRunner(),  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=WorkflowTransformRegistry(),
            metrics=metrics,
        ),
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
            ),
        ),
    )

    result = await service.run_workflow(config)

    assert result.status == "failed"
    assert result.steps[0].status == "failed"
    assert result.steps[0].error_type == "AttributeError"
    assert metrics.counters[-1] == (
        "bioetl_workflow_runs_total",
        1,
        {
            "workflow": "activity_workflow",
            "status": "failed",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    )


@pytest.mark.asyncio
async def test_pipeline_exception_preserves_reciprocal_child_anchors() -> None:
    metrics = _RecordingMetrics()
    service = WorkflowRunnerService(
        pipeline_runner=_IdentifiedFailingPipelineRunner(),  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=WorkflowTransformRegistry(),
            metrics=metrics,
        ),
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
            ),
        ),
    )

    result = await service.run_workflow(config)

    failed_step = result.steps[0]
    assert failed_step.status == "failed"
    assert failed_step.child_run_id == _IdentifiedPipelineError.run_id
    assert failed_step.child_manifest_id == _IdentifiedPipelineError.manifest_id


@pytest.mark.asyncio
async def test_workflow_runner_marks_downstream_steps_skipped_after_failure() -> None:
    metrics = _RecordingMetrics()
    service = WorkflowRunnerService(
        pipeline_runner=_FailingPipelineRunner(),  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=WorkflowTransformRegistry(),
            metrics=metrics,
            monotonic=iter([1.0, 1.2]).__next__,
        ),
        metrics=metrics,
        monotonic=iter([5.0, 5.3]).__next__,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(limit=25),
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
            ),
        ),
    )

    result = await service.run_workflow(config)

    assert result.status == "failed"
    assert [step.status for step in result.steps] == ["failed", "skipped"]
    assert result.steps[1].error_type == "UpstreamStepFailed"
    assert "extract" in (result.steps[1].error_message or "")
    assert (
        "bioetl_workflow_step_events_total",
        1,
        {
            "workflow": "activity_workflow",
            "step_kind": "transform",
            "status": "skipped",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    ) in metrics.counters


@pytest.mark.asyncio
async def test_workflow_runner_executes_chembl_baseline_in_dependency_order() -> None:
    metrics = _RecordingMetrics()
    pipeline_runner = _PipelineRunner()
    transform_service = _RecordingTransformService()
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=transform_service,  # type: ignore[arg-type]
        metrics=metrics,
    )
    config = _build_chembl_baseline_config()
    events: list[tuple[str, str, str | None, str | None]] = []

    result = await service.run_workflow(
        config,
        step_started_callback=lambda step, fingerprint=None: events.append(
            (
                "started",
                step.step_id,
                getattr(step, "pipeline_name", getattr(step, "transform_name", None)),
                fingerprint,
            )
        ),
        step_completed_callback=lambda result: events.append(
            ("completed", result.step_id, result.status, None)
        ),
    )

    assert result.status == "success"
    assert [step.step_id for step in result.steps] == list(config.topological_step_ids)
    assert [pipeline_name for pipeline_name, _options in pipeline_runner.calls] == [
        "chembl_assay",
        "chembl_target",
        "chembl_publication",
    ]
    assert all(
        options.workflow_id == "chembl_baseline"
        for _pipeline_name, options in pipeline_runner.calls
    )
    assert transform_service.calls == [
        (
            "reconcile_assay_target_orphans",
            ("run_chembl_assay", "run_chembl_target"),
            False,
        ),
        (
            "reconcile_assay_publication_orphans",
            ("reconcile_assay_target_orphans", "run_chembl_publication"),
            False,
        ),
        (
            "reconcile_target_assay_orphans",
            ("reconcile_assay_publication_orphans",),
            False,
        ),
        (
            "reconcile_publication_assay_orphans",
            ("reconcile_target_assay_orphans",),
            False,
        ),
    ]
    assert [event[:3] for event in events] == [
        ("started", "run_chembl_assay", "chembl_assay"),
        ("completed", "run_chembl_assay", "success"),
        ("started", "run_chembl_target", "chembl_target"),
        ("completed", "run_chembl_target", "success"),
        (
            "started",
            "reconcile_assay_target_orphans",
            "reconcile_foreign_keys",
        ),
        ("completed", "reconcile_assay_target_orphans", "success"),
        ("started", "run_chembl_publication", "chembl_publication"),
        ("completed", "run_chembl_publication", "success"),
        (
            "started",
            "reconcile_assay_publication_orphans",
            "reconcile_foreign_keys",
        ),
        ("completed", "reconcile_assay_publication_orphans", "success"),
        (
            "started",
            "reconcile_target_assay_orphans",
            "reconcile_foreign_keys",
        ),
        ("completed", "reconcile_target_assay_orphans", "success"),
        (
            "started",
            "reconcile_publication_assay_orphans",
            "reconcile_foreign_keys",
        ),
        ("completed", "reconcile_publication_assay_orphans", "success"),
    ]
    assert all(isinstance(events[index][3], str) for index in (4, 8, 10, 12))


@pytest.mark.asyncio
async def test_workflow_runner_skips_chembl_baseline_reconciliation_after_failure() -> (
    None
):
    metrics = _RecordingMetrics()
    pipeline_runner = _SelectiveFailingPipelineRunner("chembl_target")
    transform_service = _RecordingTransformService()
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=transform_service,  # type: ignore[arg-type]
        metrics=metrics,
    )
    config = _build_chembl_baseline_config()

    result = await service.run_workflow(config)

    assert result.status == "failed"
    assert [step.status for step in result.steps] == [
        "success",
        "failed",
        "skipped",
        "skipped",
        "skipped",
        "skipped",
        "skipped",
    ]
    assert transform_service.calls == []
    assert [pipeline_name for pipeline_name, _options in pipeline_runner.calls] == [
        "chembl_assay",
        "chembl_target",
    ]


@pytest.mark.asyncio
async def test_workflow_runner_forwards_workflow_level_dry_run_to_transforms() -> None:
    metrics = _RecordingMetrics()
    transform_service = _RecordingTransformService()
    service = WorkflowRunnerService(
        pipeline_runner=_PipelineRunner(),  # type: ignore[arg-type]
        transform_service=transform_service,  # type: ignore[arg-type]
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="repair_workflow",
        defaults=WorkflowRunOptionsConfig(dry_run=True),
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
            ),
            TransformStepConfig(
                step_id="repair",
                transform_name="reconcile_foreign_keys",
                depends_on=("extract",),
            ),
        ),
    )

    result = await service.run_workflow(config)

    assert result.status == "success"
    assert transform_service.calls == [("repair", ("extract",), True)]


@pytest.mark.asyncio
async def test_workflow_runner_skips_completed_steps_on_resume() -> None:
    metrics = _RecordingMetrics()
    pipeline_runner = _PipelineRunner()
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=WorkflowTransformRegistry(),
            metrics=metrics,
        ),
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(limit=25),
            ),
            WorkflowStepConfig(
                step_id="enrich",
                pipeline_name="chembl_assay",
                depends_on=("extract",),
            ),
        ),
    )

    result = await service.run_workflow(
        config,
        completed_step_ids=frozenset({"extract"}),
    )

    assert result.status == "success"
    assert [step.status for step in result.steps] == ["skipped", "success"]
    assert result.steps[0].error_type == "AlreadyCompletedOnResume"
    assert len(pipeline_runner.calls) == 1
    assert pipeline_runner.calls[0][0] == "chembl_assay"


@pytest.mark.asyncio
async def test_workflow_runner_callbacks_follow_start_then_complete_order() -> None:
    metrics = _RecordingMetrics()
    pipeline_runner = _PipelineRunner()
    registry = WorkflowTransformRegistry()
    registry.register("normalize_activity", lambda _spec, upstream: sorted(upstream))
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=registry,
            metrics=metrics,
        ),
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
            ),
        ),
    )
    events: list[tuple[str, str, str | None, str | None]] = []

    result = await service.run_workflow(
        config,
        step_started_callback=lambda step, fingerprint=None: events.append(
            (
                "started",
                step.step_id,
                getattr(step, "transform_name", None),
                fingerprint,
            )
        ),
        step_completed_callback=lambda result: events.append(
            ("completed", result.step_id, result.status, None)
        ),
    )

    assert result.status == "success"
    assert events[0] == ("started", "extract", None, None)
    assert events[1] == ("completed", "extract", "success", None)
    assert events[2][0:3] == ("started", "normalize", "normalize_activity")
    assert isinstance(events[2][3], str)
    assert events[3] == ("completed", "normalize", "success", None)


@pytest.mark.asyncio
async def test_workflow_runner_callbacks_record_failed_then_skipped_transition() -> (
    None
):
    metrics = _RecordingMetrics()
    service = WorkflowRunnerService(
        pipeline_runner=_FailingPipelineRunner(),  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=WorkflowTransformRegistry(),
            metrics=metrics,
        ),
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
            ),
        ),
    )
    events: list[tuple[str, str, str | None]] = []

    result = await service.run_workflow(
        config,
        step_started_callback=lambda step, fingerprint=None: events.append(
            ("started", step.step_id, fingerprint)
        ),
        step_completed_callback=lambda result: events.append(
            ("completed", result.step_id, result.status)
        ),
    )

    assert result.status == "failed"
    assert events == [
        ("started", "extract", None),
        ("completed", "extract", "failed"),
        ("completed", "normalize", "skipped"),
    ]


@pytest.mark.asyncio
async def test_workflow_runner_transform_fingerprint_skip_still_emits_callbacks() -> (
    None
):
    metrics = _RecordingMetrics()
    pipeline_runner = _PipelineRunner()
    registry = WorkflowTransformRegistry()
    registry.register("normalize_activity", lambda _spec, _upstream: "should-not-run")
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=registry,
            metrics=metrics,
        ),
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
            ),
        ),
    )
    transform_step = config.get_step("normalize")
    assert isinstance(transform_step, TransformStepConfig)
    fingerprint = WorkflowTransformSpec.from_step(transform_step).fingerprint
    events: list[tuple[str, str, str | None]] = []

    result = await service.run_workflow(
        config,
        completed_transform_fingerprints={"normalize": fingerprint},
        step_started_callback=lambda step, fingerprint=None: events.append(
            ("started", step.step_id, fingerprint)
        ),
        step_completed_callback=lambda result: events.append(
            ("completed", result.step_id, result.status)
        ),
    )

    assert result.status == "success"
    assert result.steps[1].status == "skipped"
    assert events[0] == ("started", "extract", None)
    assert events[1] == ("completed", "extract", "success")
    assert events[2][0:2] == ("started", "normalize")
    assert isinstance(events[2][2], str)
    assert events[3] == ("completed", "normalize", "skipped")
