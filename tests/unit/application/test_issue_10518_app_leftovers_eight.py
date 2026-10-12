"""Stream B APP: leftover export, certification, TPC, and mixin branches."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.composite.column_service_support import _collect_alias_matches
from bioetl.application.composite.coordinator_result_mixin import (
    EnrichmentCoordinatorResultMixin,
)
from bioetl.application.composite.helpers.join_planner_identity import (
    infer_silver_table,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_mixin import (
    CompositeRunnerMergeStageMixin,
)
from bioetl.application.composite.runner_pkg.runner_stage_support_mixin import (
    _CompositeRunnerStageSupportMixin,
)
from bioetl.application.core._batch_write_support import emit_batch_failed
from bioetl.application.core.base_transformer._structural_policy_events import (
    build_structural_details,
    preview_value,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
)
from bioetl.application.core.base_transformer.errors import FilteredOutError
from bioetl.application.core.batch_executor_runtime_state import (
    BatchExecutorRuntimeState,
    BatchExecutorRuntimeStateMixin,
)
from bioetl.application.core.batch_transformer_attempt_failures import (
    handle_data_quality_transform_error,
    handle_filtered_out_error,
)
from bioetl.application.observability import (
    current_metrics_reconciliation as metrics_rec,
)
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.protein_class_transformer import (
    ProteinClassTransformer,
)
from bioetl.application.pipelines.chembl.target_protein_classification_summary import (
    _int_or_none,
    _multifunctional_origin,
    _representative_row_for_primary_top_level,
)
from bioetl.application.pipelines.chembl.target_protein_classification_transformer import (
    TargetProteinClassificationTransformer,
)
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.application.pipelines.uniprot.extractors._crossref_structured import (
    build_interpro_entry,
    build_pfam_entry,
    build_reactome_entry,
)
from bioetl.application.services.control_plane.replay._historical_certification_support import (
    HistoricalReplayCertificationValidator,
)
from bioetl.application.services.control_plane.manifest import (
    snapshot_payloads as _snapshot_payloads,
)
from bioetl.application.services.export_lineage.export_execution import (
    _should_redact_columns,
    export_existing_table,
)
from bioetl.application.services.export_lineage.export_models import ExportOptions
from bioetl.application.services.export_lineage.export_service import ExportService
from bioetl.domain.types import BatchID, ErrorType

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_export_preview_missing_table_and_bad_payload() -> None:
    reader = AsyncMock()
    catalog = MagicMock()
    catalog.resolve_table_path.return_value = "silver/activity"
    reader.get_schema.return_value = object()
    reader.table_exists.return_value = False
    service = ExportService(
        reader=reader,
        catalog=catalog,
        writer=MagicMock(),
        logger=MagicMock(),
        silver_path=Path("silver"),
        gold_path=Path("gold"),
    )
    with pytest.raises(TypeError, match="preview schema"):
        await service.preview("activity")
    missing = await service.export("activity", options=None)
    assert missing
    reader.read_table.return_value = object()
    with pytest.raises(TypeError, match="export capabilities"):
        await export_existing_table(
            reader=reader,
            writer=MagicMock(),
            logger=MagicMock(),
            export_path=Path("exports"),
            table_name="activity",
            layer="silver",
            options=ExportOptions(),
            table_path="silver/activity",
        )


def test_historical_certification_missing_and_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = HistoricalReplayCertificationValidator(
        manifest_port=MagicMock(),
        ledger_port=MagicMock(),
        summary_builder=lambda *_a, **_k: {},
    )
    with pytest.raises(ValueError, match="composite context"):
        validator.validate_composite_context(
            SimpleNamespace(launch_context={}, provider="chembl")  # type: ignore[arg-type]
        )
    monkeypatch.setattr(
        HistoricalReplayCertificationValidator,
        "_build_expected_source_keys",
        lambda self, manifest: {("chembl", "activity", "p")},
    )
    monkeypatch.setattr(
        HistoricalReplayCertificationValidator,
        "_build_actual_source_keys",
        lambda self, certifications: set(),
    )
    monkeypatch.setattr(
        HistoricalReplayCertificationValidator,
        "_find_missing_source_keys",
        lambda self, expected, actual: (("chembl", "activity", "p"),),
    )
    with pytest.raises(ValueError, match="missing sources"):
        validator.validate_certification_coverage(
            manifest=SimpleNamespace(),  # type: ignore[arg-type]
            certifications=(SimpleNamespace(),),  # type: ignore[arg-type]
        )
    monkeypatch.setattr(
        HistoricalReplayCertificationValidator,
        "_find_matching_queries",
        lambda self, manifest, certification: ["q1", "q2"],
    )
    with pytest.raises(ValueError, match="ambiguous"):
        validator.resolve_certification_query(
            manifest=SimpleNamespace(),  # type: ignore[arg-type]
            certification=SimpleNamespace(  # type: ignore[arg-type]
                query="",
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
            ),
        )
    monkeypatch.setattr(
        HistoricalReplayCertificationValidator,
        "_find_matching_queries",
        lambda self, manifest, certification: ["only"],
    )
    assert (
        validator.resolve_certification_query(
            manifest=SimpleNamespace(),  # type: ignore[arg-type]
            certification=SimpleNamespace(  # type: ignore[arg-type]
                query="",
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
            ),
        )
        == "only"
    )
    assert (
        validator.resolve_certification_query(
            manifest=SimpleNamespace(),  # type: ignore[arg-type]
            certification=SimpleNamespace(  # type: ignore[arg-type]
                query="  keep  ",
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
            ),
        )
        == "keep"
    )


@pytest.mark.asyncio
async def test_protein_class_skip_and_assay_gold() -> None:
    host = ProteinClassTransformer.__new__(ProteinClassTransformer)
    assert (
        await host.transform_pre_silver(
            object(),  # type: ignore[arg-type]
            {"protein_class_id": 0},
            0,
        )
        is None
    )
    assert (
        await host._transform_impl(
            object(),  # type: ignore[arg-type]
            {"protein_class_id": -1},
            0,
        )
        is None
    )
    assay = AssayTransformer.__new__(AssayTransformer)
    gold = assay.transform_for_gold(
        object(),  # type: ignore[arg-type]
        {"assay_description": "binding", "assay_id": 1},
    )
    assert gold["description"] == "binding"


def test_tpc_int_parse_and_multifunctional_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _int_or_none("  ") is None
    assert _int_or_none("nope") is None
    assert _int_or_none(1.5) is None
    assert _int_or_none(object()) is None
    assert (
        _multifunctional_origin([{"component_id": 1}, {"component_id": 2}])
        == "multi_component_heterogeneity"
    )
    monkeypatch.setattr(
        "bioetl.application.pipelines.chembl.target_protein_classification_summary.derive_protein_class_target_type",
        lambda *_a, **_k: SimpleNamespace(counted_top_levels=("other",)),
    )
    fallback = _representative_row_for_primary_top_level(
        rows=[{"component_id": 1}],
        primary_top_level="enzyme",
        mapping_data=MagicMock(),  # type: ignore[arg-type]
    )
    assert fallback == {"component_id": 1}


def test_runtime_state_structural_and_filtered_out() -> None:
    class _Host(BatchExecutorRuntimeStateMixin):
        def __init__(self) -> None:
            self._runtime_state = BatchExecutorRuntimeState()

    host = _Host()
    host._silver_records_for_dq = []
    host._gold_records_for_dq = [{"id": 1}]
    host._dq_reservoir_ranks = {"a": ["h"]}
    assert host._gold_records_for_dq == [{"id": 1}]
    contract = StructuralFieldSpec(
        field_name="flag",
        logical_type="boolean",
        physical_type="bool",
        nullable=True,
        optional=False,
        optional_sources=(),
        boolean_true_values=("yes",),
        boolean_false_values=("no",),
    )
    details = build_structural_details(
        reason_code="type",
        contract=contract,
        actual_value=1,
        action_taken="warn",
        dq_error=True,
    )
    assert details["dq_error"] is True
    debug = MagicMock()
    outcome = handle_filtered_out_error(
        FilteredOutError("skip"),
        SimpleNamespace(  # type: ignore[arg-type]
            batch_metrics=MagicMock(),
            dq_config=SimpleNamespace(invalid_record_policy="skip"),
            raw_record={"id": 1},
            debug_export_service=debug,
            index=0,
        ),
    )
    debug.record_filtered_out.assert_called()
    assert outcome.silver_record is None
    with pytest.raises(FilteredOutError):
        handle_filtered_out_error(
            FilteredOutError("fail"),
            SimpleNamespace(  # type: ignore[arg-type]
                batch_metrics=MagicMock(),
                dq_config=SimpleNamespace(invalid_record_policy="fail"),
                raw_record={"id": 1},
                debug_export_service=None,
                index=0,
            ),
        )
    dq_debug = MagicMock()
    dq_outcome = handle_data_quality_transform_error(
        ValueError("dq"),
        error_type=ErrorType.DATA_QUALITY,
        batch_metrics=MagicMock(),
        dq_config=SimpleNamespace(invalid_record_policy="skip"),
        raw_record={"id": 1},
        debug_export_service=dq_debug,
        index=0,
    )
    dq_debug.record_data_quality_failure.assert_called()
    assert dq_outcome.silver_record is None
    assert preview_value("ok", field_name="flag") == "'ok'"


@pytest.mark.asyncio
async def test_coordinator_threshold_and_runner_mixins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mixin = EnrichmentCoordinatorResultMixin.__new__(EnrichmentCoordinatorResultMixin)
    mixin._logger = MagicMock()
    mixin._dq_config = SimpleNamespace(get_enricher_hard_threshold=lambda _p: 0.01)
    now = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    runner = SimpleNamespace(
        execution_metrics={"records_silver": 1, "records_quarantined": 9}
    )
    via_builder = mixin._build_enricher_result(
        enricher=SimpleNamespace(pipeline="chembl_activity"),  # type: ignore[arg-type]
        runner=runner,  # type: ignore[arg-type]
        records_input=10,
        started_at=now,
        completed_at=now,
        duration=1.0,
    )
    assert via_builder.status.value == "failed"
    failed = mixin._build_threshold_failure_result(
        enricher=SimpleNamespace(pipeline="chembl_activity"),  # type: ignore[arg-type]
        records_input=10,
        records_enriched=1,
        records_errored=9,
        dq_error_rate=0.9,
        hard_threshold=0.2,
        started_at=now,
        completed_at=now,
        duration=1.0,
    )
    assert failed.status.value == "failed"
    support = _CompositeRunnerStageSupportMixin()
    support._record_dependencies_stage_started(["d"])
    support._record_enrichment_stage_started(["e"])
    support._record_enrichment_stage_completed({})
    state = CompositeCheckpointState(composite_name="chembl_activity", run_id="run-1")
    monkeypatch.setattr(
        "bioetl.application.composite.runner_pkg.runner_merge_stage_execution_mixin.start_merge_phase",
        AsyncMock(return_value=state),
    )
    monkeypatch.setattr(
        "bioetl.application.composite.runner_pkg.runner_merge_stage_execution_mixin.handle_merge_phase_exception",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "bioetl.application.composite.runner_pkg.runner_merge_stage_execution_mixin.handle_dry_run_merge_skip",
        lambda self, checkpoint: checkpoint,
    )
    monkeypatch.setattr(
        "bioetl.application.composite.runner_pkg.runner_merge_stage_execution_mixin.run_prepared_merge_request",
        AsyncMock(return_value="merged"),
    )
    monkeypatch.setattr(
        "bioetl.application.composite.runner_pkg.runner_merge_stage_execution_mixin.execute_started_merge_phase",
        AsyncMock(return_value="executed"),
    )
    host = CompositeRunnerMergeStageMixin()
    assert host._handle_dry_run_merge_skip(state) is state
    await host._start_merge_phase(state)  # type: ignore[arg-type]
    await host._handle_merge_phase_exception(state, RuntimeError("merge"))  # type: ignore[arg-type]
    assert await host._run_prepared_merge_request(MagicMock()) == "merged"  # type: ignore[arg-type]
    assert (
        await host._execute_started_merge_phase(  # type: ignore[arg-type]
            state, enrichment_results={}, dependency_results=None
        )
        == "executed"
    )


def test_leftover_eight_remaining_one_and_three_line_clusters() -> None:
    assert "input_snapshot_payload" in _snapshot_payloads.__all__
    assert infer_silver_table("chembl_activity") == "silver/chembl/activity"
    assert _collect_alias_matches(
        field_to_cols={"title": ["seed.title", "chembl.title"]},
        aliases={"title"},
        used={"seed.title"},
    ) == ["chembl.title"]
    emit_batch_failed(
        emitter=MagicMock(),
        run_id=None,
        batch_id=BatchID(UUID("12345678-1234-5678-1234-567812345678")),
        layer="silver",
        error=RuntimeError("write"),
        occurred_at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
    )
    assert build_interpro_entry({}) is None
    assert build_pfam_entry({}) is None
    assert build_reactome_entry({}) is None
    assert (
        _should_redact_columns(("email",), options=ExportOptions(role="admin")) is False
    )
    healthy = metrics_rec._reconcile_outcome(
        successes=("s",),
        workflow_successes=(),
        scrape_has_samples=True,
        scrape_has_workflow=False,
        missing=(),
        missing_workflows=(),
    )
    assert healthy.status == "healthy"
    assert metrics_rec._gap_state(missing=("chembl_activity:full",)) == (
        "durable_success_without_scrape_samples"
    )
    labeled = (
        'bioetl_pipeline_runs_total{pipeline="chembl_activity",run_type="full"} 1\n'
    )
    assert (
        metrics_rec._exposition_has_labeled_pipeline_runs_sample(
            labeled, pipeline="chembl_activity", run_type="full"
        )
        is True
    )


@pytest.mark.asyncio
async def test_pubchem_and_tpc_transformer_skip_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pubchem = PubChemCompoundTransformer.__new__(PubChemCompoundTransformer)
    monkeypatch.setattr(
        pubchem,
        "_build_compound_business_data",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("bad compound")),
    )
    ctx = SimpleNamespace(logger=MagicMock())
    assert await pubchem.transform_pre_silver(ctx, {}, 0) is None  # type: ignore[arg-type]
    tpc = TargetProteinClassificationTransformer.__new__(
        TargetProteinClassificationTransformer
    )
    monkeypatch.setattr(tpc, "_resolve_primary_id", lambda _record: "CHEMBL1")
    monkeypatch.setattr(
        tpc, "_extract_business_data", lambda _record, _pid: {"target_id": "CHEMBL1"}
    )
    monkeypatch.setattr(
        tpc,
        "_stage_optional_normalized_business_data",
        lambda **_k: {"target_id": "CHEMBL1"},
    )
    staged = await tpc.transform_pre_silver(object(), {"target_id": "CHEMBL1"}, 0)  # type: ignore[arg-type]
    assert staged == {"target_id": "CHEMBL1"}
