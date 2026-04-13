"""Cross-cutting reproducibility contract suite for exact replay diagnostics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import polars as pl
import pytest

from bioetl.application.composite.merger_metrics_mixin import MergeMetricsRecorderMixin
from bioetl.application.composite.runner_pkg.runner_observability_mixin import (
    CompositeRunnerObservabilityMixin,
)
from bioetl.application.services.effective_config_service import EffectiveConfigService
from bioetl.application.services.lineage import MetadataCoordinator
from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane import (
    RunLedgerEntry,
    RunArtifactRef,
    RunCodeProvenance,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.ports.metadata.coordinator import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
    SilverRef,
)
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.storage.silver.validation_operations import (
    _deduplicate_by_primary_keys_impl,
)


pytestmark = pytest.mark.integration

_VALID_CONFIG_HASH = "a" * 64


class _InMemoryRunManifestStore(RunManifestPort):
    def __init__(self) -> None:
        self._items: dict[str, RunManifest] = {}
        self._by_run_id: dict[str, str] = {}

    def save(self, manifest: RunManifest) -> None:
        self._items[manifest.manifest_id] = manifest
        self._by_run_id[str(manifest.run_id)] = manifest.manifest_id

    def get(self, manifest_id: str) -> RunManifest | None:
        return self._items.get(manifest_id)

    def get_by_run_id(self, run_id: RunID) -> RunManifest | None:
        manifest_id = self._by_run_id.get(str(run_id))
        return None if manifest_id is None else self._items.get(manifest_id)


class _InMemoryRunLedgerStore:
    def __init__(self) -> None:
        self._items: dict[str, list[RunLedgerEntry]] = {}

    def append(self, entry: RunLedgerEntry) -> None:
        self._items.setdefault(entry.manifest_id, []).append(entry)

    def list_entries(self, manifest_id: str) -> tuple[RunLedgerEntry, ...]:
        return tuple(self._items.get(manifest_id, ()))


def _make_merge_metrics_mixin() -> MergeMetricsRecorderMixin:
    mixin = MergeMetricsRecorderMixin.__new__(MergeMetricsRecorderMixin)
    mixin._logger = MagicMock()
    mixin._config = SimpleNamespace(exclude_fields=())
    return mixin


class _CompositeReplayHost(CompositeRunnerObservabilityMixin):
    def __init__(self) -> None:
        self._config = SimpleNamespace(
            name="publication",
            dq=SimpleNamespace(
                soft_fail_threshold=0.1,
                hard_fail_threshold=0.2,
            ),
            merge=SimpleNamespace(
                output_silver_path="silver/publication",
                output_gold_path="gold/publication",
            ),
        )
        self._logger = MagicMock()
        self._run_id = RunID(UUID("00000000-0000-0000-0000-000000000401"))
        self._run_id_str = str(self._run_id)
        self._runtime = SimpleNamespace(cached_bronze_date="2025-02-03")
        self._started_at = datetime(2025, 2, 5, 9, 30, tzinfo=UTC)
        self._dq_report_service = None
        self._quarantine_port = AsyncMock()
        self._metrics = None


def _make_manifest(
    *,
    manifest_id: str,
    run_id: RunID,
    execution_fingerprint: str,
    config_hash: str = _VALID_CONFIG_HASH,
) -> RunManifest:
    return RunManifest(
        manifest_id=manifest_id,
        execution_fingerprint=execution_fingerprint,
        schema_version="1.0",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"limit": 25, "exact_replay": True},
        runtime_config={
            "run_type": "incremental",
            "limit": 25,
            "exact_replay": True,
        },
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash=config_hash,
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            dq_policy_ref="chembl.activity.dq",
            rule_bundle_version="dq-rules.v1",
            dq_contract_compatibility_hash="compat-hash-1",
            effective_config_artifact_id="eca-123",
        ),
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query="fixture://sample",
            ),
        ),
        planned_artifacts=(RunArtifactRef(layer="silver", path="/tmp/output"),),
    )


def test_reproducibility_contract_manifest_diff_classifies_occurrence_only() -> None:
    store = _InMemoryRunManifestStore()
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000301")),
        execution_fingerprint="fp-stable",
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000302")),
        execution_fingerprint="fp-stable",
    )
    store.save(left)
    store.save(right)

    result = RunManifestInspectionService(manifest_port=store).diff(
        "manifest-left",
        "manifest-right",
    )

    assert result.classification == "occurrence_only"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is True
    assert result.occurrence_difference_fields == ("manifest_id", "run_id")


def test_reproducibility_contract_manifest_diff_classifies_semantic_drift() -> None:
    store = _InMemoryRunManifestStore()
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000303")),
        execution_fingerprint="fp-left",
        config_hash="hash-left",
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000304")),
        execution_fingerprint="fp-right",
        config_hash="hash-right",
    )
    store.save(left)
    store.save(right)

    result = RunManifestInspectionService(manifest_port=store).diff(
        "manifest-left",
        "manifest-right",
    )

    assert result.classification == "semantic_drift"
    assert result.semantic_equivalent is False
    assert "code_provenance" in result.semantic_difference_fields


def test_reproducibility_contract_effective_config_semantic_payload_is_stable() -> None:
    service = EffectiveConfigService()
    dq_config = DQConfig(
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        rule_bundle_version="dq-rules.v1",
        default_disposition_policy=DQDisposition.WARN,
    )
    kwargs = dict(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        runtime_overrides={"cli": {"limit": 25}},
        source_refs=[
            ConfigSourceRef(
                source_type="fixture",
                source_path="tests/fixtures/bronze/chembl/activity/sample.jsonl",
                source_hash="fixture-hash-1",
                priority=1,
            )
        ],
        dq_config=dq_config,
        artifact_id="eca-stable",
    )
    first = service.create_effective_config_artifact(**kwargs)
    second = service.create_effective_config_artifact(**kwargs)

    assert service.serialize_semantic_artifact(first) == service.serialize_semantic_artifact(
        second
    )
    assert first.effective_config_hash == second.effective_config_hash


def test_reproducibility_contract_bronze_bundle_has_canonical_artifact_identity() -> None:
    started_at = datetime(2025, 1, 1, tzinfo=UTC)
    context = RunContext.create(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=started_at,
        provider="chembl",
        entity="activity",
    )
    coordinator = MetadataCoordinator(context)
    bundle = coordinator.create_bronze_metadata_bundle(
        BronzeMetadataInput(
            batch_id=BatchID("batch-1"),
            record_count=2,
            compressed_size=128,
            output_path="v1/chembl/activity/2025-01-01/batch-1.jsonl.zst",
            started_at=started_at,
            completed_at=started_at + timedelta(seconds=1),
        )
    )

    assert bundle.metadata.output.artifact_id == "bronze_batch:batch-1"
    assert bundle.metadata.output.lineage_fragment_id == bundle.lineage_fragment.fragment_id


def test_reproducibility_contract_silver_bundle_keeps_sidecar_and_fragment_identity_aligned() -> None:
    started_at = datetime(2025, 1, 1, tzinfo=UTC)
    context = RunContext.create(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=started_at,
        provider="chembl",
        entity="activity",
    )
    coordinator = MetadataCoordinator(context)

    bundle = coordinator.create_silver_metadata_bundle(
        SilverMetadataInput(
            table_path="silver/chembl/activity",
            primary_keys=["activity_id"],
            mode=SilverWriteMode.MERGE,
            records=[
                {"activity_id": 1, "_source_batch_id": "batch-a"},
                {"activity_id": 2, "_source_batch_id": "batch-b"},
            ],
            version_after=4,
            started_at=started_at,
            completed_at=started_at + timedelta(seconds=2),
        )
    )

    assert bundle.metadata.output.artifact_id == "silver:chembl.activity@4"
    assert bundle.metadata.output.lineage_fragment_id == bundle.lineage_fragment.fragment_id
    assert any(
        node.node_id == bundle.metadata.output.artifact_id
        for node in bundle.lineage_fragment.nodes
    )


def test_reproducibility_contract_gold_bundle_keeps_sidecar_and_fragment_identity_aligned() -> None:
    started_at = datetime(2025, 1, 1, tzinfo=UTC)
    context = RunContext.create(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=started_at,
        provider="chembl",
        entity="activity",
    )
    coordinator = MetadataCoordinator(context)

    bundle = coordinator.create_gold_metadata_bundle(
        GoldMetadataInput(
            table_path="gold/chembl/activity",
            table_name="chembl.activity",
            mode=GoldWriteMode.OVERWRITE,
            records=[{"activity_id": 1}],
            silver_refs=[
                SilverRef(
                    table_name="chembl.activity",
                    table_path="silver/chembl/activity",
                    delta_version=4,
                )
            ],
            started_at=started_at,
            completed_at=started_at + timedelta(seconds=3),
        )
    )

    assert bundle.metadata.output.artifact_id == "gold:chembl.activity"
    assert bundle.metadata.output.lineage_fragment_id == bundle.lineage_fragment.fragment_id
    assert any(
        node.node_id == bundle.metadata.output.artifact_id
        for node in bundle.lineage_fragment.nodes
    )


def test_reproducibility_contract_supported_gold_trace_path_resolves_run_context() -> None:
    started_at = datetime(2025, 1, 1, tzinfo=UTC)
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000411"))
    context = RunContext.create(
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        started_at=started_at,
        provider="chembl",
        entity="activity",
    )
    coordinator = MetadataCoordinator(context)
    bundle = coordinator.create_gold_metadata_bundle(
        GoldMetadataInput(
            table_path="gold/chembl/activity",
            table_name="chembl.activity",
            mode=GoldWriteMode.OVERWRITE,
            records=[{"activity_id": 1}],
            silver_refs=[
                SilverRef(
                    table_name="chembl.activity",
                    table_path="silver/chembl/activity",
                    delta_version=4,
                )
            ],
            started_at=started_at,
            completed_at=started_at + timedelta(seconds=3),
        )
    )

    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    manifest = _make_manifest(
        manifest_id="manifest-gold-trace-1",
        run_id=run_id,
        execution_fingerprint="fp-gold-trace-1",
    )
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-gold-trace-1",
            manifest_id=manifest.manifest_id,
            run_id=run_id,
            event_type="artifact_published",
            occurred_at=started_at + timedelta(seconds=4),
            event_family="artifact",
            status="success",
            stage="gold",
            dataset_ref=bundle.metadata.output.artifact_id,
            lineage_fragment_id=bundle.metadata.output.lineage_fragment_id,
            details={
                "artifact_path": "gold/chembl/activity",
                "metadata_path": "gold/chembl/activity/chembl_activity_metadata.yaml",
                "artifact_kind": "metadata_sidecar",
                "pipeline_name": "chembl_activity",
                "provider": "chembl",
                "entity": "activity",
                "run_id": str(run_id),
                "manifest_id": manifest.manifest_id,
            },
        )
    )

    result = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    ).show(manifest.manifest_id)

    assert result.diagnostics["artifact_refs"] == [
        {
            "event_type": "artifact_published",
            "stage": "gold",
            "artifact_id": "gold:chembl.activity",
            "dataset_ref": "gold:chembl.activity",
            "lineage_fragment_id": bundle.metadata.output.lineage_fragment_id,
            "artifact_path": "gold/chembl/activity",
            "metadata_path": "gold/chembl/activity/chembl_activity_metadata.yaml",
            "artifact_kind": "metadata_sidecar",
            "pipeline_name": "chembl_activity",
            "provider": "chembl",
            "entity": "activity",
            "run_id": str(run_id),
            "manifest_id": manifest.manifest_id,
        }
    ]
    assert result.diagnostics["lineage_fragment_ids"] == [
        bundle.metadata.output.lineage_fragment_id
    ]
    assert result.manifest.run_id == run_id
    assert result.manifest.manifest_id == "manifest-gold-trace-1"


def test_reproducibility_contract_silver_batch_dedup_is_order_insensitive() -> None:
    forward = [
        {"id": "1", "value": "winner", "content_hash": "a-hash"},
        {"id": "1", "value": "loser", "content_hash": "z-hash"},
    ]
    reverse = list(reversed(forward))

    assert _deduplicate_by_primary_keys_impl(forward, ["id"]) == [
        {"id": "1", "value": "winner", "content_hash": "a-hash"}
    ]


def test_reproducibility_contract_composite_rows_exclude_runtime_anchors() -> None:
    mixin = _make_merge_metrics_mixin()
    df = pl.DataFrame({"doi": ["10.1/a"]})
    metadata_timestamp = datetime(2025, 2, 3, 0, 0, tzinfo=UTC)

    first = mixin._add_lineage(
        df,
        enrichment_results={},
        run_id="run-left",
        metadata_timestamp=metadata_timestamp,
        sources_used=["seed"],
    )
    second = mixin._add_lineage(
        df,
        enrichment_results={},
        run_id="run-right",
        metadata_timestamp=metadata_timestamp,
        sources_used=["seed"],
    )

    assert "_composite_run_id" not in first.columns
    assert "_lineage_created_at" not in first.columns
    assert first.columns == second.columns


@pytest.mark.asyncio
async def test_reproducibility_contract_composite_quarantine_replay_anchor_is_deterministic() -> None:
    host = _CompositeReplayHost()

    await host._write_cv_quarantine(
        MergeResult(quarantine_payloads=({"id": "cv-1"},))
    )

    host._quarantine_port.write.assert_awaited_once()
    write_kwargs = host._quarantine_port.write.await_args.kwargs
    assert write_kwargs["pipeline"] == "composite:publication"
    assert write_kwargs["ingestion_ts"] == datetime(2025, 2, 3, 0, 0, tzinfo=UTC)
    assert write_kwargs["metadata"]["artifact_policy"] == "occurrence_only_diagnostic"
    assert (
        write_kwargs["metadata"]["replay_contract"] == "excluded_from_exact_replay"
    )


def test_reproducibility_contract_composite_quarantine_is_explicitly_occurrence_only() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000402"))
    manifest = _make_manifest(
        manifest_id="manifest-composite-quarantine",
        run_id=run_id,
        execution_fingerprint="fp-stable",
    )
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-composite-cv-1",
            manifest_id=manifest.manifest_id,
            run_id=run_id,
            event_type="dq_policy_applied",
            occurred_at=datetime(2025, 2, 3, tzinfo=UTC),
            event_family="dq",
            status="quarantined",
            stage="cross_validation",
            details={
                "rule_id": "composite.cross_validation.quarantine",
                "disposition": "quarantine",
                "violation_kind": "cross_validation_mismatch",
                "config_path": "cross_validation",
                "artifact_policy": "occurrence_only_diagnostic",
                "replay_contract": "excluded_from_exact_replay",
                "diagnostic_scope": "composite_cross_validation_quarantine",
            },
        )
    )

    result = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    ).show(manifest.manifest_id)

    assert (
        result.diagnostics["cross_validation_quarantine_policy"]
        == "occurrence_only_diagnostic"
    )
    assert (
        result.diagnostics["cross_validation_quarantine_replay_contract"]
        == "excluded_from_exact_replay"
    )
    assert result.diagnostics["occurrence_only_diagnostics"] == [
        "composite_cross_validation_quarantine"
    ]
    assert result.identity_graph["occurrence_only_diagnostics"] == [
        "composite_cross_validation_quarantine"
    ]
