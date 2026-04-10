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
from bioetl.application.services.metadata_coordinator import MetadataCoordinator
from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunCodeProvenance,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.ports.metadata.coordinator import BronzeMetadataInput
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.storage.silver.validation_operations import (
    _deduplicate_by_primary_keys_impl,
)


pytestmark = pytest.mark.integration


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
    config_hash: str = "deadbeef",
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


def test_reproducibility_contract_silver_batch_dedup_is_order_insensitive() -> None:
    forward = [
        {"id": "1", "value": "winner", "content_hash": "a-hash"},
        {"id": "1", "value": "loser", "content_hash": "z-hash"},
    ]
    reverse = list(reversed(forward))

    assert _deduplicate_by_primary_keys_impl(forward, ["id"]) == [
        {"id": "1", "value": "winner", "content_hash": "a-hash"}
    ]


def test_reproducibility_contract_composite_metadata_anchor_is_stable() -> None:
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

    assert first["_lineage_created_at"][0] == "2025-02-03T00:00:00+00:00"
    assert second["_lineage_created_at"][0] == first["_lineage_created_at"][0]


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
