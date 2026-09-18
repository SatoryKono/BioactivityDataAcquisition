"""Stream B APP: leftover redact, preview, chained-key, span, and posix-path branches."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import polars as pl
import pytest

from bioetl.application.composite.helpers.dependency_chained_key_resolver import (
    ChainedKeyResolver,
)
from bioetl.application.composite.helpers.resolver_helper import ResolverHelper
from bioetl.application.core._record_processor_span_support import RecordProcessorSpanExecutor
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.application.services.export_lineage.export_execution import (
    _should_redact_columns,
)
from bioetl.application.services.export_lineage.export_models import ExportOptions
from bioetl.application.observability.current_metrics_reconciliation import (
    _exposition_has_labeled_pipeline_runs_sample,
)
from bioetl.application.services.control_plane.forensic.diagnostics_support import (
    coerce_int,
    inspection_service_factory_from_ports,
)
from bioetl.application.services.control_plane.manifest._inspection_support import (
    RunManifestInspectionDiffClassificationMixin,
)
from bioetl.application.services.control_plane.manifest.diagnostics import replay_state as replay
from bioetl.application.services.control_plane.replay.historical_closure_policy import (
    _suggested_disposition,
    resolve_closure_verdict,
)
from bioetl.application.services.control_plane.replay.historical_corpus_policy import (
    certification_scope_for_context,
)
from bioetl.application.services.execution._pipeline_runner_support import (
    build_pipeline_run_result,
    finalize_pipeline_run_report,
)
from bioetl.application.services.execution.pipeline_run_execution_service import (
    PipelineExecutionResult,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.export_lineage.debug_export_service import (
    DebugExportConfig,
    DebugExportService,
)
from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageInspectionService,
)
from bioetl.application.services.export_lineage.export_service import ExportService
from bioetl.application.services.run_reports.source_identity import (
    _local_posix_runtime_path,
)
from bioetl.application.workflow.transforms import reconcile_foreign_keys as rec
from bioetl.application.workflow.transforms.reconcile_foreign_keys import (
    _upstream_completeness_evidence,
    build_reconcile_foreign_keys_executor,
)
from bioetl.domain.workflow.transform_spec import WorkflowTransformSpec
from bioetl.domain.composite import DependencyConfig
from bioetl.domain.types import BatchID, DebugExportResult, RunID

pytestmark = pytest.mark.unit


def test_redact_empty_sensitive_and_metrics_noop() -> None:
    assert _should_redact_columns((), options=ExportOptions()) is False
    recorder = PipelineMetricsRecorder(pipeline="chembl_activity", metrics=None)
    recorder.record_output_artifact_publication(stage="gold", status="ok", count=0)


@pytest.mark.asyncio
async def test_export_preview_table_without_pylist() -> None:
    class _Field:
        name = "id"
        type = "int64"
        nullable = False

    class _Schema:
        def __iter__(self) -> object:
            return iter((_Field(),))

    reader = AsyncMock()
    catalog = MagicMock()
    catalog.resolve_table_path.return_value = "silver/activity"
    reader.get_schema.return_value = _Schema()
    reader.get_row_count.return_value = 0
    reader.read_table.return_value = object()
    service = ExportService(
        reader=reader,
        catalog=catalog,
        writer=MagicMock(),
        logger=MagicMock(),
        silver_path=Path("silver"),
        gold_path=Path("gold"),
    )
    with pytest.raises(TypeError, match="preview support"):
        await service.preview("activity")


@pytest.mark.asyncio
async def test_chained_key_resolver_reraises_value_error() -> None:
    reader = AsyncMock()
    reader.read_table.side_effect = ValueError("bad table")
    resolver = ChainedKeyResolver(ResolverHelper(logger=MagicMock()))
    dependency = DependencyConfig(
        pipeline="chembl_assay",
        join_keys=("assay_id",),
        silver_table="silver/chembl/assay",
        key_source="chembl_activity",
    )
    source = DependencyConfig(
        pipeline="chembl_activity",
        join_keys=("activity_id",),
        silver_table="silver/chembl/activity",
    )
    with pytest.raises(ValueError, match="bad table"):
        await resolver.resolve(
            dependency,
            pl.DataFrame({"assay_id": [1]}),
            {"chembl_activity": source},
            reader,
        )


@pytest.mark.asyncio
async def test_transform_span_operation_and_base_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = RecordProcessorSpanExecutor(tracer=None)  # type: ignore[arg-type]

    async def _value_error(**_k: object) -> object:
        raise ValueError("transform-fail")

    monkeypatch.setattr(executor, "_transform_records", _value_error)
    with pytest.raises(ValueError, match="transform-fail"):
        await executor.execute_transform_with_span(
            transformer=MagicMock(),
            records=[],
            batch_id=BatchID(uuid4()),
            start_index=0,
        )

    class _BaseBoom(BaseException):
        pass

    async def _base(**_k: object) -> object:
        raise _BaseBoom()

    monkeypatch.setattr(executor, "_transform_records", _base)
    with pytest.raises(_BaseBoom):
        await executor.execute_transform_with_span(
            transformer=MagicMock(),
            records=[],
            batch_id=BatchID(uuid4()),
            start_index=0,
        )


def test_posix_runtime_path_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bioetl.application.services.run_reports.source_identity.os.name",
        "posix",
    )
    monkeypatch.setattr(
        "bioetl.application.services.run_reports.source_identity._mapped_runtime_path",
        lambda value: "/mnt/c/data" if value.startswith("C:") else None,
    )
    assert _local_posix_runtime_path("C:/data") == Path("/mnt/c/data")
    assert _local_posix_runtime_path("/tmp/nope") is None


def test_metrics_replay_forensic_and_inspection_leftovers() -> None:
    assert (
        _exposition_has_labeled_pipeline_runs_sample(
            'bioetl_pipeline_runs_total{pipeline="other",run_type="full"} 1\n',
            pipeline="chembl_activity",
            run_type="full",
        )
        is False
    )
    assert certification_scope_for_context("") is None
    assert (
        _suggested_disposition(SimpleNamespace(certification_status="unknown"))  # type: ignore[arg-type]
        == "manual_review_required"
    )
    assert coerce_int(None) == 0
    assert inspection_service_factory_from_ports(MagicMock(), None, None) is not None
    assert (
        RunManifestInspectionDiffClassificationMixin._resolve_replay_relationship(
            left_manifest=SimpleNamespace(  # type: ignore[arg-type]
                replay_of_manifest_id="right",
                replay_of_run_id=None,
                manifest_id="left",
                run_id="1",
            ),
            right_manifest=SimpleNamespace(  # type: ignore[arg-type]
                replay_of_manifest_id=None,
                replay_of_run_id=None,
                manifest_id="right",
                run_id="2",
            ),
        )
        == "left_is_exact_replay_of_right"
    )
    assert (
        RunManifestInspectionDiffClassificationMixin._resolve_replay_relationship(
            left_manifest=SimpleNamespace(  # type: ignore[arg-type]
                replay_of_manifest_id="other",
                replay_of_run_id=None,
                manifest_id="left",
                run_id="1",
            ),
            right_manifest=SimpleNamespace(  # type: ignore[arg-type]
                replay_of_manifest_id=None,
                replay_of_run_id=None,
                manifest_id="right",
                run_id="2",
            ),
        )
        == "external_replay_parentage_present"
    )
    inventory = SimpleNamespace(
        manifest_count=2,
        certified_count=0,
        replayable_count=0,
        unsupported_count=1,
        remaining_uncertified_count=2,
    )
    verdict, _reason = resolve_closure_verdict(
        inventory=inventory,  # type: ignore[arg-type]
        unresolved_records=(),
        disposition_map={},
        claim_scope_mode="all_retained_historical_runs",
    )
    assert verdict == "outside_supported_scope_present"
    evidence = _upstream_completeness_evidence(
        {"step": {"reference_completeness_evidence": "nope"}},
        "silver/chembl/activity",
    )
    assert evidence is None


def test_composite_replay_capability_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(replay, "_collect_append_mode_semantic_sinks", lambda _m: ())
    monkeypatch.setattr(replay, "_has_partial_input_snapshot_envelope", lambda _e: False)
    monkeypatch.setattr(
        replay, "_has_historical_composite_certified_snapshots", lambda _s: False
    )
    monkeypatch.setattr(
        replay, "_has_historical_source_certified_snapshots", lambda _s: False
    )
    monkeypatch.setattr(replay, "_resolve_exact_replay_supported_reason", lambda **_k: None)
    monkeypatch.setattr(replay, "_requires_resume_without_snapshot_reason", lambda **_k: False)
    monkeypatch.setattr(replay, "_is_composite_execution_context", lambda _m: True)
    reason = replay._resolve_replay_capability_reason(
        manifest=SimpleNamespace(),  # type: ignore[arg-type]
        input_snapshots=[],
        resume_requested=False,
        policy_assessment=SimpleNamespace(snapshot_envelope={}),
        replay_family_context=SimpleNamespace(
            profile=SimpleNamespace(strict_exact_replay_supported=True)
        ),
    )
    assert reason == "composite_snapshot_envelope_missing"


@pytest.mark.asyncio
async def test_debug_export_result_object() -> None:
    expected = DebugExportResult(
        root_path="artifacts/debug",
        manifest_path="artifacts/debug/manifest.json",
        debug_export_hash="abc",
    )
    service = DebugExportService(
        config=DebugExportConfig(enabled=True),
        run_id=RunID(uuid4()),
        pipeline_id="chembl_activity",
        provider_id="chembl",
        writer=SimpleNamespace(write_pack=lambda **_k: expected),
    )
    assert await service.persist() == expected


@pytest.mark.asyncio
async def test_reconcile_executor_attaches_artifact_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rec, "_build_request", lambda *_a, **_k: SimpleNamespace())
    monkeypatch.setattr(rec, "_build_reconcile_payload", lambda **_k: {"ok": True})

    async def _persist(*_a: object, **_k: object) -> tuple[dict[str, object], ...]:
        return ({"id": "art-1"},)

    monkeypatch.setattr(rec, "_persist_reconcile_result_artifact", _persist)
    port = SimpleNamespace(
        reconcile_foreign_keys=AsyncMock(
            return_value=SimpleNamespace(mutated=False, dry_run=True)
        )
    )
    payload = await build_reconcile_foreign_keys_executor(port)(  # type: ignore[arg-type]
        WorkflowTransformSpec(step_id="s1", transform_name="reconcile_foreign_keys"),
        {},
    )
    assert payload["artifact_refs"] == [{"id": "art-1"}]


def test_lineage_manifest_parse_none(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MagicMock()
    store.list_by_manifest_id.return_value = ()
    store.list_by_run_id.return_value = ()
    port = MagicMock()
    port.get.return_value = SimpleNamespace(manifest_id="m1", run_id="run-1")
    inspector = LineageInspectionService(lineage_store=store, manifest_port=port)
    monkeypatch.setattr(LineageInspectionService, "_parse_run_id", lambda self, ident: None)
    assert inspector._resolve_via_manifest("m1") is None


def test_pipeline_run_report_error_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name="chembl_activity",
        run_id="run-1",
        run_type="full",
    )
    monkeypatch.setattr(
        "bioetl.application.services.execution._pipeline_runner_support.write_pipeline_run_report",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("report-fail")),
    )
    failed = finalize_pipeline_run_report(result=result, store=MagicMock())
    assert failed.run_report_error is not None
    assert "report-fail" in failed.run_report_error
    outcome = PipelineExecutionResult(
        status="success",
        completed_at=result.completed_at,
        metrics={},
    )
    built = build_pipeline_run_result(
        outcome=outcome,
        runner=SimpleNamespace(),
        pipeline_name="chembl_activity",
        run_id=RunID(uuid4()),
        run_type="full",
        started_at=result.started_at,
        write_report=True,
        store=MagicMock(),
    )
    assert built.run_report_error is not None
