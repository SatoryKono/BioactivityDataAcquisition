"""Stream B APP: leftover checkpoint, reconcile, preflight, DQ, and markdown branches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite._preflight_orchestration import (
    PreflightSchemaOrchestrationMixin,
)
from bioetl.application.core.base_transformer._structural_policy_evaluation import (
    evaluate_null_value,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
)
from bioetl.application.observability.control_plane_evidence.retention import (
    _manifest_snapshot_ids,
)
from bioetl.application.services.checkpoint._checkpoint_service_runtime import (
    get_checkpoint_for_manifest_id_impl,
    get_checkpoint_for_run_impl,
)
from bioetl.application.services.checkpoint.checkpoint_service import CheckpointService
from bioetl.application.services.ops.error_handler import ErrorHandlerService
from bioetl.application.services.quality import config_dq_service as dq_cfg
from bioetl.application.services.run_reports import markdown as md
from bioetl.application.workflow.transforms import reconcile_foreign_keys as rec

pytestmark = pytest.mark.unit


class _PreflightHost(PreflightSchemaOrchestrationMixin):
    _logger = MagicMock()


def test_preflight_identity_empty_entity_and_alias_skip() -> None:
    host = _PreflightHost()
    assert host._parse_pipeline_identity("chembl_") is None
    assert host._parse_pipeline_identity("nounderscore") is None
    result: dict[str, str] = {}
    host._register_source_aliases(
        result, pipeline_name="nounderscore", fields="payload"
    )
    assert result == {}
    assert host._load_pipeline_profile("nounderscore") is None


def test_config_dq_parse_rejects_and_hash_strategy() -> None:
    with pytest.raises(ValueError, match="disposition"):
        dq_cfg._parse_disposition(1)
    assert dq_cfg._is_source_hash_strategy("canonical_yaml") is True
    assert dq_cfg._parse_source_hash_strategy(None) is None
    assert dq_cfg._parse_source_hash_strategy("raw_bytes") == "raw_bytes"
    with pytest.raises(ValueError, match="hash strategy"):
        dq_cfg._parse_source_hash_strategy("nope")
    with pytest.raises(ValueError, match="strictness"):
        dq_cfg._parse_strictness_mode("nope")
    with pytest.raises(ValueError, match="snapshot"):
        dq_cfg._parse_snapshot_strictness_mode("nope")


def test_error_handler_increment_counter_and_legacy_noop() -> None:
    metrics = SimpleNamespace(increment_counter=MagicMock())
    handler = ErrorHandlerService(logger=MagicMock(), metrics=metrics)  # type: ignore[arg-type]
    handler._increment_counter("n", 1, {"k": "v"})
    metrics.increment_counter.assert_called_once()

    noop = ErrorHandlerService(logger=MagicMock(), metrics=SimpleNamespace())  # type: ignore[arg-type]
    noop._increment_counter("n", 1, None)


def test_structural_optional_nonnullable_null() -> None:
    contract = StructuralFieldSpec(
        field_name="activity_id",
        logical_type="integer",
        physical_type="int",
        nullable=False,
        optional=True,
        optional_sources=(),
    )
    events: list[object] = []
    outcome = evaluate_null_value(
        contract=contract,
        working_record={"activity_id": None},
        events=events,  # type: ignore[arg-type]
    )
    assert outcome is not None
    assert outcome.should_quarantine is True


def test_markdown_skip_reason_and_samples() -> None:
    lines: list[str] = []
    row = SimpleNamespace(
        step_id="s1",
        pipeline_name="chembl_activity",
        status="skipped",
        records_extracted=0,
        records_silver=None,
        records_gold=None,
        pipeline_report_ref=None,
        top_reasons=[],
        skip_reason="no-input",
    )
    md._append_workflow_steps(lines, SimpleNamespace(execution=[row]))  # type: ignore[arg-type]
    assert any("skip_reason" in line for line in lines)

    funnel_row = SimpleNamespace(
        stage_id="gold",
        removals=[SimpleNamespace(reason_code="dup", sample_refs=["a", "b"])],
    )
    sample_lines: list[str] = []
    md._append_samples_section(
        sample_lines,
        SimpleNamespace(funnel=[funnel_row]),  # type: ignore[arg-type]
    )
    assert any("Top samples" in line for line in sample_lines)


def test_retention_snapshot_ids_and_reconcile_completeness() -> None:
    manifest = SimpleNamespace(
        source_refs=[
            SimpleNamespace(input_snapshots=[SimpleNamespace(snapshot_id="snap-1")])
        ]
    )
    assert _manifest_snapshot_ids(manifest) == {"snap-1"}  # type: ignore[arg-type]
    status, identity, _ver, _ref = rec._resolve_reference_completeness(
        {}, {}, reference_table="activity"
    )
    assert status == "unproven"
    assert identity is None
    complete, ident, _v, eref = rec._resolve_reference_completeness(
        {
            "reference_completeness_evidence": {
                "status": "complete",
                "reference_identity": "activity",
                "evidence_ref": "ev-1",
            }
        },
        {},
        reference_table="activity",
    )
    assert complete == "complete"
    assert ident == "activity"
    assert eref == "ev-1"
    evidence = rec._upstream_completeness_evidence(
        {
            "step": {
                "reference_completeness_evidence": {"reference_identity": "activity"}
            }
        },
        "activity",
    )
    assert evidence is not None
    assert rec._upstream_completeness_evidence({"step": "plain"}, "activity") is None


@pytest.mark.asyncio
async def test_reconcile_persist_artifact_writer_paths() -> None:
    spec = SimpleNamespace(step_id="s1", transform_name="reconcile_foreign_keys")
    missing_writer = SimpleNamespace(
        logger=MagicMock(),
        artifact_sink=object(),
        workflow_name="wf",
        workflow_run_id="r1",
        manifest_id="m1",
        debug_export_enabled=False,
        debug_export_dir=None,
        created_at=None,
    )
    assert (
        await rec._persist_reconcile_result_artifact(
            missing_writer,  # type: ignore[arg-type]
            spec=spec,  # type: ignore[arg-type]
            payload={},
        )
        == ()
    )

    refs = ({"artifact_id": "a1"},)

    def _write(**_k: object) -> tuple[dict[str, object], ...]:
        return refs

    writer_ctx = SimpleNamespace(
        logger=MagicMock(),
        artifact_sink=SimpleNamespace(write_reconcile_result_artifact=_write),
        workflow_name="wf",
        workflow_run_id="r1",
        manifest_id="m1",
        debug_export_enabled=False,
        debug_export_dir=None,
        created_at=None,
    )
    persisted = await rec._persist_reconcile_result_artifact(
        writer_ctx,  # type: ignore[arg-type]
        spec=spec,  # type: ignore[arg-type]
        payload={"ok": True},
    )
    assert persisted


@pytest.mark.asyncio
async def test_checkpoint_service_tracerless_and_runtime_gaps() -> None:
    svc = CheckpointService(
        checkpoint_port=AsyncMock(),
        logger=MagicMock(),
        metrics=None,
        tracer=None,
    )
    svc.checkpoint_port.list_all = AsyncMock(return_value=["chembl_activity"])
    svc.checkpoint_port.load = AsyncMock(return_value=None)
    listed = await svc.list_checkpoints()
    assert listed[0].pipeline_name == "chembl_activity"
    svc._record_operator_metrics(operation="list", status="ok", duration_seconds=0.01)

    svc.checkpoint_port.load_for_run = AsyncMock(return_value=None)
    run_id = "12345678-1234-5678-1234-567812345678"
    missing_run = await svc.get_checkpoint_for_run("chembl_activity", run_id)
    assert missing_run is None

    host = SimpleNamespace(
        logger=MagicMock(),
        checkpoint_port=SimpleNamespace(
            load_for_run=AsyncMock(side_effect=ValueError("bad")),
            load_for_manifest_id=AsyncMock(return_value=None),
        ),
        _record_operator_metrics=MagicMock(),
        _checkpoint_info_from_data=lambda **_k: None,
    )
    with pytest.raises(ValueError, match="bad"):
        await get_checkpoint_for_run_impl(
            host,  # type: ignore[arg-type]
            pipeline_name="chembl_activity",
            run_id="not-a-uuid",
            start_time=0.0,
        )
    assert (
        await get_checkpoint_for_manifest_id_impl(
            host,  # type: ignore[arg-type]
            pipeline_name="chembl_activity",
            manifest_id="m1",
            start_time=0.0,
        )
        is None
    )
    host._record_operator_metrics.assert_called()
