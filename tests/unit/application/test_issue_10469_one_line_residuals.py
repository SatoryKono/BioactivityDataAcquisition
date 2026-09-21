"""Behavior tests for one-line application coverage residuals in #10469."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from bioetl.application.composite._lifecycle_observer_span_management import (
    CompositeLifecycleSpanManagementMixin,
)
from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.join_execution import JoinExecutorService
from bioetl.application.composite.runner_pkg.runner_helpers import add_not_run_results
from bioetl.application.composite.runner_pkg.runner_stage_state_flow import (
    handle_seed_phase_exception,
)
from bioetl.application.core.postrun._service_collaborators import (
    resolve_postrun_collaborators,
)
from bioetl.application.core.postrun.service import PostrunService
from bioetl.application.core.record_normalization_finalization import (
    PreSilverRecord,
    finalize_pre_silver_record,
)
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.core.record_processor_config import (
    ContentHashPolicyByVersion,
    ContentHashVersionPolicy,
)
from bioetl.application.pipelines.common.base_publication_transformer import (
    BasePublicationTransformer,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.application.pipelines.pubmed.transformer import (
    PubMedPublicationTransformer,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayBulkCertificationResult,
    HistoricalReplayCertifiabilityInventory,
)
from bioetl.application.services.control_plane.replay.historical_universe_service import (
    HistoricalReplayUniverseClosureReportRecord,
    HistoricalReplayUniverseInventorySnapshot,
)
from bioetl.application.services.export_lineage.export_manifest_identity import utc_now
from bioetl.application.services.execution.pipeline_run_execution_service import (
    PipelineRunExecutionService,
)
from bioetl.application.services.lineage.lineage_inspection_helpers import (
    resolve_produced_nodes,
)
from bioetl.application.observability.control_plane_evidence.lineage import (
    _persistence_profile_check,
)
from bioetl.application.services.workflow.workflow_runner_service import (
    WorkflowRunnerService,
)
from bioetl.application.services.quality._quarantine_service_sync_support import (
    _run_traced_sync_operation,
)
from bioetl.application.services.quality.data_quality_anomalies import (
    DataQualityMetricsMixin,
)
from bioetl.application.services.quality.quarantine_service import QuarantineService
from bioetl.application.services.workflow._observability_workflow_models import (
    AuditRunWorkflowResult,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)


pytestmark = pytest.mark.unit


def test_close_span_safely_swallows_runtime_failure() -> None:
    span = MagicMock()
    span.set_attribute.side_effect = RuntimeError("closed")
    host = SimpleNamespace(tracer=None)

    CompositeLifecycleSpanManagementMixin._close_span_safely(
        host,
        span,
        status="failed",
        duration_seconds=0.1,
    )

    span.set_attribute.assert_called_once_with("bioetl.status", "failed")


def test_priority_order_logs_unparseable_seed_fallback() -> None:
    logger = MagicMock()
    service = ColumnOrderService(logger)

    ordered = service.order_columns_by_priority(
        field="title",
        columns=["legacyseed_title"],
        priorities=("seed",),
        seed_pipeline="legacyseed",
    )

    assert ordered == ["legacyseed_title"]
    logger.debug.assert_called_once()


@pytest.mark.asyncio
async def test_dependency_runner_method_delegates_to_timeout_guard() -> None:
    expected = object()
    dependency = object()
    keys = pl.DataFrame({"id": [1]})
    factory = MagicMock()
    with patch(
        "bioetl.application.composite.dependency_coordinator.execute_dependency_runner",
        new=AsyncMock(return_value=expected),
    ) as execute:
        result = await DependencyCoordinatorService._execute_dependency_runner(
            object(), dependency, keys, factory
        )

    assert result is expected
    execute.assert_awaited_once_with(
        dependency=dependency,
        keys=keys,
        runner_factory=factory,
    )


def test_composite_join_preserves_shared_right_key() -> None:
    service = JoinExecutorService(logger=MagicMock(), join_type_resolver=lambda: "left")
    left = pl.DataFrame({"id": [1], "kind": ["a"]})
    right = pl.DataFrame({"other_id": [1], "kind": ["a"], "value": [2]})

    joined = service.execute_composite_key_join(
        left,
        right,
        ["id", "kind"],
        ["other_id", "kind"],
        "dep",
    )

    assert joined["value"].to_list() == [2]


def test_add_not_run_results_skips_enricher_scheduled_to_run() -> None:
    results: dict[str, object] = {}
    enricher = SimpleNamespace(pipeline="optional", required=False)

    returned = add_not_run_results(
        results,
        enrichers_to_run=[enricher],
        all_enrichers=[enricher],
        completed_enrichers=frozenset(),
        required_only=True,
        composite_name="composite",
        logger=MagicMock(),
    )

    assert returned == {}


@pytest.mark.asyncio
async def test_seed_failure_labels_unexpected_bioetl_error() -> None:
    host = SimpleNamespace(
        _config=SimpleNamespace(
            name="composite",
            seed=SimpleNamespace(pipeline="seed_pipeline"),
        ),
        _run_id_str="run-1",
        _logger=MagicMock(),
        _persist_failed_state=AsyncMock(),
    )

    await handle_seed_phase_exception(host, object(), BioETLError("boom"))

    assert host._logger.error.call_args.kwargs["reason_code"] == (
        "unexpected_bioetl_error"
    )
    host._persist_failed_state.assert_awaited_once()


def test_postrun_collaborators_reject_missing_storage_and_logger() -> None:
    services = SimpleNamespace(
        storage=None,
        logger=None,
        metrics=MagicMock(),
        metadata_coordinator=None,
        metadata_writer=None,
    )
    with pytest.raises(AssertionError, match="storage and logger"):
        resolve_postrun_collaborators(
            services=services,
            context=SimpleNamespace(logger=None),
        )


def test_postrun_service_rejects_missing_dependencies_first() -> None:
    with pytest.raises(AssertionError, match="dependencies must be provided"):
        PostrunService(
            config=MagicMock(),
            runtime=MagicMock(),
            context=MagicMock(),
            dq_service=MagicMock(),
            lifecycle_service=MagicMock(),
            dependencies=None,
            services=MagicMock(),
        )


def test_pre_silver_finalization_stops_when_projection_drops_record() -> None:
    normalizer = SimpleNamespace(
        normalize_business_data=lambda value: value,
        compute_content_hashes_by_version=lambda _record: {},
        compute_content_hash=lambda _record: "hash",
        project_normalization_findings=lambda *_args, **_kwargs: None,
        _should_project_hashes_by_version=lambda: False,
        content_hash_policy_by_version=None,
    )
    record = PreSilverRecord(
        entity_id="entity:1",
        business_data={"value": 1},
        build_silver_record=lambda *_args: {"value": 1},
    )

    assert (
        finalize_pre_silver_record(
            normalizer,
            record,
            context=object(),
            index=0,
        )
        is None
    )


def test_pre_silver_structural_policy_can_drop_record() -> None:
    normalizer = SimpleNamespace(
        normalize_business_data=lambda value: value,
        compute_content_hashes_by_version=lambda _record: {},
        compute_content_hash=lambda _record: "hash",
        project_normalization_findings=lambda record, **_kwargs: record,
        _should_project_hashes_by_version=lambda: False,
        content_hash_policy_by_version=None,
    )
    record = PreSilverRecord(
        entity_id="entity:1",
        business_data={"value": 1},
        build_silver_record=lambda *_args: {"value": 1},
        apply_structural_policy=lambda *_args: None,
    )

    assert (
        finalize_pre_silver_record(normalizer, record, context=object(), index=0)
        is None
    )


def test_unknown_hash_datetime_policy_fails_closed() -> None:
    processor = RecordNormalizationProcessor(provider="crossref")
    invalid_policy = SimpleNamespace(datetime_policy="v3_local_time")
    with patch.object(
        RecordNormalizationProcessor,
        "_select_hash_policy",
        return_value=invalid_policy,
    ):
        with pytest.raises(ValueError, match="datetime policy"):
            processor._resolve_hash_policy(contract_version=None)


def test_normalize_record_projects_version_hashes_when_required() -> None:
    processor = RecordNormalizationProcessor(
        provider="crossref",
        content_hash_policy_by_version=ContentHashPolicyByVersion(
            active_version="1.0.0",
            affects_hash=True,
            policies=(
                ContentHashVersionPolicy(
                    version="1.0.0",
                    include_fields=frozenset({"title"}),
                    exclude_fields=frozenset(),
                ),
                ContentHashVersionPolicy(
                    version="2.0.0",
                    include_fields=frozenset({"title"}),
                    exclude_fields=frozenset(),
                ),
            ),
        ),
    )

    normalized = processor.normalize_record({"title": " Example "})

    assert set(normalized["_content_hashes_by_version"]) == {"1.0.0", "2.0.0"}


def test_publication_primary_id_field_delegates_to_provider_hook() -> None:
    host = SimpleNamespace(_get_primary_id_field=lambda: "publication_id")
    assert BasePublicationTransformer.get_primary_id_field(host) == "publication_id"


@pytest.mark.asyncio
async def test_pipeline_execution_derives_monotonic_anchor_from_started_at() -> None:
    clock = MagicMock()
    service = PipelineRunExecutionService(clock=clock)
    runner = SimpleNamespace(run=AsyncMock())
    started_at = datetime(2026, 9, 17, tzinfo=UTC)
    with (
        patch(
            "bioetl.application.services.execution.pipeline_run_execution_service."
            "capture_runtime_timing_anchor",
            return_value=(started_at, 10.0),
        ) as capture,
        patch(
            "bioetl.application.services.execution.pipeline_run_execution_service."
            "derive_completion_timestamp",
            return_value=(started_at, 0.0),
        ),
    ):
        result = await service.execute(
            runner=runner,
            run_logger=MagicMock(),
            metrics_extractor=SimpleNamespace(extract_metrics=lambda _runner: {}),
            started_at=started_at,
        )

    assert result.status == "success"
    capture.assert_called_once_with(clock=clock, started_at=started_at)


def test_resolve_produced_nodes_ignores_non_production_edges() -> None:
    source = LineageNodeRef(LineageNodeType.DATASET, "silver:1")
    target = LineageNodeRef(LineageNodeType.RUN, "run:1")
    fragment = LineageGraphFragment(
        fragment_id="fragment-1",
        nodes=(source, target),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.CONSUMED_BY,
                source=source,
                target=target,
            ),
        ),
    )

    assert (
        resolve_produced_nodes(
            fragments=(fragment,),
            node_type=LineageNodeType.DATASET,
        )
        == ()
    )


def test_lineage_persistence_profile_is_ok_with_complete_fragments() -> None:
    with patch(
        "bioetl.application.observability.control_plane_evidence.lineage."
        "resolve_persistence_profile",
        return_value=("replay_ready", True),
    ):
        result = _persistence_profile_check(
            MagicMock(),
            (MagicMock(),),
            validation_complete=True,
        )
    assert result.status == "OK"


@pytest.mark.asyncio
async def test_workflow_runner_skips_missing_topological_step() -> None:
    service = WorkflowRunnerService(
        pipeline_runner=MagicMock(),
        transform_service=MagicMock(),
        metrics=MagicMock(),
        report_store=MagicMock(),
    )
    config = SimpleNamespace(
        name="workflow",
        topological_step_ids=("missing",),
        get_step=lambda _step_id: None,
        workflow_context_labels={},
        defaults=SimpleNamespace(
            dry_run=False,
            debug_export_enabled=False,
            debug_export_dir=None,
        ),
    )
    final_result = object()
    with (
        patch.object(WorkflowRunnerService, "record_expected_pipeline_metrics"),
        patch(
            "bioetl.application.services.workflow.workflow_runner_service."
            "record_workflow_run_metrics"
        ),
        patch(
            "bioetl.application.services.workflow.workflow_runner_service."
            "workflow_result_from_state",
            return_value=object(),
        ),
        patch(
            "bioetl.application.services.workflow.workflow_runner_service.replace",
            return_value=final_result,
        ),
        patch(
            "bioetl.application.services.workflow.workflow_runner_service."
            "_require_workflow_result",
            return_value=final_result,
        ),
        patch(
            "bioetl.application.services.workflow.workflow_runner_service."
            "attach_workflow_run_report",
            return_value=final_result,
        ),
        patch(
            "bioetl.application.services.workflow.workflow_runner_service."
            "archive_workflow_children",
        ),
    ):
        result = await service.run_workflow(config)
    assert result is final_result


@pytest.mark.parametrize(
    ("transformer", "keyword"),
    [
        (PubMedPublicationTransformer, "unknown_pubmed_collaborator"),
    ],
)
def test_transformers_reject_unknown_legacy_collaborators(
    transformer: type[object], keyword: str
) -> None:
    with pytest.raises(TypeError, match="unexpected keyword"):
        transformer(**{keyword: object()})


def test_base_chembl_transformer_rejects_unknown_legacy_collaborator() -> None:
    class _ConcreteChemblTransformer(BaseChemblTransformer):
        def _extract_business_data(self, record: object) -> object:
            return record

    with pytest.raises(TypeError, match="unexpected keyword"):
        _ConcreteChemblTransformer(unknown_chembl_collaborator=object())


def test_empty_bulk_certification_result_serializes_counts() -> None:
    inventory = HistoricalReplayCertifiabilityInventory(records=())
    result = HistoricalReplayBulkCertificationResult(
        inventory_before=inventory,
        inventory_after=inventory,
        records=(),
    )

    assert result.to_dict()["completed_count"] == 0
    assert result.to_dict()["skipped_count"] == 0


def test_historical_universe_report_record_serializes_utc_time() -> None:
    record = HistoricalReplayUniverseClosureReportRecord(
        generated_at=datetime(2026, 9, 17, tzinfo=UTC),
        report_id="report-1",
        inventory=HistoricalReplayUniverseInventorySnapshot(records=()),
        authoritative_truth_surface={},
        universal_claim={},
        durable_evidence_coverage_claim={},
        governed_full_corpus_gate={},
    )

    assert record.to_dict()["generated_at"] == "2026-09-17T00:00:00+00:00"


def test_utc_now_returns_formatted_runtime_clock_value() -> None:
    value = utc_now()
    assert value.endswith("Z")


def test_quarantine_sync_without_tracer_executes_directly() -> None:
    anchor = (datetime(2026, 9, 17, tzinfo=UTC), 1.5)
    host = SimpleNamespace(
        tracer=None,
        _capture_operator_timing_anchor=lambda: anchor,
    )

    result = _run_traced_sync_operation(
        host,
        span_name="quarantine.test",
        operation="test",
        pipeline=None,
        trace_attributes={},
        execute=lambda started_at, monotonic: (started_at, monotonic),
        success_of=lambda _result: True,
        result_extra_of=lambda _result: {},
    )

    assert result == anchor


def test_dq_metrics_skip_baseline_lookup_without_monitor() -> None:
    host = SimpleNamespace(
        _metrics=MagicMock(),
        _pipeline_name="pipeline",
        _dq_monitor=None,
    )

    DataQualityMetricsMixin._update_baseline_metrics(host, {"rows": 2.0}, False)

    host._metrics.increment_counter.assert_called_once()


def test_quarantine_operator_metrics_are_optional() -> None:
    host = SimpleNamespace(metrics=None)
    QuarantineService._record_operator_metrics(
        host,
        operation="list",
        status="ok",
        duration_seconds=0.1,
    )
    assert host.metrics is None


def test_audit_workflow_result_serializes_absent_manifest() -> None:
    audit = MagicMock()
    audit.to_dict.return_value = {"status": "ok"}

    payload = AuditRunWorkflowResult(run_id="run-1", audit=audit).to_dict()

    assert payload == {
        "run_id": "run-1",
        "audit": {"status": "ok"},
        "run_manifest": None,
    }
