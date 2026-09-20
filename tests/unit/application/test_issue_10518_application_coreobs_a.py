"""Behavior-focused unit tests for GitHub issue #10518 (application, core+observability A).

Covers coverage residuals measured against tests/unit/application for:
control_plane_archive, checkpoint_validation, _filtered_data_source_support,
_structural_policy_evaluation, batch_memory_decision_policy,
publication_term_extraction_mixin, control_plane_evidence.service,
_runner_support, batch_executor_state_flow, control_plane_evidence.models.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# control_plane_archive (missing: 63, 64, 71, 88-106)
# ---------------------------------------------------------------------------

from bioetl.composition import control_plane_archive as cpa
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.domain.control_plane import RunManifest


def _success_result(**overrides):
    base = {
        "status": PipelineRunResult.SUCCESS,
        "pipeline_name": "pipe",
        "run_id": str(UUID(int=4001)),
        "run_type": "incremental",
        "manifest_id": "m1",
    }
    base.update(overrides)
    return RunResult(**base)


def test_archive_skipped_on_invalid_run_id():
    result = _success_result(run_id="not-a-uuid")
    ok, reason = cpa.archive_successful_run(
        result=result,
        options=None,
        data_root="/tmp",
        archive_root=None,
        report_root=None,
    )
    assert (ok, reason) == (None, "archive_skipped")


def test_archive_successful_run_delegates_to_pack(tmp_path, monkeypatch):
    manifest = RunManifest(pipeline_name="pipe")
    result = _success_result(
        run_id=str(manifest.run_id), pipeline_name="pipe", manifest_id="m1"
    )

    class FakeManifests:
        def __init__(self, **kwargs):
            pass

        def get_by_run_id(self, run_id):
            return manifest

    plan = SimpleNamespace(resolution_issues=["boom"], artifacts=[])
    planner_calls = {}

    class FakePlanner:
        def __init__(self, **kwargs):
            pass

        def plan_for_manifest(self, *args, **kwargs):
            planner_calls["called"] = True
            return plan

    monkeypatch.setattr(cpa, "FileRunManifestStore", FakeManifests)
    monkeypatch.setattr(cpa, "FileControlPlaneArtifactLifecycleStore", FakePlanner)
    ok, reason = cpa.archive_successful_run(
        result=result,
        options=None,
        data_root=tmp_path,
        archive_root=tmp_path / "arch",
        report_root=None,
    )
    assert (ok, reason) == (None, "archive_source_evidence_incomplete")
    assert planner_calls["called"]


def _pack_kwargs(tmp_path, manifest):
    return {
        "manifest": manifest,
        "data_root": tmp_path,
        "archive_root": tmp_path / "arch",
        "report_root": None,
        "control_root": tmp_path / "control",
    }


def test_create_or_verify_pack_incomplete_plan(tmp_path, monkeypatch):
    manifest = RunManifest(pipeline_name="pipe")

    class FakePlanner:
        def __init__(self, **kwargs):
            pass

        def plan_for_manifest(self, *args, **kwargs):
            return SimpleNamespace(resolution_issues=[], artifacts=[])

    monkeypatch.setattr(cpa, "FileControlPlaneArtifactLifecycleStore", FakePlanner)
    ok, reason = cpa._create_or_verify_pack(**_pack_kwargs(tmp_path, manifest))
    assert (ok, reason) == (None, "archive_source_evidence_incomplete")


def test_create_or_verify_pack_returns_existing_verification(tmp_path, monkeypatch):
    manifest = RunManifest(pipeline_name="pipe")

    class FakePlanner:
        def __init__(self, **kwargs):
            pass

        def plan_for_manifest(self, *args, **kwargs):
            return SimpleNamespace(resolution_issues=[], artifacts=[object()])

    store = SimpleNamespace(
        verify=MagicMock(return_value=(True, "archive_verified")),
        create=MagicMock(),
    )
    monkeypatch.setattr(cpa, "FileControlPlaneArtifactLifecycleStore", FakePlanner)
    monkeypatch.setattr(cpa, "FileArchiveStore", lambda *a, **k: store)
    ok, reason = cpa._create_or_verify_pack(**_pack_kwargs(tmp_path, manifest))
    assert (ok, reason) == (True, "archive_verified")
    store.create.assert_not_called()


def test_create_or_verify_pack_create_failure(tmp_path, monkeypatch):
    manifest = RunManifest(pipeline_name="pipe")

    class FakePlanner:
        def __init__(self, **kwargs):
            pass

        def plan_for_manifest(self, *args, **kwargs):
            return SimpleNamespace(resolution_issues=[], artifacts=[object()])

    def _boom(**kwargs):
        raise OSError("disk gone")

    store = SimpleNamespace(
        verify=MagicMock(return_value=(None, "archive_evidence_not_recorded")),
        create=MagicMock(side_effect=_boom),
    )
    monkeypatch.setattr(cpa, "FileControlPlaneArtifactLifecycleStore", FakePlanner)
    monkeypatch.setattr(cpa, "FileArchiveStore", lambda *a, **k: store)
    ok, reason = cpa._create_or_verify_pack(**_pack_kwargs(tmp_path, manifest))
    assert (ok, reason) == (False, "archive_create_failed")


def test_create_or_verify_pack_create_then_verify(tmp_path, monkeypatch):
    manifest = RunManifest(pipeline_name="pipe")

    class FakePlanner:
        def __init__(self, **kwargs):
            pass

        def plan_for_manifest(self, *args, **kwargs):
            return SimpleNamespace(resolution_issues=[], artifacts=[object()])

    store = SimpleNamespace(
        verify=MagicMock(
            side_effect=[
                (None, "archive_evidence_not_recorded"),
                (True, "archive_verified"),
            ]
        ),
        create=MagicMock(),
    )
    monkeypatch.setattr(cpa, "FileControlPlaneArtifactLifecycleStore", FakePlanner)
    monkeypatch.setattr(cpa, "FileArchiveStore", lambda *a, **k: store)
    ok, reason = cpa._create_or_verify_pack(**_pack_kwargs(tmp_path, manifest))
    assert (ok, reason) == (True, "archive_verified")
    assert store.create.call_count == 1


# ---------------------------------------------------------------------------
# checkpoint_validation (missing: 23, 32, 74-82, 99, 127, 166, 188)
# ---------------------------------------------------------------------------

from bioetl.application.observability.control_plane_evidence.checkpoint_validation import (
    build_checkpoint_checks,
)


def _manifest_with_anchors():
    manifest = RunManifest(pipeline_name="pipe")
    metadata = {
        "manifest_id": manifest.manifest_id,
        "pipeline_name": manifest.pipeline_name,
        "run_type": manifest.run_type.value,
        "execution_fingerprint": manifest.execution_fingerprint,
    }
    return manifest, metadata


def test_checkpoint_aggregate_scope_unknown():
    (check,) = build_checkpoint_checks(
        manifest=None, checkpoint=None, aggregate_scope_unknown=True
    )
    assert check.check == "scope"
    assert check.status == "UNKNOWN"


def test_checkpoint_not_found():
    (check,) = build_checkpoint_checks(
        manifest=None, checkpoint=None, aggregate_scope_unknown=False
    )
    assert check.reason == "checkpoint_not_found"


def test_checkpoint_saved_at_string_and_invalid():
    manifest, metadata = _manifest_with_anchors()
    metadata["checkpoint_saved_at_epoch_seconds"] = "1700000000"
    checks = build_checkpoint_checks(
        manifest=manifest,
        checkpoint=("run", metadata),
        aggregate_scope_unknown=False,
    )
    schema = next(c for c in checks if c.check == "schema")
    assert schema.status == "OK"

    bad = dict(metadata, checkpoint_saved_at_epoch_seconds="not-a-time")
    checks = build_checkpoint_checks(
        manifest=manifest, checkpoint=("run", bad), aggregate_scope_unknown=False
    )
    schema = next(c for c in checks if c.check == "schema")
    assert schema.reason == "checkpoint_saved_at_invalid"

    weird = dict(metadata, checkpoint_saved_at_epoch_seconds=["x"])
    checks = build_checkpoint_checks(
        manifest=manifest,
        checkpoint=("run", weird),
        aggregate_scope_unknown=False,
    )
    schema = next(c for c in checks if c.check == "schema")
    assert schema.reason == "checkpoint_saved_at_invalid"

    infinite = dict(metadata, checkpoint_saved_at_epoch_seconds=float("inf"))
    checks = build_checkpoint_checks(
        manifest=manifest,
        checkpoint=("run", infinite),
        aggregate_scope_unknown=False,
    )
    schema = next(c for c in checks if c.check == "schema")
    assert schema.reason == "checkpoint_saved_at_invalid"


def test_checkpoint_checksum_verified():
    manifest, metadata = _manifest_with_anchors()
    metadata["checkpoint_checksum_valid"] = True
    checks = build_checkpoint_checks(
        manifest=manifest,
        checkpoint=("run", metadata),
        aggregate_scope_unknown=False,
    )
    checksum = next(c for c in checks if c.check == "checksum")
    assert checksum.reason == "checkpoint_checksum_verified"


def test_checkpoint_anchors_without_manifest():
    (parse, _schema, _checksum, anchors) = build_checkpoint_checks(
        manifest=None,
        checkpoint=("run", {"checkpoint_checksum_valid": True}),
        aggregate_scope_unknown=False,
    )
    assert anchors.reason == "manifest_unavailable_for_anchor_validation"


def test_checkpoint_anchor_incomplete_warns():
    manifest, _ = _manifest_with_anchors()
    checks = build_checkpoint_checks(
        manifest=manifest,
        checkpoint=(str(manifest.run_id), {}),
        aggregate_scope_unknown=False,
    )
    anchors = next(c for c in checks if c.check == "anchors")
    assert anchors.status == "WARNING"
    assert anchors.reason == "checkpoint_anchor_incomplete"


def test_checkpoint_anchor_run_context_fallback():
    manifest, _ = _manifest_with_anchors()
    metadata = {
        "run_context": {
            "manifest_id": manifest.manifest_id,
            "pipeline_name": manifest.pipeline_name,
            "run_type": manifest.run_type.value,
            "execution_fingerprint": manifest.execution_fingerprint,
        }
    }
    checks = build_checkpoint_checks(
        manifest=manifest,
        checkpoint=(str(manifest.run_id), metadata),
        aggregate_scope_unknown=False,
    )
    anchors = next(c for c in checks if c.check == "anchors")
    assert anchors.reason == "checkpoint_anchors_match_manifest"


# ---------------------------------------------------------------------------
# _filtered_data_source_support (missing: 50, 51, 74-80, 114, 121, 124, 126)
# ---------------------------------------------------------------------------

from bioetl.application.core import _filtered_data_source_support as fds


def _filtered_state(**overrides):
    state = SimpleNamespace(
        _data_source=AsyncMock(),
        _filter_reader=None,
        _filter_config=SimpleNamespace(
            enabled=False,
            direct_multi_filter_ids=None,
            direct_filter_ids=None,
            direct_valid_combinations=None,
            direct_fallback_mapping=None,
            source_path=None,
            column_name=None,
            fallback_column=None,
            filter_field="id",
            get_columns=lambda: (),
        ),
        _metrics=None,
        _pipeline_name="pipe",
        _logger=None,
        _filter_ids=None,
        _filter_result=None,
        _multi_filter_ids=None,
        _valid_combinations=None,
        _filter_fields=None,
        _fallback_mapping=None,
    )
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


async def test_enter_loads_direct_multi_filter_ids():
    state = _filtered_state()
    state._filter_config.enabled = True
    state._filter_config.direct_multi_filter_ids = {"f": ["a", "b"]}
    await fds.enter_filtered_data_source(state)
    assert state._multi_filter_ids == {"f": ["a", "b"]}
    assert state._filter_fields == ("f",)


def test_load_direct_multi_filter_ids_logs_counts():
    logger = MagicMock()
    state = _filtered_state(_logger=logger)
    state._filter_config.direct_multi_filter_ids = {"f1": ["a"], "f2": ["b", "c"]}
    state._filter_config.direct_valid_combinations = frozenset({("a", "b")})
    fds.load_direct_multi_filter_ids(state)
    assert state._multi_filter_ids == {"f1": ["a"], "f2": ["b", "c"]}
    assert state._filter_fields == ("f1", "f2")
    logger.info.assert_called_once()
    _, kwargs = logger.info.call_args
    assert kwargs["valid_combinations_count"] == 1


async def test_load_csv_filter_ids_without_source_path_returns():
    state = _filtered_state()
    state._filter_reader = AsyncMock()
    state._filter_config.source_path = None
    await fds.load_csv_filter_ids(state)
    assert state._filter_result is None


async def test_load_csv_single_column_entry_uses_multi_path():
    result = SimpleNamespace(
        column_ids={"f": ["1"]},
        valid_combinations=frozenset({("1",)}),
        filter_fields=("f",),
    )
    reader = AsyncMock()
    reader.load_multi_column_filter = AsyncMock(return_value=result)
    state = _filtered_state(_filter_reader=reader)
    state._filter_config.source_path = "filters.csv"
    state._filter_config.column_name = None
    state._filter_config.get_columns = lambda: (MagicMock(),)
    await fds.load_csv_filter_ids(state)
    assert state._multi_filter_ids == {"f": ["1"]}
    reader.load_multi_column_filter.assert_awaited_once()


async def test_load_csv_without_columns_raises():
    state = _filtered_state(_filter_reader=AsyncMock())
    state._filter_config.source_path = "filters.csv"
    state._filter_config.column_name = None
    state._filter_config.get_columns = lambda: ()
    with pytest.raises(ValueError, match="column_name"):
        await fds.load_csv_filter_ids(state)


# ---------------------------------------------------------------------------
# _structural_policy_evaluation (missing: 44, 98, 99, 100, 101, 102, 111, 112)
# ---------------------------------------------------------------------------

from bioetl.application.core.base_transformer._structural_policy_evaluation import (
    evaluate_contract,
    evaluate_null_value,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
)


def _int_spec(**overrides):
    base = {
        "field_name": "age",
        "logical_type": "integer",
        "physical_type": "int",
        "nullable": False,
        "optional": True,
        "optional_sources": (),
    }
    base.update(overrides)
    return StructuralFieldSpec(**base)


def test_evaluate_contract_null_optional_nonnullable_quarantines():
    events: list = []
    outcome = evaluate_contract(_int_spec(), {"age": None}, events)
    assert outcome is not None
    assert outcome.should_quarantine
    assert events


def test_evaluate_contract_null_nullable_passes():
    events: list = []
    outcome = evaluate_contract(_int_spec(nullable=True), {"age": None}, events)
    assert outcome is None
    assert events == []


def test_evaluate_null_value_required_without_nullable_passes():
    events: list = []
    outcome = evaluate_null_value(
        contract=_int_spec(optional=False),
        working_record={"age": None},
        events=events,
    )
    assert outcome is None
    assert events == []


# ---------------------------------------------------------------------------
# batch_memory_decision_policy (missing: 18, 57-63)
# ---------------------------------------------------------------------------

from bioetl.application.core import batch_memory_decision_policy as mempolicy


def test_config_budget_exceeded_without_config():
    assert mempolicy.config_budget_exceeded(None, 10**9) is False


def test_decision_status_branches():
    assert (
        mempolicy.decision_status(old_size=10, new_size=5, pressure_state=None)
        == "reduced"
    )
    assert (
        mempolicy.decision_status(old_size=5, new_size=10, pressure_state=None)
        == "recovered"
    )
    assert (
        mempolicy.decision_status(old_size=5, new_size=5, pressure_state=True)
        == "pressure"
    )
    assert (
        mempolicy.decision_status(old_size=5, new_size=5, pressure_state=False)
        == "stable"
    )
    assert (
        mempolicy.decision_status(old_size=5, new_size=5, pressure_state=None)
        == "disabled"
    )


# ---------------------------------------------------------------------------
# publication_term_extraction_mixin (missing: 93-97, 164, 179, 197)
# ---------------------------------------------------------------------------

from bioetl.application.core.publication_term_extraction_mixin import (
    PublicationTermExtractionMixin,
)


class _TermHost(PublicationTermExtractionMixin):
    SOURCE_ENTITY_TYPE = "publication"
    PUBLICATION_LIMIT_MULTIPLIER = 3
    _data_source = AsyncMock()

    def _extract_terms_from_publication(self, record, publication_id):
        return [{"term": "t", "publication_id": publication_id}]


async def test_yield_terms_limit_zero_closes_stream():
    host = _TermHost()

    async def _pubs():
        yield {"publication_id": "P1"}

    agen = _pubs()
    seen = [t async for t in host._yield_terms_from_publications(agen, 0)]
    assert seen == []


async def test_yield_terms_limit_zero_without_aclose():
    host = _TermHost()

    class _NoCloseStream:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    seen = [t async for t in host._yield_terms_from_publications(_NoCloseStream(), 0)]
    assert seen == []


def test_create_term_record_builds_record():
    host = _TermHost()
    record = host._create_term_record(
        publication_id="P1",
        term="kinase",
        term_type="mesh",
        mesh_id="D0001",
        qualifier=None,
    )
    assert record["publication_id"] == "P1"
    assert record["term"] == "kinase"


def test_compute_entity_id_is_deterministic():
    host = _TermHost()
    first = host._compute_entity_id("P1", "mesh", "kinase")
    second = host._compute_entity_id("P1", "mesh", "kinase")
    assert first == second and isinstance(first, str)


async def test_fetch_filtered_terms_limit_zero_yields_nothing():
    host = _TermHost()
    seen = [
        t
        async for t in host._fetch_filtered_publication_terms(
            MagicMock(), ["P1"], "publication_id", 0
        )
    ]
    assert seen == []


# ---------------------------------------------------------------------------
# control_plane_evidence.service (missing: 82, 85, 88, 166, 172, 216, 222, 275)
# ---------------------------------------------------------------------------

from bioetl.application.observability.control_plane_evidence.service import (
    ControlPlaneEvidenceService,
)
from bioetl.application.observability.control_plane_evidence.service_support import (
    EvidenceScopeContext,
)


def _scope(manifest=None, resolved_via="pipeline_scope"):
    return EvidenceScopeContext(
        requested_pipeline="pipe",
        selected_run_id=None,
        selected_run_types=("incremental",),
        resolved_via=resolved_via,
        manifest=manifest,
    )


def test_trust_summary_handles_missing_and_foreign_rows():
    svc = ControlPlaneEvidenceService()
    good_row = {
        "check": "parse",
        "status": "OK",
        "reason": "ok",
        "detail": "fine",
    }
    with (
        patch.object(
            ControlPlaneEvidenceService,
            "manifest_validation",
            return_value={"endpoint": "manifest-validation", "rows": []},
        ),
        patch.object(
            ControlPlaneEvidenceService,
            "lineage_validation",
            return_value={
                "endpoint": "lineage-validation",
                "rows": ["not-a-dict", good_row],
            },
        ),
        patch.object(
            ControlPlaneEvidenceService,
            "retention_compliance",
            return_value={
                "endpoint": "retention-compliance",
                "rows": [good_row],
            },
        ),
    ):
        payload = svc.trust_summary(scope=_scope(), now=MagicMock())
    reasons = [row["reason"] for row in payload["rows"]]
    assert "evidence_missing" in reasons
    assert "ok" in reasons


def test_lineage_validation_without_manifest():
    svc = ControlPlaneEvidenceService()
    payload = svc.lineage_validation(scope=_scope(manifest=None))
    assert payload["endpoint"] == "lineage-validation"


def test_lineage_validation_without_store():
    svc = ControlPlaneEvidenceService()
    payload = svc.lineage_validation(scope=_scope(manifest=RunManifest()))
    assert payload["rows"][0]["reason"] == "lineage_store_unavailable"


def test_retention_compliance_without_manifest():
    svc = ControlPlaneEvidenceService()
    payload = svc.retention_compliance(scope=_scope(manifest=None), now=MagicMock())
    assert payload["endpoint"] == "retention-compliance"


def test_retention_compliance_without_planner():
    svc = ControlPlaneEvidenceService()
    payload = svc.retention_compliance(
        scope=_scope(manifest=RunManifest()), now=MagicMock()
    )
    assert payload["rows"][0]["reason"] == "lifecycle_planner_unavailable"


def test_bounded_retention_plan_legacy_planner_fallback():
    sentinel = object()
    planner = SimpleNamespace(plan=lambda *args, **kwargs: sentinel)
    svc = ControlPlaneEvidenceService(lifecycle_planner=planner)
    assert svc._bounded_retention_plan(RunManifest(), MagicMock()) is sentinel


# ---------------------------------------------------------------------------
# _runner_support (missing: 108, 119, 126, 131, 136, 153, 154)
# ---------------------------------------------------------------------------

from bioetl.application.core import _runner_support as rsupport
from bioetl.application.core._runner_support import PipelineRunnerSupportMixin


async def test_runner_support_delegates_execution_cycle():
    with patch.object(rsupport, "run_execution_cycle", new=AsyncMock()) as cycle:
        await PipelineRunnerSupportMixin()._run_execution_cycle()
    cycle.assert_awaited_once()


def test_runner_support_extract_checkpoint_offset():
    with patch.object(rsupport, "extract_checkpoint_offset", return_value=7) as extract:
        assert PipelineRunnerSupportMixin()._extract_checkpoint_offset({"x": 1}) == 7
    extract.assert_called_once()


async def test_runner_support_delegates_pipeline_and_postrun():
    with (
        patch.object(rsupport, "execute_pipeline", new=AsyncMock()) as exe,
        patch.object(rsupport, "run_postrun_phase", new=AsyncMock()) as post,
        patch.object(rsupport, "validate_infrastructure", new=AsyncMock()) as valid,
    ):
        host = PipelineRunnerSupportMixin()
        await host._execute_pipeline(offset=3)
        await host._run_postrun_phase()
        await host._validate_infrastructure()
    exe.assert_awaited_once()
    post.assert_awaited_once()
    valid.assert_awaited_once()


def test_runner_support_close_metrics_failure_warns():
    host = PipelineRunnerSupportMixin()
    metrics = MagicMock()
    metrics.close.side_effect = OSError("closed?")
    host._services = SimpleNamespace(metrics=metrics)
    host._logger = MagicMock()
    host._close_metrics()
    host._logger.warning.assert_called_once()
    _, kwargs = host._logger.warning.call_args
    assert kwargs["reason"] == "metrics_close_failed"


# ---------------------------------------------------------------------------
# batch_executor_state_flow (missing: 150, 151, 155, 164, 172, 173, 177)
# ---------------------------------------------------------------------------

from bioetl.application.core import batch_executor_state_flow as stateflow
from bioetl.application.core.lifecycle.batch_fsm import (
    BatchExecutionCommand,
    BatchExecutionEvent,
    BatchExecutionState,
)


def _flow_host(**overrides):
    host = SimpleNamespace(
        _resume_offset=0,
        _query_string=None,
        _fsm=MagicMock(),
        _fsm_state=BatchExecutionState.STREAMING,
        _execution_run_service=MagicMock(),
        _processing_port=AsyncMock(),
        _execution_state_service=MagicMock(),
        _memory=MagicMock(),
        _batch_result_type=MagicMock(),
    )
    for key, value in overrides.items():
        setattr(host, key, value)
    return host


async def test_process_stateful_batch_process_failure_transitions():
    host = _flow_host()
    host._processing_port.process_batch = AsyncMock(side_effect=ValueError("bad"))
    host._fsm.advance.side_effect = [
        SimpleNamespace(
            new_state=BatchExecutionState.STREAMING,
            commands=(BatchExecutionCommand.PROCESS_BATCH,),
        ),
        SimpleNamespace(new_state=BatchExecutionState.FAILED, commands=()),
    ]
    with pytest.raises(ValueError, match="bad"):
        await stateflow.process_stateful_batch(host, [{"a": 1}], 0)
    failure_events = [call.args[1] for call in host._fsm.advance.call_args_list]
    assert BatchExecutionEvent.PROCESS_FAILED in failure_events


async def test_process_stateful_batch_skips_commit_when_not_commanded():
    host = _flow_host()
    host._processing_port.process_batch = AsyncMock(return_value=SimpleNamespace())
    host._fsm.advance.side_effect = [
        SimpleNamespace(
            new_state=BatchExecutionState.STREAMING,
            commands=(BatchExecutionCommand.PROCESS_BATCH,),
        ),
        SimpleNamespace(new_state=BatchExecutionState.STREAMING, commands=()),
    ]
    await stateflow.process_stateful_batch(host, [{"a": 1}], 0)
    host._execution_state_service.commit_successful_batch.assert_not_called()


async def test_process_stateful_batch_commit_failure_transitions():
    host = _flow_host()
    host._processing_port.process_batch = AsyncMock(return_value=SimpleNamespace())
    host._execution_state_service.commit_successful_batch.side_effect = ValueError(
        "commit?"
    )
    host._fsm.advance.side_effect = [
        SimpleNamespace(
            new_state=BatchExecutionState.STREAMING,
            commands=(BatchExecutionCommand.PROCESS_BATCH,),
        ),
        SimpleNamespace(
            new_state=BatchExecutionState.STREAMING,
            commands=(BatchExecutionCommand.COMMIT_STATE,),
        ),
        SimpleNamespace(new_state=BatchExecutionState.FAILED, commands=()),
    ]
    with pytest.raises(ValueError, match="commit"):
        await stateflow.process_stateful_batch(host, [{"a": 1}], 0)
    failure_events = [call.args[1] for call in host._fsm.advance.call_args_list]
    assert BatchExecutionEvent.STATE_COMMIT_FAILED in failure_events


# ---------------------------------------------------------------------------
# control_plane_evidence.models (missing: 103, 106, 107, 119, 120, 121, 154)
# ---------------------------------------------------------------------------

import datetime
from uuid import UUID

from bioetl.application.observability.control_plane_evidence import models as evmodels
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.types import RunID


def _ledger_entry(event_type):
    return RunLedgerEntry(
        entry_id="e1",
        manifest_id="legacy-manifest",
        run_id=RunID(UUID(int=1)),
        event_type=event_type,
        occurred_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
    )


def test_processing_status_from_ledger_tail():
    manifest = RunManifest()
    assert (
        evmodels._processing_status(manifest, (_ledger_entry("run_finished"),))
        == "success"
    )
    assert (
        evmodels._processing_status(manifest, (_ledger_entry("run_failed"),))
        == "failed"
    )
    assert (
        evmodels._processing_status(manifest, (_ledger_entry("run_shutdown"),))
        == "shutdown"
    )


def test_processing_status_skips_unmatched_ledger_head():
    manifest = RunManifest()
    entries = (
        _ledger_entry("run_finished"),
        _ledger_entry("some_other_event"),
    )
    assert evmodels._processing_status(manifest, entries) == "success"


def test_scope_kind_branches():
    manifest = RunManifest()
    assert (
        evmodels._scope_kind(
            resolved_via="selected_run_id_not_found", manifest=manifest
        )
        == "unresolved"
    )
    assert (
        evmodels._scope_kind(resolved_via="latest_run", manifest=manifest)
        == "pipeline_current"
    )
    assert (
        evmodels._scope_kind(resolved_via="exact_run", manifest=manifest) == "exact_run"
    )


def test_evidence_payload_empty_checks_is_unknown():
    payload = evmodels.evidence_payload(
        endpoint="trust-summary",
        checks=(),
        requested_pipeline="pipe",
        selected_run_id=None,
        selected_run_types=("incremental",),
        resolved_via="pipeline_scope",
        manifest=None,
    )
    assert payload["status"] == "UNKNOWN"
