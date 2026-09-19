"""Behavior coverage for remaining two-line application residuals in #10469."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.checkpoint.load_service import (
    CompositeCheckpointLoadParams,
    CompositeCheckpointLoadService,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.application.composite.merge_service import MergeService
from bioetl.application.composite import merger_orchestration
from bioetl.application.composite.runner_pkg.runner_merge_request_flow import (
    get_explicit_merger_method,
    run_prepared_merge_request,
)
from bioetl.application.composite.runner_pkg.runner_support_flow import (
    build_correlation_log_context,
)
from bioetl.application.core._quarantine_manager_support import (
    QuarantineManagerSupportMixin,
)
from bioetl.application.core._record_normalization_mapping import (
    RecordNormalizationMappingMixin,
)
from bioetl.application.core._runner_finalize import (
    finalize_contract_evidence,
    finalize_debug_export,
)
from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
from bioetl.application.core.batch_processing_support import (
    BatchProcessingSupportService,
)
from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
from bioetl.application.core.preflight.health_aggregator import HealthAggregator
from bioetl.application.observability.control_plane_evidence.manifest_validation import (
    _contract_check,
    _optional_anchor_check,
)
from bioetl.application.services.control_plane.manifest._reference_hydration import (
    hydrate_source_refs,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profiles import (
    build_lineage_closure_boundary,
)
from bioetl.application.services.lineage.metadata_lineage_fragments_gold import (
    _find_gold_dataset_node,
    _find_run_node as _find_gold_run_node,
)
from bioetl.application.services.lineage.metadata_lineage_fragments_silver import (
    _find_run_node as _find_silver_run_node,
    _find_silver_dataset_node,
)
from bioetl.application.services.workflow._observability_workflow_execution import (
    inspect_checkpoint_workflow,
)


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_key_extractor_handles_series_and_reports_missing_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = SimpleNamespace(read_table=AsyncMock(return_value=object()))
    service = KeyExtractorService(reader, MagicMock())
    monkeypatch.setattr(pl, "from_arrow", lambda _table: pl.Series("id", ["A"]))
    frame = await service._read_silver_table("silver/table")
    assert frame.to_dict(as_series=False) == {"id": ["A"]}

    service._read_silver_table = AsyncMock(  # type: ignore[method-assign]
        return_value=pl.DataFrame({"id": ["A"]})
    )
    with pytest.raises(ValueError, match="Keys not found"):
        await service.extract("silver/table", ("missing",))


def test_merge_service_rejects_unexpected_runtime_keywords() -> None:
    with pytest.raises(TypeError, match="unexpected keyword"):
        MergeService(
            merge_config=MagicMock(),
            storage=MagicMock(),
            logger=MagicMock(),
            collaborators=MagicMock(),
            unsupported=True,
        )


@pytest.mark.asyncio
async def test_merge_workflow_builds_and_executes_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = object()
    expected = object()
    host = MagicMock()
    build = MagicMock(return_value=request)
    execute = AsyncMock(return_value=expected)
    monkeypatch.setattr(merger_orchestration, "build_merge_execution_request", build)
    monkeypatch.setattr(merger_orchestration, "execute_merge_request", execute)

    assert (
        await merger_orchestration.execute_merge_workflow(
            host,
            seed_table="silver/seed",
            enrichers=(),
            enrichment_results={},
            run_id="run-1",
        )
        is expected
    )
    build.assert_called_once()
    execute.assert_awaited_once_with(host, request)


def _checkpoint_loader(
    *, metrics: object | None = None, ledger: object | None = None
) -> CompositeCheckpointLoadService:
    return CompositeCheckpointLoadService(
        CompositeCheckpointLoadParams(
            composite_name="publication",
            run_id="run-1",
            storage=MagicMock(),
            logger=MagicMock(),
            resume=True,
            stale_threshold_hours=1.0,
            expected_context=MagicMock(),
            checkpoint_filename="checkpoint.json",
            glob_pattern="*.json",
            run_ledger_port=ledger,  # type: ignore[arg-type]
            metrics=metrics,  # type: ignore[arg-type]
        )
    )


def test_checkpoint_loader_skips_absent_metrics_and_unbound_manifest() -> None:
    service = _checkpoint_loader(ledger=MagicMock())
    service._emit_checkpoint_load_status("missing")
    state = CompositeCheckpointState(composite_name="publication", run_id="run-1")
    assert service._replay_checkpoint_suffix(state) is state


class _NonCallableMerger:
    execute_request = None
    merge = None


@pytest.mark.asyncio
async def test_merge_dispatch_rejects_noncallable_explicit_methods() -> None:
    merger = _NonCallableMerger()
    merger.__dict__["execute_request"] = "disabled"
    assert get_explicit_merger_method(merger, "execute_request") is None
    with pytest.raises(AttributeError, match="does not implement"):
        await run_prepared_merge_request(
            SimpleNamespace(_merger=merger),
            SimpleNamespace(),  # type: ignore[arg-type]
        )


def test_correlation_context_includes_available_contract_anchors() -> None:
    host = SimpleNamespace(
        _config=SimpleNamespace(name="publication", version="v2"),
        _run_id_str="run-1",
        _checkpoint_manager=SimpleNamespace(
            expected_effective_config_hash="a" * 64,
            expected_contract_ref="contract.ref",
            expected_contract_version="v3",
        ),
    )

    context = build_correlation_log_context(host, phase="merge")
    assert context["effective_config_hash"] == "a" * 64
    assert context["contract_ref"] == "contract.ref"
    assert context["contract_version"] == "3.0.0"


@pytest.mark.asyncio
async def test_quarantine_support_returns_plain_rows_and_stats() -> None:
    quarantine = SimpleNamespace(
        inspect=AsyncMock(return_value=({"record_id": "1"},)),
        get_stats=AsyncMock(return_value={"total": 1}),
    )
    host = SimpleNamespace(_quarantine=quarantine, _pipeline_name="chembl_activity")

    assert await QuarantineManagerSupportMixin.inspect(host) == [{"record_id": "1"}]
    assert await QuarantineManagerSupportMixin.get_stats(host) == {"total": 1}


def test_record_normalization_handles_blank_text_and_delegates_smiles() -> None:
    host = RecordNormalizationMappingMixin()
    host.rule_set = NormalizationRulesPolicy()
    assert host._normalize_string_field("payload", "   ") is None
    assert host._normalize_smiles_field("canonical_smiles", "C") == "C"


@pytest.mark.asyncio
async def test_runner_finalizers_fail_closed_without_context_and_skip_absent_hook() -> (
    None
):
    with pytest.raises(RuntimeError, match="manifest-bound launch context"):
        finalize_contract_evidence(
            SimpleNamespace(
                _contract_evidence_recorder=MagicMock(),
                manifest_id="manifest-1",
                _contract_evidence_context=None,
            )
        )

    await finalize_debug_export(
        SimpleNamespace(_executor=SimpleNamespace(), manifest_id="manifest-1"),
        "success",
    )


def test_batch_memory_exposes_trace_and_handles_missing_runtime_policy() -> None:
    manager = BatchMemoryManagerService(initial_batch_size=100)
    assert manager.decision_trace == ()
    assert manager._adjust(25, record_index=1) == 25


@pytest.mark.asyncio
async def test_batch_processing_rejects_unknown_runtime_and_records_debug_bronze() -> (
    None
):
    with pytest.raises(TypeError, match="unexpected keyword"):
        BatchProcessingSupportService(
            services=MagicMock(), logger=MagicMock(), unknown=True
        )

    debug = MagicMock()
    writer = MagicMock()
    writer.write_bronze.return_value = object()
    service = BatchProcessingSupportService(
        services=MagicMock(),
        logger=MagicMock(),
        batch_runtime={
            "batch_metrics": MagicMock(),
            "transformer": MagicMock(),
            "writer": writer,
            "tracing": MagicMock(),
            "quarantine_manager": MagicMock(),
        },
        debug_export_service=debug,
    )
    service._execute_with_span = AsyncMock(return_value="written")  # type: ignore[method-assign]
    result = await service.write_bronze_layer(
        records=[{"id": "1"}],  # type: ignore[list-item]
        batch_id="batch-1",  # type: ignore[arg-type]
        start_index=0,
        ingestion_ts=datetime(2026, 9, 17, tzinfo=UTC),
        source_metadata=None,
    )
    assert result == "written"
    debug.record_bronze_batch.assert_called_once()


@pytest.mark.asyncio
async def test_health_aggregator_rejects_mode_and_none_health_result() -> None:
    with pytest.raises(ValueError, match="health_check_mode"):
        HealthAggregator(health_check_mode="invalid")  # type: ignore[arg-type]

    service = HealthAggregator()
    services = SimpleNamespace(
        data_source=SimpleNamespace(check_health=AsyncMock(return_value=None))
    )
    with pytest.raises(TypeError, match="returned None"):
        await service._check_data_source(services)


def test_manifest_evidence_reports_incompatibility_and_reason_only_anchor() -> None:
    result = _contract_check(
        [],
        SimpleNamespace(
            contract_comparison_status="incompatible",
            contract_comparison_reason="schema_changed",
        ),
    )
    assert result.status == "ERROR"
    anchor = _optional_anchor_check(
        check="snapshot",
        value=None,
        reason_value="not_required",
        missing_reason="missing",
        missing_detail="missing detail",
        ok_reason="present",
        ok_detail="ok",
    )
    assert anchor.reason == "not_required"


def test_source_ref_hydration_accepts_none_snapshots_and_rejects_wrong_shape() -> None:
    refs = hydrate_source_refs(
        [
            {
                "provider": "chembl",
                "entity": "activity",
                "pipeline_name": "chembl_activity",
                "input_snapshots": None,
            }
        ]
    )
    assert refs[0].input_snapshots == ()
    with pytest.raises(ValueError, match="input_snapshots must be a list"):
        hydrate_source_refs(
            [
                {
                    "provider": "chembl",
                    "entity": "activity",
                    "pipeline_name": "chembl_activity",
                    "input_snapshots": "invalid",
                }
            ]
        )


def test_lineage_boundary_selects_composite_support_scope() -> None:
    boundary = build_lineage_closure_boundary(
        provider="composite", entity="publication", contract_ref="contract"
    )
    assert boundary["support_scope"] == "bounded_composite_rebuild_resume_debug"
    assert (
        boundary["reason"] == "composite_execution_outside_strict_exact_replay_boundary"
    )


def test_lineage_fragment_lookup_errors_name_missing_nodes() -> None:
    context = SimpleNamespace(run_id="run-1", provider="chembl", entity="publication")
    with pytest.raises(ValueError, match="Run node missing from gold"):
        _find_gold_run_node(nodes=[], run_context=context)
    with pytest.raises(ValueError, match="Gold dataset node missing"):
        _find_gold_dataset_node(nodes=[], table_name="gold/publication")
    with pytest.raises(ValueError, match="Run node missing from silver"):
        _find_silver_run_node(nodes=[], run_context=context)
    with pytest.raises(ValueError, match="Silver dataset node missing"):
        _find_silver_dataset_node(nodes=[], run_context=context, version_after=None)


@pytest.mark.asyncio
async def test_checkpoint_workflow_selects_manifest_and_run_lookup_paths() -> None:
    checkpoint = SimpleNamespace(run_id="run-1")
    checkpoint_service = SimpleNamespace(
        get_checkpoint_for_manifest_id=AsyncMock(return_value=checkpoint),
        get_checkpoint_for_run=AsyncMock(return_value=checkpoint),
    )
    audit = SimpleNamespace(inspect_run=AsyncMock(return_value=SimpleNamespace()))

    manifest_result = await inspect_checkpoint_workflow(
        audit_service=audit,
        checkpoint_service=checkpoint_service,
        run_manifest_service=None,
        pipeline_name="chembl_activity",
        run_id=None,
        manifest_id="manifest-1",
        audit_limit=5,
    )
    run_result = await inspect_checkpoint_workflow(
        audit_service=audit,
        checkpoint_service=checkpoint_service,
        run_manifest_service=None,
        pipeline_name="chembl_activity",
        run_id="run-1",
        manifest_id=None,
        audit_limit=5,
    )
    assert manifest_result.checkpoint is checkpoint
    assert run_result.checkpoint is checkpoint
