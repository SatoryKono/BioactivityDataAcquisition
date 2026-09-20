"""Stream A leftover L12 application residuals for #10469 / #10516."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.runner_pkg import runner as composite_runner_mod
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.config import LockConfig
from bioetl.application.core.lifecycle.lock_lifecycle import acquire_lock, release_lock
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.core.postrun._phase_descriptions import (
    describe_compaction_phase,
)
from bioetl.application.core.postrun.compact_orchestrator import (
    CompactionResult,
    PostrunCompactService,
)
from bioetl.application.core.postrun.metadata_write_service import (
    PostrunMetadataWriteService,
)
from bioetl.application.core.runner_flow_metrics import _monotonic_invariant_status
from bioetl.application.observability.control_plane_evidence.manifest_validation import (
    _raw_manifest_checks,
)
from bioetl.application.observability import current_metrics_rehydrate as rehydrate
from bioetl.application.pipelines.pubchem._compound_business_data import (
    _resolve_compound_identifier,
)
from bioetl.application.pipelines.uniprot.idmapping_transformer import (
    IDMappingTransformer,
)
from bioetl.application.services.control_plane.ledger.core_events import (
    record_manifest_created,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profile_support import (
    build_forensic_grade_missing_requirements,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profiles import (
    resolve_required_profile_requirements,
)
from bioetl.application.services.control_plane.manifest.validation import (
    _is_explicit_degraded_profile_opt_down,
)
from bioetl.application.services.dq._checks_business import _normalize_business_rule
from bioetl.application.services.lineage._metadata_coordinator_helpers import (
    _merge_input_snapshots,
)
from bioetl.application.services.lineage.metadata_lineage_dataset_nodes import (
    _canonical_bronze_batch_node,
)
from bioetl.application.services.medallion.medallion_lifecycle import (
    MedallionLifecycleService,
)
from bioetl.application.services.quality.dq_report_generation_mixin import (
    DQReportGenerationMixin,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
)
from bioetl.application.services.workflow.workflow_runner_reports import (
    _plan_steps_from_config,
)
from bioetl.application.services.workflow.workflow_transform_service import (
    WorkflowTransformService,
)
from bioetl.application.workflow.transforms import (
    WorkflowTransformRegistry,
    WorkflowTransformRuntimeContext,
)
from bioetl.domain.locking import FencingToken, LockContextHolder
from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import InputSnapshotRef, SourceMetadata
from bioetl.domain.ports.control_plane.run_manifest import RawManifestInspection
from bioetl.domain.types import GoldBusinessRuleSpec, RunID
from bioetl.domain.workflow import TransformStepConfig
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies
from tests.unit.application.composite.test_runner import create_runner


pytestmark = pytest.mark.unit

_TEST_RUN_ID = RunID(UUID("12345678-1234-5678-1234-567812345678"))


def test_column_renamer_treats_identity_columns_as_system() -> None:
    renamer = ColumnRenamer(MagicMock())
    assert renamer._is_system_column("entity_id") is True
    assert renamer._is_system_column("content_hash") is True


def test_composite_runner_exposes_config_and_emits_failed_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = create_runner()
    assert runner.config is runner._config
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        composite_runner_mod,
        "emit_failed_run",
        lambda host, error, **kwargs: captured.update({"error": error, **kwargs}),
    )
    runner._emit_failed_run(RuntimeError("boom"), reason_code="failed", stage="run")
    assert captured["reason_code"] == "failed"
    assert captured["stage"] == "run"


def test_batch_writer_track_batch_failed_delegates_to_metrics() -> None:
    config = MagicMock()
    config.provider = "chembl"
    config.entity_type = "activity"
    config.silver_schema = None
    config.gold_schema = None
    config.gold_schema_policy_by_version = {}
    config.column_groups = None
    config.data_schema = None
    config.table_config.silver_table = "silver"
    config.table_config.gold_table = "gold"
    config.table_config.silver_write_mode = "append"
    config.table_config.gold_write_mode = "overwrite"
    metrics = MagicMock()
    writer = BatchWriter(
        MagicMock(),
        MagicMock(),
        config,
        MagicMock(),
        MagicMock(),
        metrics,
    )
    writer.track_batch_failed(stage="gold", count=3)
    metrics.track_batch_failed.assert_called_once_with(stage="gold", count=3)


@pytest.mark.asyncio
async def test_lock_lifecycle_sets_and_clears_context_holder() -> None:
    token = FencingToken(
        sequence=1, key="lock:test", owner_id=_TEST_RUN_ID, issued_at=1.0
    )
    holder = MagicMock(spec=LockContextHolder)
    lock = AsyncMock()
    lock.acquire.return_value = token
    host = SimpleNamespace(
        _lock=lock,
        _config=LockConfig(lock_key="lock:test"),
        _run_id=_TEST_RUN_ID,
        _context_holder=holder,
        _logger=MagicMock(),
        _heartbeat_factory=lambda **_kwargs: MagicMock(),
        _shutdown_signal=MagicMock(),
        _heartbeat=None,
        _acquired_at=None,
        _fencing_token=None,
        get_context=lambda: MagicMock(),
    )
    acquired = await acquire_lock(host)  # type: ignore[arg-type]
    assert acquired is token
    holder.set.assert_called_once()
    await release_lock(host)  # type: ignore[arg-type]
    holder.clear.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_services_aclose_closes_metadata_writer() -> None:
    metadata_writer = AsyncMock()
    services = PipelineService(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=MagicMock(),
        metadata_writer=metadata_writer,
    )
    await services.aclose()
    metadata_writer.aclose.assert_awaited_once()


def test_compaction_phase_includes_error_attribute() -> None:
    described = describe_compaction_phase(
        CompactionResult(status="failed", error="optimize failed")
    )
    assert described.span_attributes["bioetl.compaction_error"] == "optimize failed"


@pytest.mark.asyncio
async def test_compact_orchestrator_logs_optimize_allowlist_failure() -> None:
    config = MagicMock()
    config.table.silver_write_mode = SilverWriteMode.APPEND
    config.table.primary_keys = ("activity_id",)
    config.effective_silver_table = "chembl/activity"
    storage = MagicMock()
    storage.deduplicate_silver = AsyncMock(return_value=2)
    storage.optimize = AsyncMock(side_effect=RuntimeError("opt boom"))
    logger = MagicMock()
    service = PostrunCompactService(
        config=config,
        storage=storage,
        logger=logger,
        warning_allowlist=(RuntimeError,),
    )
    result = await service.run_if_needed()
    assert result.status == "success"
    logger.warning.assert_called_once()
    assert logger.warning.call_args.args[0] == "silver_optimize_failed"


@pytest.mark.asyncio
async def test_metadata_write_returns_false_when_no_coroutines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = PostrunMetadataWriteService(
        config=MagicMock(),
        runtime=MagicMock(),
        context=MagicMock(),
        storage=MagicMock(),
        metadata_coordinator=None,
        metadata_writer=MagicMock(),
        metadata_version_resolver=MagicMock(),
    )
    monkeypatch.setattr(service, "_build_write_coroutines", lambda **_kwargs: [])
    assert await service.write_final_metadata_if_available(MagicMock(), None) is False


def test_monotonic_invariant_status_unknown_when_unobserved() -> None:
    assert _monotonic_invariant_status(upper=4, lower=1, observed=False) == "unknown"


def test_raw_manifest_checks_parse_error_uses_schema_error_or_fallback() -> None:
    with_reason = _raw_manifest_checks(
        RawManifestInspection(parse_ok=False, schema_errors=("bad json",))
    )
    assert with_reason[0].status == "ERROR"
    assert with_reason[0].reason == "bad json"
    fallback = _raw_manifest_checks(RawManifestInspection(parse_ok=False))
    assert fallback[0].reason == "manifest_parse_error"


def test_rehydrate_collect_skips_unparseable_anchors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rehydrate, "list_pipeline_reports", lambda **_kwargs: [object()]
    )
    monkeypatch.setattr(rehydrate, "_anchor_from_report_entry", lambda *_a, **_k: None)
    assert rehydrate.collect_latest_terminal_anchors(store=MagicMock()) == ()

    monkeypatch.setattr(
        rehydrate, "list_workflow_reports", lambda **_kwargs: [object()]
    )
    monkeypatch.setattr(rehydrate, "anchor_from_workflow_entry", lambda *_a, **_k: None)
    assert rehydrate.collect_latest_terminal_workflow_anchors(store=MagicMock()) == ()


def test_pubchem_compound_identifier_prefers_cid() -> None:
    assert _resolve_compound_identifier({"cid": 2244, "molecule_id": "skip"}) == 2244


def test_idmapping_transformer_marks_multiple_mappings() -> None:
    transformer = IDMappingTransformer(
        provider="uniprot",
        entity_type="idmapping",
        dependencies=build_test_transformer_dependencies(),
    )
    target_id, payload = transformer._build_mapping_business_data(
        {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
            "all_mappings": ["P00742", "P00743"],
        }
    )
    assert target_id == "CHEMBL204"
    assert payload["mapping_status"] == "multiple"


def test_record_manifest_created_rejects_run_id_mismatch() -> None:
    appender = SimpleNamespace(manifest_id="manifest-1", run_id="run-a")
    manifest = SimpleNamespace(manifest_id="manifest-1", run_id="run-b")
    with pytest.raises(ValueError, match="run_id must match"):
        record_manifest_created(appender, manifest)  # type: ignore[arg-type]


def test_forensic_grade_missing_includes_lineage_closure_gap() -> None:
    missing = build_forensic_grade_missing_requirements(
        replay_ready_missing_requirements=[],
        ledger_entries_present=True,
        artifact_lineage_links_complete=True,
        lineage_closure_boundary_supported=False,
        composite_resume_rich_replay_supported=True,
    )
    assert missing == ["lineage_closure_boundary_support"]


def test_required_profile_requirements_forensic_grade() -> None:
    profile, missing = resolve_required_profile_requirements(
        required_profile="forensic_grade",
        replay_ready_missing_requirements=["replay"],
        forensic_grade_missing_requirements=["forensic"],
    )
    assert profile == "forensic_grade"
    assert missing == ["forensic"]


def test_explicit_degraded_opt_down_rejects_exact_replay() -> None:
    request = SimpleNamespace(launch_context={"exact_replay": True})
    assert _is_explicit_degraded_profile_opt_down(request) is False  # type: ignore[arg-type]


def test_normalize_business_rule_keeps_typed_spec() -> None:
    rule = GoldBusinessRuleSpec(column="activity_id", condition="not_null")
    assert _normalize_business_rule(rule, contract_version=None) is rule


def test_merge_input_snapshots_skips_duplicate_identities() -> None:
    snapshot = InputSnapshotRef(snapshot_id="snap-1", content_hash="abc")
    source = SourceMetadata(type="api", input_snapshots=[snapshot])
    merged = _merge_input_snapshots(source=source, input_snapshots=(snapshot,))
    assert merged == [snapshot]


def test_bronze_batch_node_skips_identity_and_none_extras() -> None:
    node = _canonical_bronze_batch_node(
        batch_id="batch-1",
        provider="chembl",
        entity="activity",
        extra={"provider": "other", "output_path": None, "ok": "keep"},
    )
    assert node.attributes["provider"] == "chembl"
    assert "output_path" not in node.attributes
    assert node.attributes["ok"] == "keep"


@pytest.mark.asyncio
async def test_medallion_optimize_skips_duplicate_gold_table() -> None:
    storage = AsyncMock()
    storage.vacuum.return_value = 4
    service = MedallionLifecycleService(storage=storage, logger=MagicMock())
    removed = await service._optimize_tables("shared", "shared", 24, False)
    assert removed == (4, 0)
    storage.vacuum.assert_awaited_once()


def test_dq_check_failure_metric_is_noop_without_metrics() -> None:
    host = DQReportGenerationMixin()
    host._metrics = None
    assert (
        host._emit_dq_check_failure_metric(
            pipeline="chembl_activity",
            stage="gold",
            check_type="not_null",
            severity="error",
        )
        is None
    )


def test_workflow_run_result_is_success_property() -> None:
    result = WorkflowRunExecutionResult(workflow_name="wf", status="success", steps=())
    assert result.is_success is True


def test_plan_steps_skips_missing_step_ids() -> None:
    config = MagicMock()
    config.topological_step_ids = ("missing",)
    config.get_step.return_value = None
    assert _plan_steps_from_config(config) == []


@pytest.mark.asyncio
async def test_workflow_transform_awaits_async_executor() -> None:
    async def _async_transform(spec: object, upstream: object) -> dict[str, str]:
        return {"status": "awaited"}

    registry = WorkflowTransformRegistry()
    registry.register("async_normalize", _async_transform)
    service = WorkflowTransformService(
        registry=registry,
        metrics=MagicMock(),
        monotonic=iter([1.0, 1.5]).__next__,
    )
    result = await service.run_step(
        workflow_name="wf",
        step=TransformStepConfig(step_id="t1", transform_name="async_normalize"),
    )
    assert result.status == "success"
    assert result.output == {"status": "awaited"}


def test_destructive_commit_is_noop_without_callback() -> None:
    context = WorkflowTransformRuntimeContext()
    assert (
        context.record_destructive_commit(
            step_id="t1",
            transform_name="normalize",
            fingerprint="fp",
            details={},
        )
        is None
    )
