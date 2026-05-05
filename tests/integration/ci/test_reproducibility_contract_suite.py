"""Cross-cutting reproducibility contract suite for exact replay diagnostics."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import polars as pl
import pytest

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.application.composite.merger_metrics_mixin import MergeMetricsRecorderMixin
from bioetl.application.composite.runner_pkg.runner_observability_mixin import (
    CompositeRunnerObservabilityMixin,
)
from bioetl.application.services.effective_config_service import EffectiveConfigService
from bioetl.application.services.lineage import MetadataCoordinator
from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.composition.bootstrap.runtime.composite_control_plane_builder import (
    build_composite_control_plane_bundle,
)
from bioetl.composition.bootstrap.runtime.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.domain.composite.config import (
    CompositeConfig,
    DependencyConfig,
    EnricherConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunLedgerEntry,
    RunArtifactRef,
    RunCodeProvenance,
    RunManifest,
    RunInputSnapshotRef,
    RunSourceRef,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    published_production_reproducibility_families,
    published_reproducibility_family_inventory,
    published_supported_reproducibility_families,
)
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.domain.lineage import (
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from tests.helpers.control_plane import InMemoryRunManifestStore
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
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.config import Settings


pytestmark = pytest.mark.integration

_VALID_CONFIG_HASH = "a" * 64
_PUBLISHED_SUPPORTED_FAMILIES = tuple(published_supported_reproducibility_families())
_PUBLISHED_PRODUCTION_FAMILIES = tuple(published_production_reproducibility_families())


@dataclass(frozen=True)
class _ManifestIdentity:
    pipeline_name: str = "chembl_activity"
    provider: str = "chembl"
    entity: str = "activity"
    contract_ref: str = "chembl.activity"


_DEFAULT_MANIFEST_IDENTITY = _ManifestIdentity()


_InMemoryRunManifestStore = InMemoryRunManifestStore


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


def _build_replay_matrix_composite_config() -> CompositeConfig:
    """Build a canonical composite config for full-envelope exact replay evidence."""
    return CompositeConfig(
        name="composite_publication",
        version="1.0.0",
        seed=SeedConfig(
            pipeline="pubmed_publication",
            output_keys=("publication_id",),
            silver_table="publication",
        ),
        dependencies=(
            DependencyConfig(
                pipeline="crossref_publication",
                join_keys=("publication_id",),
                silver_table="publication",
            ),
        ),
        enrichers=(
            EnricherConfig(
                pipeline="openalex_publication",
                join_keys=("publication_id",),
                silver_table="publication",
            ),
        ),
        merge=MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="data/output/silver/composite/publication",
            output_gold_path="data/output/gold/composite/publication",
        ),
    )


def _write_composite_snapshot_envelope(bronze_root: Path) -> None:
    """Materialize seed/dependency/enricher cached-Bronze files for replay tests."""
    for provider, entity in (
        ("pubmed", "publication"),
        ("crossref", "publication"),
        ("openalex", "publication"),
    ):
        bronze_day = bronze_root / provider / entity / "2026-01-01"
        bronze_day.mkdir(parents=True, exist_ok=True)
        (bronze_day / f"batch_{provider}_{entity}.jsonl.zst").write_bytes(
            f"{provider}:{entity}:snapshot".encode()
        )


def _load_manifest_payload(data_dir: Path, manifest_id: str) -> dict[str, object]:
    manifest_path = (
        data_dir / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _make_manifest(
    *,
    manifest_id: str,
    run_id: RunID,
    execution_fingerprint: str,
    config_hash: str = _VALID_CONFIG_HASH,
    replay_of_run_id: str | None = None,
    replay_of_manifest_id: str | None = None,
    required_persistence_profile: str = "degraded_observable",
    input_snapshots: tuple[RunInputSnapshotRef, ...] = (),
    identity: _ManifestIdentity = _DEFAULT_MANIFEST_IDENTITY,
    exact_replay: bool = True,
    execution_context: str = "ordinary",
) -> RunManifest:
    is_composite = execution_context == "composite" or identity.provider == "composite"
    replay_capability = (
        ReplayCapability.REBUILD_ONLY
        if not input_snapshots
        else ReplayCapability.EXACT_REPLAY_SUPPORTED
    )
    return RunManifest(
        manifest_id=manifest_id,
        execution_fingerprint=execution_fingerprint,
        schema_version="1.0",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name=identity.pipeline_name,
        provider=identity.provider,
        entity=identity.entity,
        launch_context={
            "limit": 25,
            "exact_replay": exact_replay,
            "execution_context": execution_context,
            "required_persistence_profile": required_persistence_profile,
        },
        runtime_config={
            "run_type": "incremental",
            "limit": 25,
            "exact_replay": exact_replay,
            "execution_context": execution_context,
            "required_persistence_profile": required_persistence_profile,
        },
        resolved_config={
            "provider": identity.provider,
            "entity_type": identity.entity,
        },
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        replay_capability=replay_capability,
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            source_revision_state="clean",
            config_hash=config_hash,
            resolved_config_hash="b" * 64,
            effective_config_hash="c" * 64,
            contract_ref=identity.contract_ref,
            contract_version="1.0.0",
            contract_schema_hash="schema-hash-1",
            dq_policy_ref=f"{identity.contract_ref}.dq",
            rule_bundle_version="dq-rules.v1",
            dq_contract_compatibility_hash="compat-hash-1",
            effective_config_artifact_id="eca-123",
        ),
        source_refs=(
            RunSourceRef(
                provider=identity.provider,
                entity=identity.entity,
                pipeline_name=identity.pipeline_name,
                query="fixture://sample",
                input_snapshots=input_snapshots,
            ),
        ),
        planned_artifacts=(RunArtifactRef(layer="silver", path="test-output/silver"),),
    )


def _family_context(family: str) -> tuple[str, str, str]:
    provider, entity = family.split(".", maxsplit=1)
    return provider, entity, f"{provider}_{entity}"


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


def test_reproducibility_contract_manifest_diff_treats_created_at_as_occurrence_only() -> (
    None
):
    store = _InMemoryRunManifestStore()
    left = _make_manifest(
        manifest_id="manifest-left-created-at",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000316")),
        execution_fingerprint="fp-created-at-stable",
    )
    right = replace(
        left,
        manifest_id="manifest-right-created-at",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000317")),
        created_at=datetime(2025, 1, 2, tzinfo=UTC),
    )
    store.save(left)
    store.save(right)

    result = RunManifestInspectionService(manifest_port=store).diff(
        "manifest-left-created-at",
        "manifest-right-created-at",
    )

    assert result.classification == "occurrence_only"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is True
    assert result.occurrence_difference_fields == (
        "created_at",
        "manifest_id",
        "run_id",
    )


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


def test_reproducibility_contract_manifest_diff_exposes_exact_replay_parentage() -> (
    None
):
    store = _InMemoryRunManifestStore()
    parent_run_id = RunID(UUID("00000000-0000-0000-0000-000000000305"))
    child_run_id = RunID(UUID("00000000-0000-0000-0000-000000000306"))
    parent = _make_manifest(
        manifest_id="manifest-parent",
        run_id=parent_run_id,
        execution_fingerprint="fp-stable",
    )
    child = _make_manifest(
        manifest_id="manifest-child",
        run_id=child_run_id,
        execution_fingerprint="fp-stable",
        replay_of_run_id=str(parent_run_id),
        replay_of_manifest_id="manifest-parent",
    )
    store.save(parent)
    store.save(child)

    result = RunManifestInspectionService(manifest_port=store).diff(
        "manifest-parent",
        "manifest-child",
    )

    assert result.classification == "semantic_equivalent_with_noncanonical_differences"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is False
    assert result.replay_relationship == "right_is_exact_replay_of_left"
    assert "replay_of_manifest_id" in result.noncanonical_difference_fields


def test_reproducibility_contract_lineage_store_preserves_occurrence_history(
    tmp_path: Path,
) -> None:
    store = FileLineageStore(base_path=tmp_path / "control" / "lineage")
    semantic_fragment_id = "silver:chembl.activity@4"
    node = LineageNodeRef(
        node_type=LineageNodeType.DATASET,
        node_id=semantic_fragment_id,
    )
    first = LineageGraphFragment(
        fragment_id=semantic_fragment_id,
        nodes=(node,),
        run_id="00000000-0000-0000-0000-000000000901",
        manifest_id="manifest-first",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    second = replace(
        first,
        run_id="00000000-0000-0000-0000-000000000902",
        manifest_id="manifest-second",
    )

    store.save(first)
    store.save(second)

    first_loaded = store.list_by_run_id(RunID(UUID(first.run_id or "")))
    second_loaded = store.list_by_run_id(RunID(UUID(second.run_id or "")))

    assert first_loaded[0].fragment_id == semantic_fragment_id
    assert second_loaded[0].fragment_id == semantic_fragment_id
    assert first_loaded[0].stored_fragment_id is not None
    assert second_loaded[0].stored_fragment_id is not None
    assert first_loaded[0].stored_fragment_id != second_loaded[0].stored_fragment_id
    with pytest.raises(
        ValueError,
        match="Semantic lineage fragment id resolves to multiple stored occurrence records",
    ):
        store.get(semantic_fragment_id)


def test_reproducibility_contract_effective_config_semantic_payload_is_stable() -> None:
    service = EffectiveConfigService()
    dq_config = DQConfig(
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        rule_bundle_version="dq-rules.v1",
        default_disposition_policy=DQDisposition.WARN,
    )
    kwargs = {
        "pipeline_name": "chembl_activity",
        "pipeline_kind": "standard",
        "resolved_config": {"provider": "chembl", "entity_type": "activity"},
        "runtime_overrides": {"cli": {"limit": 25}},
        "source_refs": [
            ConfigSourceRef(
                source_type="fixture",
                source_path="tests/fixtures/bronze/chembl/activity/sample.jsonl",
                source_hash="fixture-hash-1",
                priority=1,
            )
        ],
        "dq_config": dq_config,
        "artifact_id": "eca-stable",
    }
    first = service.create_effective_config_artifact(**kwargs)
    second = service.create_effective_config_artifact(**kwargs)

    assert service.serialize_semantic_artifact(
        first
    ) == service.serialize_semantic_artifact(second)
    assert first.effective_config_hash == second.effective_config_hash


def test_reproducibility_contract_bronze_bundle_has_canonical_artifact_identity() -> (
    None
):
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
    assert (
        bundle.metadata.output.lineage_fragment_id
        == bundle.lineage_fragment.fragment_id
    )


def test_reproducibility_contract_silver_bundle_keeps_sidecar_and_fragment_identity_aligned() -> (
    None
):
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
    assert (
        bundle.metadata.output.lineage_fragment_id
        == bundle.lineage_fragment.fragment_id
    )
    assert any(
        node.node_id == bundle.metadata.output.artifact_id
        for node in bundle.lineage_fragment.nodes
    )


def test_reproducibility_contract_gold_bundle_keeps_sidecar_and_fragment_identity_aligned() -> (
    None
):
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
    assert (
        bundle.metadata.output.lineage_fragment_id
        == bundle.lineage_fragment.fragment_id
    )
    assert any(
        node.node_id == bundle.metadata.output.artifact_id
        for node in bundle.lineage_fragment.nodes
    )


def test_reproducibility_contract_supported_gold_trace_path_resolves_run_context() -> (
    None
):
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


@pytest.mark.parametrize("family", _PUBLISHED_SUPPORTED_FAMILIES)
def test_reproducibility_contract_forensic_grade_profile_is_attained(
    family: str,
) -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000412"))
    provider, entity, pipeline_name = _family_context(family)
    manifest = _make_manifest(
        manifest_id="manifest-forensic-grade-1",
        run_id=run_id,
        execution_fingerprint="fp-forensic-grade-1",
        required_persistence_profile="forensic_grade",
        input_snapshots=(
            RunInputSnapshotRef(
                snapshot_id="snapshot-1",
                content_hash="content-hash-1",
                immutable_uri="file:///snapshots/bronze-1.jsonl.zst",
                query_fingerprint="query-hash-1",
                captured_at=datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
            ),
        ),
        identity=_ManifestIdentity(
            pipeline_name=pipeline_name,
            provider=provider,
            entity=entity,
            contract_ref=family,
        ),
    )
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-forensic-grade-1",
            manifest_id=manifest.manifest_id,
            run_id=run_id,
            event_type="artifact_published",
            occurred_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
            event_family="artifact",
            status="success",
            stage="silver",
            dataset_ref=f"silver:{family}@7",
            lineage_fragment_id=f"silver:{family}@7#lineage",
            details={
                "artifact_path": f"silver/{provider}/{entity}",
                "metadata_path": f"silver/{provider}/{entity}/{entity}_metadata.yaml",
                "artifact_kind": "metadata_sidecar",
                "pipeline_name": pipeline_name,
                "provider": provider,
                "entity": entity,
                "run_id": str(run_id),
                "manifest_id": manifest.manifest_id,
            },
        )
    )

    result = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    ).show(manifest.manifest_id)

    assert result.diagnostics["required_persistence_profile"] == "forensic_grade"
    assert result.diagnostics["lineage_closure_boundary"] == {
        "family": family,
        "support_scope": "operator_grade_trace_debug",
        "supported": True,
        "reason": "family_within_supported_boundary",
        "supported_families": list(_PUBLISHED_SUPPORTED_FAMILIES),
    }
    assert result.diagnostics["replay_family_contract"]["family"] == family
    assert (
        result.diagnostics["replay_family_contract"]["strict_exact_replay_supported"]
        is True
    )
    assert result.diagnostics["persistence_profile"]["attained_profile"] == (
        "forensic_grade"
    )
    assert result.diagnostics["persistence_profile"]["required_profile"] == (
        "forensic_grade"
    )
    assert (
        result.diagnostics["persistence_profile"]["required_profile_satisfied"] is True
    )
    assert (
        result.diagnostics["persistence_profile"][
            "required_profile_missing_requirements"
        ]
        == []
    )
    assert (
        result.diagnostics["alert_signals"]["required_persistence_profile_gap"] is False
    )
    score = result.diagnostics["reproducibility_audit_score"]
    assert score["schema_version"] == "2.0"
    assert score["score_scope"] == "supported_boundary_run"
    assert score["supported_boundary_verdict"]["verdict"] == (
        "supported_boundary_satisfied"
    )
    assert score["supported_boundary_verdict"]["supported_boundary_satisfied"] is True
    assert score["global_reproducibility_claim"]["claimed"] is False
    assert score["required_profile"] == "forensic_grade"
    assert score["thresholds"] == {
        "determinism": 8,
        "run_identity": 8,
        "checkpoint_safety": 8,
        "lineage_completeness": 8,
        "replay_readiness": 8,
        "layer_consistency": 8,
    }
    assert score["threshold_failures"] == []
    assert score["thresholds_satisfied"] is True


def test_reproducibility_contract_replay_ready_profile_requires_snapshot_backed_inputs() -> (
    None
):
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000413"))
    manifest = _make_manifest(
        manifest_id="manifest-replay-ready-missing-snapshots",
        run_id=run_id,
        execution_fingerprint="fp-replay-ready-missing-snapshots",
        required_persistence_profile="replay_ready",
        input_snapshots=(),
        exact_replay=False,
    )
    manifest_store.save(manifest)

    result = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    ).show(manifest.manifest_id)

    assert result.diagnostics["required_persistence_profile"] == "replay_ready"
    assert result.diagnostics["persistence_profile"]["attained_profile"] == (
        "degraded_observable"
    )
    assert (
        result.diagnostics["persistence_profile"]["required_profile_satisfied"] is False
    )
    assert result.diagnostics["persistence_profile"][
        "required_profile_missing_requirements"
    ] == [
        "exact_replay_capability",
        "immutable_input_snapshots",
        "produced_artifact_trace",
    ]
    assert (
        result.diagnostics["alert_signals"]["required_persistence_profile_gap"] is True
    )
    assert result.diagnostics["alert_signals"]["immutable_input_snapshot_gap"] is True
    score = result.diagnostics["reproducibility_audit_score"]
    assert score["schema_version"] == "2.0"
    assert score["score_scope"] == "supported_boundary_run"
    assert score["supported_boundary_verdict"]["verdict"] == (
        "supported_boundary_gaps_present"
    )
    assert score["supported_boundary_verdict"]["supported_boundary_satisfied"] is False
    assert score["global_reproducibility_claim"]["claimed"] is False
    assert score["required_profile"] == "replay_ready"
    assert score["thresholds"] == {
        "determinism": 7,
        "run_identity": 8,
        "checkpoint_safety": 7,
        "replay_readiness": 7,
        "layer_consistency": 7,
    }
    threshold_failures = {
        item["category"]: item for item in score["threshold_failures"]
    }
    assert score["thresholds_satisfied"] is False
    assert {"determinism", "replay_readiness"} <= set(threshold_failures)
    assert threshold_failures["determinism"]["reason"] == "below_required_threshold"
    assert threshold_failures["replay_readiness"]["reason"] == (
        "below_required_threshold"
    )


def test_reproducibility_contract_composite_replay_ready_profile_is_fail_closed() -> (
    None
):
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000414"))
    manifest = _make_manifest(
        manifest_id="manifest-composite-replay-ready",
        run_id=run_id,
        execution_fingerprint="fp-composite-replay-ready",
        required_persistence_profile="replay_ready",
        input_snapshots=(),
        identity=_ManifestIdentity(
            pipeline_name="publications",
            provider="composite",
            entity="publications",
            contract_ref="composite.publications",
        ),
        exact_replay=False,
        execution_context="composite",
    )
    manifest_store.save(manifest)

    result = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    ).show(manifest.manifest_id)

    assert result.diagnostics["exact_replay_support_boundary"] == (
        "composite_snapshot_backed_input_envelope"
    )
    assert (
        result.diagnostics["persistence_profile"]["required_profile_satisfied"] is False
    )
    assert result.diagnostics["persistence_profile"][
        "required_profile_missing_requirements"
    ] == [
        "exact_replay_capability",
        "immutable_input_snapshots",
        "produced_artifact_trace",
    ]
    assert result.diagnostics["alert_signals"]["strict_replay_boundary_gap"] is False
    assert (
        result.diagnostics["alert_signals"]["required_persistence_profile_gap"] is True
    )
    score = result.diagnostics["reproducibility_audit_score"]
    assert score["schema_version"] == "2.0"
    assert score["score_scope"] == "supported_boundary_run"
    assert score["supported_boundary_verdict"]["verdict"] == (
        "blocked_outside_supported_boundary"
    )
    assert score["supported_boundary_verdict"]["supported_boundary_satisfied"] is False
    assert score["global_reproducibility_claim"]["claimed"] is False
    threshold_failures = {
        item["category"]: item for item in score["threshold_failures"]
    }
    assert score["required_profile"] == "replay_ready"
    assert score["thresholds_satisfied"] is False
    assert {"determinism", "replay_readiness"} <= set(threshold_failures)


def test_reproducibility_contract_composite_full_snapshot_envelope_exact_replay_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Composite replay matrix must prove stable semantic identity at runtime."""
    data_dir = tmp_path / "runtime"
    bronze_root = tmp_path / "cached-bronze"
    _write_composite_snapshot_envelope(bronze_root)
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_code_revision_provenance",
        lambda: SimpleNamespace(
            git_commit="test-clean-composite-replay",
            source_revision_state="clean",
            dependency_lock_hash="sha256:test-lock-composite-replay",
        ),
    )
    config = _build_replay_matrix_composite_config()
    runtime = CompositeRuntimeConfig(
        resume=True,
        use_cached_bronze=True,
        cached_bronze_path=str(bronze_root),
        cached_bronze_date="2026-01-01",
    )

    bundles = []
    manifests = []
    for index in range(2):
        settings = Settings(
            data_dir=data_dir,
            pipeline={
                "control_plane": {
                    "run_manifest_enabled": True,
                    "run_ledger_enabled": True,
                    "required_persistence_profile": "replay_ready",
                }
            },
        )
        infra_context = CompositeInfrastructureContext(
            run_id=str(UUID(f"00000000-0000-0000-0000-00000000052{index}")),
            settings=settings,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracer=MagicMock(),
            storage=MagicMock(),
            lock=MagicMock(),
        )
        bundle = build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )
        bundles.append(bundle)
        manifests.append(_load_manifest_payload(data_dir, bundle.manifest_id))

    first, second = manifests
    assert first["run_id"] != second["run_id"]
    assert first["manifest_id"] != second["manifest_id"]
    assert first["replay_capability"] == "exact_replay_supported"
    assert second["replay_capability"] == "exact_replay_supported"
    assert first["execution_fingerprint"] == second["execution_fingerprint"]
    assert (
        first["code_provenance"]["effective_config_artifact_id"]
        == (second["code_provenance"]["effective_config_artifact_id"])
    )
    snapshot_ids_first = [
        snapshot["snapshot_id"]
        for source_ref in first["source_refs"]
        for snapshot in source_ref["input_snapshots"]
    ]
    snapshot_ids_second = [
        snapshot["snapshot_id"]
        for source_ref in second["source_refs"]
        for snapshot in source_ref["input_snapshots"]
    ]
    assert len(snapshot_ids_first) == 3
    assert snapshot_ids_first == snapshot_ids_second

    evidence_dir = tmp_path / "reports" / "reproducibility"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "composite_publication_exact_replay_matrix.json"
    evidence_path.write_text(
        json.dumps(
            {
                "pipeline_name": config.name,
                "case": "composite_full_snapshot_envelope_exact_replay",
                "replay_capability": first["replay_capability"],
                "semantic_identity": {
                    "execution_fingerprint": first["execution_fingerprint"],
                    "effective_config_artifact_id": first["code_provenance"][
                        "effective_config_artifact_id"
                    ],
                    "snapshot_ids": snapshot_ids_first,
                },
                "occurrences": [
                    {
                        "run_id": first["run_id"],
                        "manifest_id": first["manifest_id"],
                    },
                    {
                        "run_id": second["run_id"],
                        "manifest_id": second["manifest_id"],
                    },
                ],
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["case"] == "composite_full_snapshot_envelope_exact_replay"
    assert len(evidence["occurrences"]) == 2


def test_reproducibility_contract_forensic_grade_is_blocked_outside_supported_lineage_family() -> (
    None
):
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000415"))
    manifest = _make_manifest(
        manifest_id="manifest-forensic-unsupported-family",
        run_id=run_id,
        execution_fingerprint="fp-forensic-unsupported-family",
        required_persistence_profile="forensic_grade",
        input_snapshots=(
            RunInputSnapshotRef(
                snapshot_id="snapshot-pubmed-1",
                content_hash="content-hash-pubmed-1",
                immutable_uri="file:///snapshots/pubmed/publication-1.jsonl.zst",
                query_fingerprint="query-hash-pubmed-1",
                captured_at=datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
            ),
        ),
        identity=_ManifestIdentity(
            pipeline_name="openalex_works",
            provider="openalex",
            entity="works",
            contract_ref="openalex.works",
        ),
    )
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-forensic-unsupported-family-1",
            manifest_id=manifest.manifest_id,
            run_id=run_id,
            event_type="artifact_published",
            occurred_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
            event_family="artifact",
            status="success",
            stage="silver",
            dataset_ref="silver:openalex.works@1",
            lineage_fragment_id="silver:openalex.works@1#lineage",
            details={
                "artifact_path": "silver/openalex/works",
                "metadata_path": "silver/openalex/works/works_metadata.yaml",
                "artifact_kind": "metadata_sidecar",
                "pipeline_name": "openalex_works",
                "provider": "openalex",
                "entity": "works",
                "run_id": str(run_id),
                "manifest_id": manifest.manifest_id,
            },
        )
    )

    result = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    ).show(manifest.manifest_id)

    assert result.diagnostics["lineage_closure_boundary"] == {
        "family": "openalex.works",
        "support_scope": "operator_grade_trace_debug",
        "supported": False,
        "reason": "family_outside_published_inventory",
        "supported_families": list(_PUBLISHED_SUPPORTED_FAMILIES),
    }
    assert result.diagnostics["replay_family_contract"]["family"] == "openalex.works"
    assert (
        result.diagnostics["replay_family_contract"]["strict_exact_replay_supported"]
        is False
    )
    assert (
        result.diagnostics["persistence_profile"]["attained_profile"]
        == "degraded_observable"
    )
    assert result.diagnostics["persistence_profile"]["required_profile"] == (
        "forensic_grade"
    )
    assert (
        result.diagnostics["persistence_profile"]["required_profile_satisfied"] is False
    )
    assert result.diagnostics["persistence_profile"][
        "required_profile_missing_requirements"
    ] == [
        "strict_replay_execution_context_support",
        "exact_replay_capability",
        "lineage_closure_boundary_support",
    ]
    assert result.diagnostics["persistence_profile"][
        "replay_ready_missing_requirements"
    ] == [
        "strict_replay_execution_context_support",
        "exact_replay_capability",
    ]
    assert result.diagnostics["persistence_profile"][
        "forensic_grade_missing_requirements"
    ] == [
        "strict_replay_execution_context_support",
        "exact_replay_capability",
        "lineage_closure_boundary_support",
    ]
    assert result.diagnostics["alert_signals"]["strict_replay_boundary_gap"] is True
    assert result.diagnostics["alert_signals"]["lineage_closure_boundary_gap"] is True
    assert (
        result.diagnostics["alert_signals"]["required_persistence_profile_gap"] is True
    )
    score = result.diagnostics["reproducibility_audit_score"]
    assert score["schema_version"] == "2.0"
    assert score["score_scope"] == "supported_boundary_run"
    assert score["supported_boundary_verdict"]["verdict"] == (
        "blocked_outside_supported_boundary"
    )
    assert score["supported_boundary_verdict"]["supported_boundary_satisfied"] is False
    assert score["global_reproducibility_claim"]["claimed"] is False
    threshold_failures = {
        item["category"]: item for item in score["threshold_failures"]
    }
    assert score["required_profile"] == "forensic_grade"
    assert score["thresholds_satisfied"] is False
    assert "lineage_completeness" in threshold_failures


def test_reproducibility_contract_inventory_covers_all_production_families() -> None:
    entity_families = {
        f"{path.parent.name}.{path.stem}"
        for path in Path("configs/entities").glob("*/*.yaml")
    }
    composite_families = {
        f"composite.{path.stem}" for path in Path("configs/composites").glob("*.yaml")
    }

    assert set(_PUBLISHED_PRODUCTION_FAMILIES) == entity_families | composite_families


def test_reproducibility_contract_inventory_profiles_all_production_families() -> None:
    inventory = published_reproducibility_family_inventory()
    profile_by_family = {str(item["family"]): item for item in inventory}

    assert set(profile_by_family) == set(_PUBLISHED_PRODUCTION_FAMILIES)
    assert profile_by_family["chembl.activity"]["strict_exact_replay_supported"] is True
    assert profile_by_family["chembl.activity"]["strict_replay_runtime_verdict"] == (
        "allowed_with_snapshot_backed_source_refs"
    )
    assert (
        profile_by_family["openalex.publication"]["strict_exact_replay_supported"]
        is False
    )
    assert (
        profile_by_family["openalex.publication"]["strict_replay_runtime_verdict"]
        == "blocked_outside_supported_boundary"
    )
    assert (
        profile_by_family["composite.publication"]["exact_replay_support_boundary"]
        == "composite_snapshot_backed_input_envelope"
    )
    assert (
        profile_by_family["composite.publication"]["strict_replay_runtime_verdict"]
        == "requires_full_composite_snapshot_envelope"
    )


def test_reproducibility_contract_silver_batch_dedup_is_order_insensitive() -> None:
    forward = [
        {"id": "1", "value": "winner", "content_hash": "a-hash"},
        {"id": "1", "value": "loser", "content_hash": "z-hash"},
    ]
    reverse = list(reversed(forward))
    expected = [{"id": "1", "value": "winner", "content_hash": "a-hash"}]

    assert _deduplicate_by_primary_keys_impl(forward, ["id"]) == expected
    assert _deduplicate_by_primary_keys_impl(reverse, ["id"]) == expected


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
async def test_reproducibility_contract_composite_quarantine_replay_anchor_is_deterministic() -> (
    None
):
    host = _CompositeReplayHost()

    await host._write_cv_quarantine(MergeResult(quarantine_payloads=({"id": "cv-1"},)))

    host._quarantine_port.write.assert_awaited_once()
    write_kwargs = host._quarantine_port.write.await_args.kwargs
    assert write_kwargs["pipeline"] == "composite:publication"
    assert write_kwargs["ingestion_ts"] == datetime(2025, 2, 3, 0, 0, tzinfo=UTC)
    assert write_kwargs["metadata"]["artifact_policy"] == "occurrence_only_diagnostic"
    assert write_kwargs["metadata"]["replay_contract"] == "excluded_from_exact_replay"


def test_reproducibility_contract_composite_quarantine_is_explicitly_occurrence_only() -> (
    None
):
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
