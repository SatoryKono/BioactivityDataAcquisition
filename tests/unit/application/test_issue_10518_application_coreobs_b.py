"""Behavior-focused unit tests for GitHub issue #10518 (application, core+observability B).

Covers coverage residuals measured against tests/unit/application for:
pipeline_metrics, _record_processor_span_support, _runner_finalize,
base_transformer_dependency_helpers_mixin, batch_executor_dq_helpers,
batch_executor_loop_helpers, lifecycle.checkpoint_manager,
record_processor_config, control_plane_integrity_metrics, replay_write_risk.
"""

from __future__ import annotations

import sys
from uuid import UUID
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# pipeline_metrics (missing: 183, 267, 295, 296, 297, 346, 386)
# ---------------------------------------------------------------------------

from bioetl.application.observability.pipeline_metrics import (
    PipelineMetricsRecorder,
    _PipelineMetricsRecorderCore,
)


def test_record_pipeline_stage_expected_sets_gauge():
    metrics = MagicMock()
    recorder = _PipelineMetricsRecorderCore(metrics=metrics, pipeline="pipe")
    recorder.record_pipeline_stage_expected(stage="silver", expected=True)
    metrics.set_gauge.assert_called_once()
    name, value, labels = metrics.set_gauge.call_args.args
    assert name == "bioetl_pipeline_stage_expected"
    assert value == 1.0
    assert labels["stage"] == "silver"


def test_record_batch_lifecycle_event_without_metrics_is_noop():
    recorder = _PipelineMetricsRecorderCore(metrics=None, pipeline="pipe")
    recorder.record_batch_lifecycle_event(
        run_type="incremental", event="flush", stage="bronze", status="ok"
    )


def test_guarded_recorders_without_metrics_are_noop():
    core = _PipelineMetricsRecorderCore(metrics=None, pipeline="pipe")
    core.record_pipeline_stage_expected(stage="silver", expected=False)
    core.record_output_artifact_publication(stage="gold", status="ok")
    core.record_batch_lifecycle_event(
        run_type="incremental",
        event="flush",
        stage="bronze",
        status="ok",
        count=0,
    )
    composite = PipelineMetricsRecorder(metrics=None, pipeline="pipe")
    composite.record_composite_phase_errors(phase="build", error_kind="io")
    composite.record_composite_phase_retries(phase="build", retry_kind="resume")


def test_record_batch_lifecycle_event_with_records():
    metrics = MagicMock()
    recorder = _PipelineMetricsRecorderCore(metrics=metrics, pipeline="pipe")
    recorder.record_batch_lifecycle_event(
        run_type="incremental",
        event="flush",
        stage="bronze",
        status="ok",
        record_count=4,
    )
    names = [c.args[0] for c in metrics.increment_counter.call_args_list]
    assert "bioetl_batch_lifecycle_events_total" in names
    assert "bioetl_batch_lifecycle_records_total" in names


def test_record_output_artifact_publication():
    metrics = MagicMock()
    recorder = _PipelineMetricsRecorderCore(metrics=metrics, pipeline="pipe")
    recorder.record_output_artifact_publication(stage="gold", status="ok")
    metrics.increment_counter.assert_called_once()
    assert (
        metrics.increment_counter.call_args.args[0]
        == "bioetl_output_artifact_publication_events_total"
    )


def test_record_composite_phase_errors():
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics=metrics, pipeline="pipe")
    recorder.record_composite_phase_errors(phase="build", error_kind="io")
    metrics.increment_counter.assert_called_once()
    assert (
        metrics.increment_counter.call_args.args[0]
        == "bioetl_composite_phase_errors_total"
    )


def test_record_composite_phase_retries():
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics=metrics, pipeline="pipe")
    recorder.record_composite_phase_retries(phase="build", retry_kind="resume")
    metrics.increment_counter.assert_called_once()
    assert (
        metrics.increment_counter.call_args.args[0]
        == "bioetl_composite_phase_retries_total"
    )


# ---------------------------------------------------------------------------
# _record_processor_span_support (missing: 54, 55, 56, 57, 88, 89)
# ---------------------------------------------------------------------------

from bioetl.application.core import _record_processor_span_support as spansupport
from bioetl.application.core._record_processor_span_support import (
    RecordProcessorSpanExecutor,
)


async def test_execute_with_span_calls_on_error_and_reraises():
    async def _boom():
        raise ValueError("nope")

    on_error = MagicMock()
    executor = RecordProcessorSpanExecutor(tracer=MagicMock())
    with pytest.raises(ValueError, match="nope"):
        await executor.execute_with_span(
            "stage", _boom(), "batch-1", 3, on_error=on_error
        )
    on_error.assert_called_once()


async def test_execute_with_span_operation_error_without_handler():
    async def _boom():
        raise ValueError("nope")

    executor = RecordProcessorSpanExecutor(tracer=MagicMock())
    with pytest.raises(ValueError, match="nope"):
        await executor.execute_with_span("stage", _boom(), "batch-1", 3)


async def test_execute_with_span_reraises_unexpected_errors():
    class _Weird(BaseException):
        pass

    async def _boom():
        raise _Weird()

    executor = RecordProcessorSpanExecutor(tracer=MagicMock())
    with pytest.raises(_Weird):
        await executor.execute_with_span("stage", _boom(), "batch-1", 3)


async def test_execute_transform_with_span_operation_error():
    transformer = MagicMock()
    executor = RecordProcessorSpanExecutor(tracer=MagicMock())
    with (
        patch.object(
            spansupport,
            "_run_transform_batch",
            new=AsyncMock(side_effect=ValueError("bad batch")),
        ),
        pytest.raises(ValueError, match="bad batch"),
    ):
        await executor.execute_transform_with_span(
            transformer=transformer,
            records=[{"a": 1}],
            batch_id="batch-1",
            start_index=0,
        )


# ---------------------------------------------------------------------------
# _runner_finalize (missing: 83, 87, 88, 89, 90, 91)
# ---------------------------------------------------------------------------

from bioetl.application.core._runner_finalize import finalize_contract_evidence


def test_finalize_contract_evidence_records_with_lock_owner():
    recorder = MagicMock()
    runner = SimpleNamespace(
        _contract_evidence_recorder=recorder,
        manifest_id="m1",
        _contract_evidence_context=SimpleNamespace(
            contract_ref="c", contract_schema_hash="h", resume=False
        ),
        _lock_runtime_service=SimpleNamespace(
            get_context=lambda: SimpleNamespace(owner_id="owner-1")
        ),
    )
    finalize_contract_evidence(runner)
    recorder.record.assert_called_once()
    args, _ = recorder.record.call_args
    assert args[0] == "m1"


def test_finalize_contract_evidence_skips_without_recorder():
    runner = SimpleNamespace(
        _contract_evidence_recorder=None,
        manifest_id="m1",
    )
    assert finalize_contract_evidence(runner) is None


# ---------------------------------------------------------------------------
# base_transformer_dependency_helpers_mixin (missing: 46, 47, 48, 130, 153, 159)
# ---------------------------------------------------------------------------

import dataclasses

from bioetl.application.core.base_transformer_dependency_helpers_mixin import (
    _BaseTransformerDependencyHelpersMixin,
)


def _owner(**attrs):
    mixin = _BaseTransformerDependencyHelpersMixin()
    for key, value in attrs.items():
        setattr(mixin, key, value)
    return mixin


def test_hash_pii_list_delegates():
    owner = _owner(_pii_hasher=MagicMock(hash_list=lambda v: ["h1"]))
    assert owner.hash_pii_list(["a@b.c"]) == ["h1"]


def test_entity_to_silver_record_rejects_non_dataclass():
    owner = _owner(
        _contract_policy=SimpleNamespace(rename_map={}),
        _normalize_lineage_value=lambda f, v: v,
    )
    with pytest.raises(TypeError, match="dataclass"):
        owner.entity_to_silver_record("nope")


def test_entity_to_silver_record_applies_rename_map():
    @dataclasses.dataclass
    class _Entity:
        old_name: str = "v"

    owner = _owner(
        _contract_policy=SimpleNamespace(rename_map={"old_name": "new_name"}),
    )
    owner._normalize_lineage_value = staticmethod(lambda f, v: v)
    record = owner.entity_to_silver_record(_Entity())
    assert record == {"new_name": "v"}


def test_apply_hash_policy_explicit_identity_returns_copy():
    identity = SimpleNamespace(has_explicit_content_hash_policy=lambda: True)
    policy = SimpleNamespace(hash_include=frozenset(), hash_exclude=frozenset())
    data = {"a": 1}
    out = _BaseTransformerDependencyHelpersMixin._apply_hash_policy(
        identity, policy, data
    )
    assert out == data and out is not data


def test_apply_hash_policy_include_scoping():
    identity = SimpleNamespace(has_explicit_content_hash_policy=lambda: False)
    policy = SimpleNamespace(
        hash_include=frozenset({"a"}), hash_exclude=frozenset({"b"})
    )
    out = _BaseTransformerDependencyHelpersMixin._apply_hash_policy(
        identity, policy, {"a": 1, "b": 2}
    )
    assert out == {"a": 1}


# ---------------------------------------------------------------------------
# batch_executor_dq_helpers (missing: 39, 40, 62, 89, 106, 194)
# ---------------------------------------------------------------------------

from bioetl.application.core import batch_executor_dq_helpers as dqhelpers


def test_dataframe_error_types_without_polars(monkeypatch):
    monkeypatch.setitem(sys.modules, "polars", None)
    assert dqhelpers.dataframe_error_types() == dqhelpers._DQ_DATAFRAME_ERRORS


def test_stringify_value_serializes_nested():
    out = dqhelpers.stringify_value({"b": 1}, {"k"}, "k")
    assert out == '{"b": 1}'


def test_build_dataframe_from_records_empty():
    assert (
        dqhelpers.build_dataframe_from_records(
            records=[], logger=MagicMock()
        )
        is None
    )


def test_build_dataframe_from_records_blocked_polars_warns(monkeypatch):
    monkeypatch.setitem(sys.modules, "polars", None)
    logger = MagicMock()
    metrics = MagicMock()
    records = [{"a": {"x": 1}}, {"a": "text"}, {"a": None}]
    assert (
        dqhelpers.build_dataframe_from_records(
            records=records,
            logger=logger,
            metrics=metrics,
            pipeline="pipe",
            stage="silver",
        )
        is None
    )
    logger.warning.assert_called_once()


def test_build_dq_report_context_requires_started_at():
    context = SimpleNamespace(
        run_id="r1", started_at=None, replay_timestamp_anchor=None
    )
    config = SimpleNamespace(
        table_config=SimpleNamespace(
            primary_keys=[], silver_table="s", gold_table="g"
        ),
        dq_config=None,
        entity_type="e",
        pipeline_name="p",
        provider="pr",
        bronze_output_path=None,
        silver_output_path=None,
        gold_output_path=None,
        scd_config=None,
        flat_structure=False,
    )
    with pytest.raises(ValueError, match="started_at"):
        dqhelpers.build_dq_report_context(
            context=context,
            config=config,
            bronze_records=[],
            silver_records=[],
            gold_records=[],
            source_batch_ids=[],
            last_bronze_path=None,
            records_fetched=0,
            records_quarantined=0,
            build_dataframe=lambda records, stage: None,
        )


# ---------------------------------------------------------------------------
# batch_executor_loop_helpers (missing: 120, 121, 130, 139, 140, 147)
# ---------------------------------------------------------------------------

from bioetl.application.core import batch_executor_loop_helpers as loophelpers
from bioetl.application.core.batch_executor_loop_flow import (
    build_start_index as flow_build_start_index,
)


def test_append_record_and_update_batch_size():
    loop_state = loophelpers.create_batch_extraction_loop_state(
        batch_size=10, check_interval=5
    )
    memory = MagicMock()
    memory.check_pressure = lambda size, interval, fetched: 7
    loophelpers.append_record_and_update_batch_size(
        loop_state=loop_state,
        raw_record={"a": 1},
        memory_manager=memory,
        records_fetched=3,
    )
    assert loop_state.batch == [{"a": 1}]
    assert loop_state.current_batch_size == 7


def test_should_flush_batch_threshold():
    loop_state = loophelpers.create_batch_extraction_loop_state(
        batch_size=1, check_interval=5
    )
    assert loophelpers.should_flush_batch(loop_state) is False
    loop_state.batch.append({"a": 1})
    assert loophelpers.should_flush_batch(loop_state) is True


def test_reset_batch_after_flush_recovers():
    loop_state = loophelpers.create_batch_extraction_loop_state(
        batch_size=10, check_interval=5
    )
    loop_state.batch.append({"a": 1})
    memory = MagicMock()
    memory.maybe_recover = lambda size: 5
    loophelpers.reset_batch_after_flush(
        loop_state=loop_state, memory_manager=memory
    )
    assert loop_state.batch == []
    assert loop_state.current_batch_size == 5


def test_build_start_index_matches_flow():
    batch = [{"a": 1}, {"a": 2}]
    assert loophelpers.build_start_index(
        records_fetched=10, batch=batch
    ) == flow_build_start_index(records_fetched=10, batch=batch)


# ---------------------------------------------------------------------------
# lifecycle.checkpoint_manager (missing: 97, 111, 115, 120, 121, 122)
# ---------------------------------------------------------------------------

from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointRuntimeParams,
    CheckpointRuntimeService,
)
from bioetl.domain.types import RunID


def _checkpoint_service(**overrides):
    params = CheckpointRuntimeParams(
        pipeline_name="pipe",
        run_id=RunID(UUID(int=2001)),
        resume=True,
    )
    kwargs = {
        "checkpoint_port": AsyncMock(),
        "logger": MagicMock(),
        "identity": params,
    }
    kwargs.update(overrides)
    return CheckpointRuntimeService(**kwargs)


def test_current_metadata_property():
    svc = _checkpoint_service()
    assert svc.current_metadata is None


async def test_load_checkpoint_data_by_manifest_id():
    port = AsyncMock()
    port.load_for_manifest_id = AsyncMock(return_value=("run", {"a": 1}))
    svc = _checkpoint_service(checkpoint_port=port)
    svc._resume_manifest_id = "m1"
    assert await svc._load_checkpoint_data() == ("run", {"a": 1})
    port.load_for_manifest_id.assert_awaited_once_with("m1")


async def test_load_checkpoint_data_by_run_id():
    run_id = RunID(UUID(int=2002))
    port = AsyncMock()
    port.load_for_run = AsyncMock(return_value=("run", {"a": 1}))
    svc = _checkpoint_service(checkpoint_port=port)
    svc._resume_run_id = run_id
    assert await svc._load_checkpoint_data() == ("run", {"a": 1})
    port.load_for_run.assert_awaited_once_with("pipe", run_id)


async def test_load_checkpoint_data_failure_emits_metric():
    port = AsyncMock()
    port.load = AsyncMock(side_effect=OSError("down"))
    metrics = MagicMock()
    svc = _checkpoint_service(checkpoint_port=port, metrics=metrics)
    with pytest.raises(OSError, match="down"):
        await svc._load_checkpoint_data()
    metrics.increment_counter.assert_called_once()
    _, _, labels = metrics.increment_counter.call_args.args
    assert labels["status"] == "failed"


# ---------------------------------------------------------------------------
# record_processor_config (missing: 46, 49, 51, 62, 65, 70)
# ---------------------------------------------------------------------------

from bioetl.application.core.record_processor_config import (
    ContentHashPolicyGroup,
    ContentHashVersionPolicy,
)


def test_hash_policy_group_rejects_empty_active_version():
    with pytest.raises(ValueError, match="active_version"):
        ContentHashPolicyGroup(
            active_version="  ",
            policies=(ContentHashVersionPolicy(version="v1"),),
        )


def test_hash_policy_group_rejects_duplicate_versions():
    with pytest.raises(ValueError, match="unique"):
        ContentHashPolicyGroup(
            active_version="v1",
            policies=(
                ContentHashVersionPolicy(version="v1"),
                ContentHashVersionPolicy(version="v1"),
            ),
        )


def test_hash_policy_group_rejects_unknown_active_version():
    with pytest.raises(ValueError, match="active_version"):
        ContentHashPolicyGroup(
            active_version="v9",
            policies=(ContentHashVersionPolicy(version="v1"),),
        )


def test_hash_policy_group_active_policy_and_versions():
    group = ContentHashPolicyGroup(
        active_version="v1",
        policies=(
            ContentHashVersionPolicy(version="v1"),
            ContentHashVersionPolicy(version="v2"),
        ),
    )
    assert group.active_policy.version == "v1"
    assert group.versions == ("v1", "v2")
    assert group.is_multi_version is True
    assert group.for_version("missing") is None


def test_hash_policy_group_requires_projected_hashes():
    single = ContentHashPolicyGroup(
        active_version="v1",
        policies=(ContentHashVersionPolicy(version="v1"),),
        affects_hash=True,
    )
    assert single.requires_projected_hashes is False
    multi = ContentHashPolicyGroup(
        active_version="v1",
        policies=(
            ContentHashVersionPolicy(version="v1"),
            ContentHashVersionPolicy(version="v2"),
        ),
        affects_hash=True,
    )
    assert multi.requires_projected_hashes is True


# ---------------------------------------------------------------------------
# control_plane_integrity_metrics (missing: 63, 64, 89, 120, 121, 154)
# ---------------------------------------------------------------------------

from bioetl.application.observability import control_plane_integrity_metrics as integrity
from bioetl.domain.control_plane import RunManifest


def test_manifest_expects_ledger_string_flags():
    assert (
        integrity.manifest_expects_ledger(
            RunManifest(launch_context={"run_ledger_enabled": "yes"})
        )
        is True
    )
    assert (
        integrity.manifest_expects_ledger(
            RunManifest(launch_context={"run_ledger_enabled": "no"})
        )
        is False
    )


def test_manifest_expects_ledger_nested_config():
    manifest = RunManifest(
        launch_context={"pipeline": {"ledger_enabled": "off"}}
    )
    assert integrity.manifest_expects_ledger(manifest) is False


def test_ledger_matches_manifest_read_failure():
    manifest = RunManifest()
    ledger = SimpleNamespace(
        list_entries=MagicMock(side_effect=OSError("down")),
        list_entries_by_run_id=MagicMock(),
    )
    assert integrity._ledger_matches_manifest(manifest, ledger) is False


def test_refresh_skips_manifests_without_ledger():
    manifest = RunManifest(launch_context={"run_ledger_enabled": False})
    service = integrity.ControlPlaneIntegrityMetricsService(
        manifest_port=SimpleNamespace(list_all=lambda: [manifest]),
        ledger_port=MagicMock(),
        metrics=MagicMock(),
    )
    assert service.refresh() == ()


# ---------------------------------------------------------------------------
# replay_write_risk (missing: 49, 59, 103, 110, 122, 204)
# ---------------------------------------------------------------------------

from bioetl.application.observability import replay_write_risk as risk


def test_replay_mode_launch_is_reprocessing():
    manifest = RunManifest(launch_context={"replay_mode": "rebuild"})
    assert risk.assess_replay_write_risks(manifest) == frozenset()


def test_resume_launch_is_reprocessing_with_sink_risk():
    manifest = RunManifest(
        launch_context={"resume": True},
        runtime_config={"silver_write_mode": "append"},
    )
    assert risk._is_reprocessing_manifest(manifest) is True
    assert risk.ReplayWriteRiskClassification.DUPLICATE in (
        risk.assess_replay_write_risks(manifest)
    )


def test_non_mapping_configs_are_skipped():
    manifest = RunManifest(replay_of_run_id="r1")
    object.__setattr__(manifest, "runtime_config", "junk")
    object.__setattr__(manifest, "resolved_config", "junk")
    assert risk.assess_replay_write_risks(manifest) == frozenset()


def test_legacy_append_sink_is_duplicate_risk():
    manifest = RunManifest(
        replay_of_run_id="r1",
        runtime_config={"silver_write_mode": "append"},
    )
    assert risk.ReplayWriteRiskClassification.DUPLICATE in (
        risk.assess_replay_write_risks(manifest)
    )


def test_append_semantic_sink_is_duplicate_risk():
    manifest = RunManifest(
        replay_of_run_id="r1",
        launch_context={"append_mode_semantic_sinks": ["sink-a"]},
    )
    assert risk.ReplayWriteRiskClassification.DUPLICATE in (
        risk.assess_replay_write_risks(manifest)
    )


def test_clear_before_run_is_overwrite_risk():
    manifest = RunManifest(
        replay_of_run_id="r1",
        launch_context={"clear_before_run": True},
    )
    assert risk.ReplayWriteRiskClassification.OVERWRITE in (
        risk.assess_replay_write_risks(manifest)
    )


def test_emit_metrics_increments_detected_risks():
    manifest = RunManifest(
        replay_of_run_id="r1",
        runtime_config={"silver_write_mode": "append"},
    )
    metrics = MagicMock()
    risk.emit_replay_write_risk_metrics(metrics, manifest)
    incremented = [
        c.kwargs.get("risk_type", c.args[2].get("risk_type"))
        if len(c.args) > 2
        else c.kwargs.get("risk_type")
        for c in metrics.increment_counter.call_args_list
    ]
    assert "duplicate" in incremented


def test_emit_metrics_without_metrics_is_noop():
    manifest = RunManifest()
    assert risk.emit_replay_write_risk_metrics(None, manifest) is None
