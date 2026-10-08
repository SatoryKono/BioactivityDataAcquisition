"""Stream B APP: leftover 5-line DQ helpers, runner stages, and remaining 4-line branches."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.runner_pkg.runner_stage_mixin import (
    CompositeRunnerStageMixin,
)
from bioetl.application.core.batch_executor_dq_helpers import (
    build_dataframe_from_records,
    build_dq_report_context,
    dataframe_error_types,
    normalize_records_for_polars,
)
from bioetl.application.core.runner_flow import (
    emit_pipeline_completion,
    emit_pipeline_start,
    record_run_shutdown,
)
from bioetl.application.observability.control_plane_evidence.checkpoint_validation import (
    _checkpoint_schema_check,
    _metadata_text,
)
from bioetl.application.observability.control_plane_evidence.retention import (
    _artifact_matches_manifest,
)
from bioetl.application.observability.observer_context_mixin import (
    _ObserverContextManagerMixin,
)
from bioetl.application.observability.replay_write_risk import (
    _declares_append_semantic_sink,
    _has_explicit_clear,
    _iter_config_roots,
)
from bioetl.application.pipelines.crossref.author_extractors import (
    extract_author_details,
    extract_author_orcids,
)
from bioetl.application.pipelines.uniprot.extractors._comment_structured_facets import (
    _extract_alternative_products_family_raw,
    _extract_cofactors_raw,
    _extract_subcellular_locations_raw,
)
from bioetl.application.services.control_plane.effective_config.runtime_overrides import (
    coerce_runtime_override_layer,
)
from bioetl.application.services.control_plane.forensic.diagnostics_support import (
    coerce_int,
    inspection_service_factory_from_ports,
    resolve_forensic_verdict,
)
from bioetl.application.services.control_plane.manifest._inspection_support import (
    RunManifestInspectionDiffClassificationMixin,
)
from bioetl.application.services.control_plane.replay.historical_closure_models import (
    HistoricalReplayClosureReportRecord,
    HistoricalReplayResidualDispositionRecord,
)
from bioetl.application.services.control_plane.replay.historical_corpus_policy import (
    SUPPORTED_BROADER_POLICY,
    certification_scope_for_context,
    classify_certification_status,
)
from bioetl.application.services.dq._checks_integrity import (
    _count_scd_overlaps,
    _materialize_entity_key,
    _normalize_scd_config,
)
from bioetl.application.services.export_lineage.debug_export_service import (
    DebugExportConfig,
    DebugExportService,
)
from bioetl.application.services.run_reports.source_identity import _mapped_runtime_path
from bioetl.domain.exceptions import BioETLError

pytestmark = pytest.mark.unit


def test_dq_helpers_import_none_and_started_at(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def _import(name: str, *args: object, **kwargs: object) -> object:
        if name == "polars":
            raise ModuleNotFoundError("polars")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    assert dataframe_error_types()
    monkeypatch.setattr(builtins, "__import__", real_import)

    mixed = normalize_records_for_polars(
        [
            {"payload": None, "flag": 1},
            {"payload": {"x": 1}, "flag": 2},
            {"payload": "raw", "flag": 3},
        ]
    )
    assert mixed is not None

    import polars as real_pl

    class _BoomFrame:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise ValueError("df")

    monkeypatch.setattr(real_pl, "DataFrame", _BoomFrame)
    assert (
        build_dataframe_from_records(
            records=[{"payload": {"x": 1}}, {"payload": "raw"}],
            logger=MagicMock(),
        )
        is None
    )

    with pytest.raises(ValueError, match="started_at"):
        build_dq_report_context(
            context=SimpleNamespace(  # type: ignore[arg-type]
                started_at=None, replay_timestamp_anchor=None, run_id="run-1"
            ),
            config=SimpleNamespace(  # type: ignore[arg-type]
                dq_config=None,
                pipeline_name="chembl_activity",
                provider="chembl",
                entity_type="activity",
                table_config=SimpleNamespace(
                    silver_table="silver_activity", primary_keys=("id",)
                ),
                bronze_output_path="bronze",
            ),
            bronze_records=[],
            silver_records=[],
            gold_records=[],
            source_batch_ids=[],
            last_bronze_path=None,
            records_fetched=0,
            records_quarantined=0,
            build_dataframe=lambda *_a: None,
        )


@pytest.mark.asyncio
async def test_runner_stage_skip_success_and_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = CompositeCheckpointState(composite_name="chembl_activity", run_id="run-1")
    keys = pl.DataFrame({"id": [1]})

    class _SkipHost:
        def _has_dependencies_configured(self) -> bool:
            return False

        async def _skip_dependencies_phase(
            self, checkpoint: CompositeCheckpointState
        ) -> tuple[CompositeCheckpointState, dict[str, object]]:
            return checkpoint, {}

    skipped = await CompositeRunnerStageMixin._execute_dependencies_phase(
        _SkipHost(),  # type: ignore[arg-type]
        state,
        keys,
    )
    assert skipped[1] == {}

    class _OkHost:
        def _has_dependencies_configured(self) -> bool:
            return True

        def _prepare_dependencies_run_context(self) -> str:
            return "ctx"

        async def _start_dependencies_phase(
            self, checkpoint: CompositeCheckpointState, context: str
        ) -> CompositeCheckpointState:
            return checkpoint

        async def _run_dependencies(self, **_kwargs: object) -> dict[str, object]:
            return {"dep": object()}

        async def _postprocess_dependency_results(
            self, checkpoint: CompositeCheckpointState, results: dict[str, object]
        ) -> tuple[CompositeCheckpointState, dict[str, object]]:
            return checkpoint, results

        async def _execute_started_dependencies_phase(
            self,
            checkpoint: CompositeCheckpointState,
            *,
            context: str,
            keys_df: pl.DataFrame,
        ) -> tuple[CompositeCheckpointState, dict[str, object]]:
            return await CompositeRunnerStageMixin._execute_started_dependencies_phase(
                self,  # type: ignore[arg-type]
                checkpoint,
                context=context,  # type: ignore[arg-type]
                keys_df=keys_df,
            )

    started = await CompositeRunnerStageMixin._execute_dependencies_phase(
        _OkHost(),  # type: ignore[arg-type]
        state,
        keys,
    )
    assert "dep" in started[1]

    monkeypatch.setattr(
        "bioetl.application.composite.runner_pkg.runner_stage_completion_mixin.handle_dependencies_phase_exception",
        AsyncMock(),
    )
    await CompositeRunnerStageMixin._handle_dependencies_phase_exception(
        SimpleNamespace(),  # type: ignore[arg-type]
        state,
        BioETLError("dep"),
    )


def test_dedup_empty_list_and_datetime_expr() -> None:
    service = EnricherDeduplicatorService(logger=MagicMock())
    empty = pl.DataFrame({"id": [], "value": []})
    conflicts, clean = service._classify_columns(empty, ["id"], ["value"])
    assert conflicts == [] and clean == ["value"]
    list_expr = service._to_string_expr("tags", pl.List(pl.String))
    dt_expr = service._to_string_expr("ts", pl.Datetime("us"))
    df = pl.DataFrame({"tags": [["a"]], "ts": [datetime(2024, 1, 1, tzinfo=UTC)]})
    assert df.select(list_expr.alias("tags"), dt_expr.alias("ts")).height == 1


def test_runner_flow_emit_and_shutdown_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    host = SimpleNamespace(
        _logger=MagicMock(),
        _config=SimpleNamespace(pipeline_name="chembl_activity"),
        _runtime=SimpleNamespace(run_type=SimpleNamespace(value="incremental")),
        _executor=SimpleNamespace(records_fetched=3),
        _context=SimpleNamespace(run_id="run-1"),
    )
    emit_pipeline_start(host)  # type: ignore[arg-type]
    emit_pipeline_completion(host)  # type: ignore[arg-type]
    monkeypatch.setattr(
        "bioetl.application.core.runner_flow._record_run_metrics_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "bioetl.application.core.runner_flow._record_flow_invariants_impl",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("inv")),
    )
    record_run_shutdown(host)  # type: ignore[arg-type]
    host._logger.warning.assert_called()


def test_observer_optional_attrs_and_failed_span() -> None:
    observer = _ObserverContextManagerMixin.__new__(_ObserverContextManagerMixin)
    observer.pipeline_name = "chembl_activity"
    observer.run_id = "run-1"
    observer.run_type = "incremental"
    observer.manifest_id = None
    observer.effective_config_hash = None
    observer.contract_ref = "contract"
    observer.contract_version = None
    observer.composite_run_id = None
    attrs = observer._build_trace_attributes()
    assert "bioetl.manifest_id" not in attrs
    observer.span = MagicMock()
    observer._tracer = None
    observer._close_span_safely("failed", 0.5, ValueError, ValueError("boom"), None)
    observer.span.record_exception.assert_called()


def test_replay_risk_retention_and_checkpoint_schema() -> None:
    manifest = SimpleNamespace(
        runtime_config="skip",
        resolved_config={"pipeline": {"gold_write_mode": "append"}},
        launch_context={
            "append_mode_semantic_sinks": ["gold"],
            "clear_policy": "both",
        },
        run_type="incremental",
        replay_of_run_id=None,
        replay_of_manifest_id=None,
        manifest_id="m1",
        run_id="run-1",
        code_provenance=SimpleNamespace(effective_config_artifact_id="cfg"),
        source_refs=(),
    )
    assert _iter_config_roots(manifest)  # type: ignore[arg-type]
    assert _declares_append_semantic_sink(manifest) is True  # type: ignore[arg-type]
    assert _has_explicit_clear(manifest) is True  # type: ignore[arg-type]
    artifact = SimpleNamespace(artifact_id="cfg", protected_by=())
    assert _artifact_matches_manifest(artifact, manifest) is True  # type: ignore[arg-type]
    invalid = _checkpoint_schema_check({"checkpoint_saved_at_epoch_seconds": "bad"})
    assert invalid.reason == "checkpoint_saved_at_invalid"
    assert (
        _metadata_text(
            {"run_context": {"pipeline_name": "chembl_activity"}}, "pipeline_name"
        )
        == "chembl_activity"
    )


def test_extractors_runtime_overrides_and_diagnostics() -> None:
    assert extract_author_details({"author": ["skip", {"family": "Doe"}]})
    assert extract_author_orcids({"author": ["skip"]}) == []
    index = {
        "SUBCELLULAR LOCATION": [{"subcellularLocations": "nope"}],
        "ALTERNATIVE PRODUCTS": [{"isoforms": "nope"}],
        "COFACTOR": [{"cofactors": "nope"}],
    }
    assert _extract_subcellular_locations_raw(index) == []
    assert _extract_alternative_products_family_raw(index)[0] == []
    assert _extract_cofactors_raw(index) == []
    assert coerce_runtime_override_layer({"env": None}, "env") == {}
    with pytest.raises(TypeError, match="must be a mapping"):
        coerce_runtime_override_layer({"env": ["x"]}, "env")
    factory = inspection_service_factory_from_ports(
        MagicMock(),
        None,
        lambda: "ready",  # type: ignore[arg-type, return-value]
    )
    assert factory() == "ready"
    assert coerce_int(1.5) == 1
    assert coerce_int("nope") == 0
    verdict = resolve_forensic_verdict(
        manifest_diff=SimpleNamespace(classification="semantic_drift"),  # type: ignore[arg-type]
        forensic_diff={},
    )
    assert verdict == "semantic_drift"


def test_inspection_identical_and_replay_relationships(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identical = RunManifestInspectionDiffClassificationMixin._classify_manifest_diff(
        left_manifest=MagicMock(),
        right_manifest=MagicMock(),
        differences=(),
    )
    assert identical["classification"] == "identical"
    monkeypatch.setattr(
        RunManifestInspectionDiffClassificationMixin,
        "_manifest_replays_other",
        staticmethod(lambda *, manifest, other: True),
    )
    assert (
        RunManifestInspectionDiffClassificationMixin._resolve_replay_relationship(
            left_manifest=MagicMock(),
            right_manifest=MagicMock(),
        )
        == "mutual_replay_cycle"
    )


def test_historical_models_policy_integrity_and_paths() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        HistoricalReplayResidualDispositionRecord(
            manifest_id="m1",
            disposition="nope",
            rationale="x",
        )
    report = HistoricalReplayClosureReportRecord(
        generated_at=datetime(2024, 1, 1, tzinfo=UTC),
        report_id="r1",
        inventory=object(),
        residual_dispositions=(),
        suggested_resolution_queue=(),
        closure_verdict="open",
        closure_reason="none",
        claim_scope_mode="all_retained_historical_runs",
        global_universal_historical_replay_claim={},
        retained_corpus_claim={},
    )
    assert report.to_dict()["inventory"] == {}
    status, _reasons = classify_certification_status(
        broader_policy="other",
        replay_occurrence_kind="x",
        broader_state="x",
    )
    assert status == "outside_certified_historical_scope"
    replayable, _ = classify_certification_status(
        broader_policy=SUPPORTED_BROADER_POLICY,
        replay_occurrence_kind="x",
        broader_state="exact_replay_child_run",
    )
    assert replayable == "already_replayable"
    review, _ = classify_certification_status(
        broader_policy=SUPPORTED_BROADER_POLICY,
        replay_occurrence_kind="x",
        broader_state="unknown",
    )
    assert review == "needs_operator_review"
    assert certification_scope_for_context("source") == "historical_source_replay"
    overlaps = _count_scd_overlaps(
        df=pl.DataFrame({"id": [1]}),
        entity_key="id",
        valid_from="vf",
        valid_to="vt",
    )
    assert overlaps == 0
    keyed, name = _materialize_entity_key(
        pl.DataFrame({"a": [1], "b": [2]}), entity_keys=("a", "b")
    )
    assert name == "__scd_entity_key" and "__scd_entity_key" in keyed.columns
    assert (
        _normalize_scd_config(
            pl.DataFrame({"a": [1]}), SimpleNamespace(business_keys=())
        )
        is None
    )  # type: ignore[arg-type]
    assert _mapped_runtime_path("//wsl$/Ubuntu/home/data") == "/home/data"


@pytest.mark.asyncio
async def test_debug_export_disabled_root_and_finalize() -> None:
    service = DebugExportService(
        config=DebugExportConfig(enabled=False),
        run_id="00000000-0000-0000-0000-000000000001",
        pipeline_id="chembl_activity",
        provider_id="chembl",
    )
    service.set_debug_root("tmp-debug")
    with pytest.raises(RuntimeError, match="not enabled"):
        await service.persist()
    assert service.finalize(status="complete", manifest_id=None) is None
