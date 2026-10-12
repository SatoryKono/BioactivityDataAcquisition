"""Stream B APP: leftover 4-line aggregator, persistence, postrun, and mixin branches."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.aggregator import (
    EnricherAggregator,
    _deduplicate_columns,
)
from bioetl.application.composite.checkpoint.persistence_service import (
    CompositeCheckpointPersistenceService,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.composite.cross_validator_helpers import (
    _build_enricher_detail,
    _combine_cv_details,
    _compare_field,
)
from bioetl.application.composite.runner_pkg.runner_control_plane_mixin import (
    _CompositeRunnerLedgerLifecycleMixin,
)
from bioetl.application.core.base_transformer.base import BaseTransformer
from bioetl.application.core.batch_executor_dq_mixin import _BatchExecutorDQMixin
from bioetl.application.core.batch_writer_columns_mixin import BatchWriterColumnsMixin
from bioetl.application.core.postrun._phase_runtime import (
    resolve_postrun_phase_log_level,
    run_async_postrun_phase,
    run_sync_postrun_phase,
)
from bioetl.application.core.preflight.medallion_validator_runtime import (
    validate_medallion_policy_consistency,
)
from bioetl.application.services.lineage.metadata_assembler_support import (
    _stable_unique_text,
    coerce_rule_provenance_mappings,
    normalize_rule_provenance_entries,
)
from bioetl.application.services.quality._quarantine_service_status_sync import (
    QuarantineServiceStatusSyncMixin,
)
from bioetl.application.services.run_reports.query import (
    _collect_report_candidates,
    _load_json_dict,
    _load_latest_report,
)
from bioetl.application.services.workflow._observability_workflow_next_steps_support import (
    _degraded_evidence_steps,
    _manifest_next_steps,
    _missing_evidence_steps,
)
from bioetl.application.services.workflow._observability_workflow_quarantine_support import (
    enrich_quarantine_summary,
    resolve_bronze_record_count,
)
from bioetl.application.services.workflow._observability_workflow_status_support import (
    build_status_section,
)
from bioetl.domain.composite.aggregation import AggregationConfig, AggregationFieldSpec
from bioetl.domain.composite.cross_validation import ComparisonMethod
from bioetl.domain.exceptions import BioETLError, CheckpointConflictError
from bioetl.domain.medallion import ClearPolicy, MedallionPolicy
from bioetl.domain.types.enums import QuarantineRecordStatus, RunType

pytestmark = pytest.mark.unit


def test_aggregator_dedupe_sort_and_fallback_expr() -> None:
    assert _deduplicate_columns(["id", "id", "name"]) == ["id", "name"]
    aggregator = EnricherAggregator(logger=MagicMock())
    config = AggregationConfig(
        group_by="id",
        fields=(AggregationFieldSpec(source_field="term", agg_function="concat_str"),),
        order_by=("missing_col",),
    )
    df = pl.DataFrame({"term": ["b", "a"]})
    assert aggregator._sort_for_deterministic_aggregation(df, config).equals(df)
    fallback = aggregator._build_aggregation_expr(
        SimpleNamespace(  # type: ignore[arg-type]
            effective_output_field="term",
            source_field="term",
            filter_condition=None,
            agg_function="unknown",
        )
    )
    concat = aggregator._build_aggregation_expr(
        AggregationFieldSpec(source_field="term", agg_function="concat_str")
    )
    assert fallback is not None and concat is not None


def test_checkpoint_persistence_none_timestamp_and_save_errors() -> None:
    metrics = MagicMock()
    service = CompositeCheckpointPersistenceService(
        composite_name="chembl_activity",
        checkpoint_filename="cp.json",
        glob_pattern="cp-*.json",
        storage=MagicMock(),
        logger=MagicMock(),
        metrics=metrics,
    )
    empty = CompositeCheckpointState(composite_name="chembl_activity", run_id="run-1")
    service._emit_checkpoint_saved_at_from_state(empty)
    metrics.set_gauge.assert_not_called()

    service._storage.write_atomic.side_effect = ValueError("disk")
    with pytest.raises(CheckpointConflictError):
        service.save(empty)

    service._storage.write_atomic.side_effect = BioETLError("bio")
    with pytest.raises(BioETLError, match="bio"):
        service.save(empty)


def test_control_plane_mixin_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(
        "bioetl.application.composite.runner_pkg.runner_control_plane_mixin.record_with_ledger_service",
        lambda *_a, **_k: seen.append("ledger"),
    )
    monkeypatch.setattr(
        "bioetl.application.composite.runner_pkg.runner_control_plane_mixin.record_run_metrics_event",
        lambda *_a, **_k: seen.append("metrics"),
    )
    monkeypatch.setattr(
        "bioetl.application.composite.runner_pkg.runner_control_plane_mixin.record_stage_started",
        lambda *_a, **_k: seen.append("started"),
    )
    monkeypatch.setattr(
        "bioetl.application.composite.runner_pkg.runner_control_plane_mixin.record_stage_completed",
        lambda *_a, **_k: seen.append("completed"),
    )

    class _Host(_CompositeRunnerLedgerLifecycleMixin):
        pass

    host = _Host()
    host._record_with_ledger_service(lambda _svc: None)
    host._record_run_metrics_event(metrics_snapshot={}, recorder=lambda *_a, **_k: None)
    host._record_stage_started(stage="seed")
    host._record_stage_completed(stage="seed", metrics_snapshot={})
    assert seen == ["ledger", "metrics", "started", "completed"]


class _TinyTransformer(BaseTransformer):
    async def _transform_impl(
        self, context: object, record: object, index: int
    ) -> object:
        return None


def test_transformer_unexpected_kwargs_and_silver_filter() -> None:
    with pytest.raises(TypeError, match="unexpected keyword"):
        _TinyTransformer(provider="chembl", bogus=True)
    host = SimpleNamespace(
        _silver_filters=SimpleNamespace(
            is_empty=lambda: False, should_include=lambda _r: False
        ),
        _gold_filters=SimpleNamespace(
            is_empty=lambda: False, should_include=lambda _r: True
        ),
    )
    assert BaseTransformer.should_write_silver(host, object(), {"id": 1}) is False  # type: ignore[arg-type]
    assert BaseTransformer.should_write_gold(host, object(), {"id": 1}) is True  # type: ignore[arg-type]


def test_postrun_failed_level_and_sync_error() -> None:
    assert resolve_postrun_phase_log_level("failed") == "error"
    emitted: list[str] = []

    def _emit(**kwargs: object) -> None:
        emitted.append(str(kwargs.get("status")))

    def _boom() -> object:
        raise RuntimeError("phase")

    with pytest.raises(RuntimeError, match="phase"):
        run_sync_postrun_phase(
            span_factory=lambda _name: nullcontext(
                SimpleNamespace(set_attribute=lambda *_a, **_k: None)
            ),
            phase="vacuum",
            operation=_boom,
            operation_errors=(RuntimeError,),
            emit_phase_observability=_emit,
            on_success=lambda _r: SimpleNamespace(  # type: ignore[arg-type]
                span_attributes={}, status="ok", level="info", observability_fields={}
            ),
        )
    assert "failed" in emitted


@pytest.mark.asyncio
async def test_async_postrun_phase_propagates_operation_error() -> None:
    emitted: list[str] = []

    async def _boom() -> object:
        raise RuntimeError("phase")

    def _emit(**kwargs: object) -> None:
        emitted.append(str(kwargs.get("status")))

    with pytest.raises(RuntimeError, match="phase"):
        await run_async_postrun_phase(
            span_factory=lambda _name: nullcontext(
                SimpleNamespace(set_attribute=lambda *_a, **_k: None)
            ),
            phase="vacuum",
            operation=_boom,
            operation_errors=(RuntimeError,),
            emit_phase_observability=_emit,
            on_success=lambda _r: SimpleNamespace(  # type: ignore[arg-type]
                span_attributes={}, status="ok", level="info", observability_fields={}
            ),
        )
    assert "failed" in emitted


def test_column_rename_schema_noop_and_error() -> None:
    mixin = BatchWriterColumnsMixin()
    assert mixin._apply_renames_to_schema(None, {"a": "b"}) is None
    schema = SimpleNamespace(names=["id"], rename_columns=lambda names: names)
    assert mixin._apply_renames_to_schema(schema, {"other": "x"}) is schema

    class _Boom:
        names = ["id"]

        def rename_columns(self, _names: list[str]) -> object:
            raise ValueError("bad schema")

    boom = _Boom()
    assert mixin._apply_renames_to_schema(boom, {"id": "pk"}) is boom


def test_medallion_rebuild_and_incremental_policy_errors() -> None:
    rebuild = validate_medallion_policy_consistency(
        run_type=RunType.REBUILD,
        policy=MedallionPolicy(clear_policy=ClearPolicy.NEVER),
    )
    incremental = validate_medallion_policy_consistency(
        run_type=RunType.INCREMENTAL,
        policy=MedallionPolicy(clear_policy=ClearPolicy.SILVER_AND_GOLD),
    )
    assert rebuild and incremental


def test_next_steps_status_and_quarantine_fallbacks() -> None:
    assert _manifest_next_steps(None) == ()
    assert _manifest_next_steps(SimpleNamespace(diagnostics={"next_steps": "x"})) == ()  # type: ignore[arg-type]
    assert _missing_evidence_steps(("run_manifest",))
    assert _degraded_evidence_steps(("composite_correlation_policy_gap",))
    manifest = SimpleNamespace(
        diagnostics={
            "persistence_profile": {
                "attained_profile": "forensic_grade",
                "required_profile_satisfied": False,
            },
            "latest_status": "success",
            "critical_pipeline": True,
        }
    )
    section = build_status_section(
        run_manifest=manifest,  # type: ignore[arg-type]
        checkpoint=SimpleNamespace(metadata={"status": "present"}),  # type: ignore[arg-type]
        lineage=object(),  # type: ignore[arg-type]
        quarantine_summary={"ok": True},
        missing_evidence=(),
        degraded_evidence=(),
    )
    assert section["checkpoint_status"] == "present"
    bronze = resolve_bronze_record_count(
        SimpleNamespace(  # type: ignore[arg-type]
            ledger_entries=(
                SimpleNamespace(metrics_snapshot="skip"),
                SimpleNamespace(metrics_snapshot={"records_bronze": 0}),
                SimpleNamespace(metrics_snapshot={"records_bronze": 8}),
            )
        )
    )
    assert bronze == 8
    enriched = enrich_quarantine_summary(
        stats={"silver_filter_rejects": {"total_count": 2}},
        run_id="run-1",
        run_manifest=SimpleNamespace(  # type: ignore[arg-type]
            ledger_entries=(SimpleNamespace(metrics_snapshot={"records_bronze": 8}),)
        ),
    )
    assert enriched["silver_filter_rejects"]["bronze_records"] == 8


def test_cross_validator_skip_fuzzy_none_and_empty_details() -> None:
    skip = _compare_field(
        pl.DataFrame({"a": [1]}),
        "a",
        "a",
        ComparisonMethod.SKIP,
        threshold=0.0,
    )
    assert skip.to_list() == [True]
    fuzzy = _compare_field(
        pl.DataFrame({"a": [None], "b": ["x"]}),
        "a",
        "b",
        ComparisonMethod.FUZZY,
        threshold=0.8,
    )
    assert fuzzy.to_list() == [True]
    empty_detail = _build_enricher_detail("chembl_activity", {}, pl.Series([0, 1]))
    assert empty_detail.null_count() == 2
    combined = _combine_cv_details([], 2)
    assert combined.null_count() == 2


def test_dq_mixin_invalid_utf8_and_helpers() -> None:
    payload = _BatchExecutorDQMixin._serialize_dq_sample_item(b"\xff")
    assert payload == b"\xff".hex()
    assert _BatchExecutorDQMixin._dataframe_error_types()
    assert _BatchExecutorDQMixin._stringify_value({"k": 1}, {"id"}, "id") == '{"k": 1}'


def test_metadata_assembler_empty_and_object_provenance() -> None:
    assert _stable_unique_text("not-a-collection") == []
    assert coerce_rule_provenance_mappings("nope") == []
    entry = SimpleNamespace(
        rule_id="r1",
        contract_version="1.0.0",
        severity="error",
        disposition="fail",
        config_path=None,
        report_artifact_path=None,
        policy_hash=None,
    )
    normalized = normalize_rule_provenance_entries([{"rule_id": "r0"}, entry])  # type: ignore[list-item]
    assert normalized[1]["rule_id"] == "r1"


def test_quarantine_status_update_operator_error() -> None:
    class _Host(QuarantineServiceStatusSyncMixin):
        def __init__(self) -> None:
            self.logger = MagicMock()
            self.quarantine_port = MagicMock()
            self.quarantine_port.update_status.side_effect = ValueError("port")

        def _derive_operator_completion(
            self, *, started_at: datetime, started_monotonic: float
        ) -> tuple[datetime, float]:
            return datetime(2026, 9, 16, 12, 0, tzinfo=UTC), 0.01

        def _record_operator_metrics(self, **_kwargs: object) -> None:
            return None

    with pytest.raises(ValueError, match="port"):
        _Host()._update_status_impl(
            payload_hash="abc",
            new_status=QuarantineRecordStatus.NEW,
            started_at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
            started_monotonic=0.0,
        )


def test_run_report_query_missing_pointer_and_bad_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MagicMock()
    monkeypatch.setattr(
        "bioetl.application.services.run_reports.query.load_latest_pointer",
        lambda **_k: None,
    )
    assert (
        _load_latest_report(
            kind="pipeline", owner="chembl", root=Path("reports"), store=store
        )
        is None
    )
    store.is_file.return_value = True
    store.read_text.return_value = "not-json"
    assert _load_json_dict(Path("x.json"), store=store) is None
    store.read_text.return_value = "[1]"
    assert _load_json_dict(Path("x.json"), store=store) is None
    store.is_dir.return_value = True
    store.iterdir.return_value = ["run-1"]
    store.is_file.return_value = False
    assert (
        _collect_report_candidates(
            base=Path("reports"), kind="pipeline", owner="chembl", store=store
        )
        == []
    )
