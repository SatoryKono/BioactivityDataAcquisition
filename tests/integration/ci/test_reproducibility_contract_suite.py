# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Cross-cutting reproducibility contract suite for exact replay diagnostics."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import count
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.application.composite.merger_metrics_mixin import MergeMetricsRecorderMixin
from bioetl.application.services.control_plane.effective_config.service import (
    EffectiveConfigService,
)
from bioetl.application.services.checkpoint.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.application.services.control_plane.forensic import ForensicRunDiffService
from bioetl.application.services.control_plane.replay.historical_certification_service import (
    HistoricalReplayCertificationService,
    HistoricalReplaySnapshotCertification,
)
from bioetl.application.services.control_plane.replay.historical_corpus_service import (
    HistoricalReplayBulkCertificationSpec,
    HistoricalReplayCorpusService,
)
from bioetl.application.services.control_plane.manifest.diagnostics import (
    build_diagnostics_summary,
)
from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.application.services.lineage import MetadataCoordinator
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.composition.bootstrap.runtime.composite_control_plane_builder import (
    build_composite_control_plane_bundle,
)
from bioetl.composition.bootstrap.runtime.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunLedgerEntry,
    RunCodeProvenance,
    RunManifest,
    RunInputSnapshotRef,
    RunSourceRef,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    published_production_reproducibility_families,
    published_supported_boundary_families,
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
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.control_plane import FileArtifactByteComparisonAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.config._base import Settings
from tests.helpers.clock import FixedClock
from tests.integration.ci.reproducibility_contract_support import (
    CompositeReplayHost as _CompositeReplayHost,
    DEFAULT_MANIFEST_IDENTITY as _DEFAULT_MANIFEST_IDENTITY,
    InMemoryRunLedgerStore as _InMemoryRunLedgerStore,
    ManifestIdentity as _ManifestIdentity,
    build_replay_matrix_composite_config as _build_replay_matrix_composite_config,
    load_manifest_payload as _load_manifest_payload,
    write_composite_snapshot_envelope as _write_composite_snapshot_envelope,
)
from tests.unit.infrastructure.storage.test_metadata_writer_control_plane import (
    _make_bronze_metadata,
    _make_gold_metadata,
    _make_silver_metadata,
)


pytestmark = pytest.mark.integration


def _repro_contract_entry_id_factory(prefix: str = "entry-historical") -> Callable[[], str]:
    sequence = count(1)
    return lambda: f"{prefix}-{next(sequence)}"


_VALID_CONFIG_HASH = "a" * 64
_PUBLISHED_SUPPORTED_FAMILIES = tuple(published_supported_reproducibility_families())
_PUBLISHED_SUPPORTED_BOUNDARY_FAMILIES = tuple(published_supported_boundary_families())
_PUBLISHED_SUPPORTED_SOURCE_FAMILIES = tuple(
    family
    for family in _PUBLISHED_SUPPORTED_FAMILIES
    if not family.startswith("composite.")
)
_PUBLISHED_PRODUCTION_FAMILIES = tuple(published_production_reproducibility_families())


_InMemoryRunManifestStore = InMemoryRunManifestStore


class _MergeMetricsMixinHarness(MergeMetricsRecorderMixin):
    """Concrete harness exposing MergeMetricsRecorderMixin contract methods."""


def _make_merge_metrics_mixin() -> MergeMetricsRecorderMixin:
    return _MergeMetricsMixinHarness()


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
            dependency_lock_hash="sha256:test-lock-hash",
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
                input_snapshots=input_snapshots,
            ),
        ),
    )


def test_historical_replay_corpus_inventory_and_bulk_certification() -> None:
    source_manifest = _make_manifest(
        manifest_id="historical-source-manifest",
        run_id=deterministic_run_uuid_from_callsite(
            "test_reproducibility_contract_suite"
        ),
        execution_fingerprint="historical-source-fingerprint",
        identity=_ManifestIdentity(
            pipeline_name="pubmed_publication",
            provider="pubmed",
            entity="publication",
            contract_ref="pubmed.publication",
        ),
        execution_context="source",
    )
    composite_manifest = _make_manifest(
        manifest_id="historical-composite-manifest",
        run_id=deterministic_run_uuid_from_callsite(
            "test_reproducibility_contract_suite"
        ),
        execution_fingerprint="historical-composite-fingerprint",
        identity=_ManifestIdentity(
            pipeline_name="composite_publication",
            provider="composite",
            entity="publication",
            contract_ref="composite.publication",
        ),
        execution_context="composite",
    )
    composite_manifest = replace(
        composite_manifest,
        source_refs=(
            RunSourceRef(
                provider="pubmed",
                entity="publication",
                pipeline_name="pubmed_publication",
            ),
        ),
    )
    manifest_store = _InMemoryRunManifestStore()
    manifest_store.save(source_manifest)
    manifest_store.save(composite_manifest)
    ledger_store = _InMemoryRunLedgerStore()
    service = HistoricalReplayCorpusService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        certification_service=HistoricalReplayCertificationService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            entry_id_factory=_repro_contract_entry_id_factory("entry-corpus"),
        ),
    )

    inventory_before = service.build_certifiability_inventory()

    assert inventory_before.awaiting_source_certification_count == 1
    assert inventory_before.awaiting_composite_lineage_count == 1

    result = service.certify_retained_corpus(
        specs=(
            HistoricalReplayBulkCertificationSpec(
                manifest_id=composite_manifest.manifest_id,
                certifications=(
                    HistoricalReplaySnapshotCertification(
                        provider="pubmed",
                        entity="publication",
                        pipeline_name="pubmed_publication",
                        snapshot_id="snapshot-certified-composite-1",
                        content_hash="sha256:composite-certified-1",
                        immutable_uri="file:///historical/composite/snapshot-1.jsonl",
                        bronze_batch_ref=(
                            "bronze://historical/composite/batch-1.jsonl"
                        ),
                        certification_artifact_ref=(
                            "control://historical/composite-certification-1.json"
                        ),
                        upstream_run_id=str(source_manifest.run_id),
                        upstream_manifest_id=source_manifest.manifest_id,
                    ),
                ),
            ),
            HistoricalReplayBulkCertificationSpec(
                manifest_id=source_manifest.manifest_id,
                certifications=(
                    HistoricalReplaySnapshotCertification(
                        provider="pubmed",
                        entity="publication",
                        pipeline_name="pubmed_publication",
                        snapshot_id="snapshot-certified-source-1",
                        content_hash="sha256:source-certified-1",
                        immutable_uri="file:///historical/source/snapshot-1.jsonl",
                        bronze_batch_ref="bronze://historical/source/batch-1.jsonl",
                        certification_artifact_ref=(
                            "control://historical/source-certification-1.json"
                        ),
                    ),
                ),
            ),
        )
    )

    assert result.completed_count == 2
    assert (
        result.inventory_after.certified_count + result.inventory_after.replayable_count
        == 2
    )
    assert result.inventory_after.remaining_uncertified_count == 0


def test_reproducibility_contract_historical_source_certification_promotes_certified_tranche() -> (
    None
):
    manifest = _make_manifest(
        manifest_id="historical-source-manifest",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000701")),
        execution_fingerprint="historical-source-fingerprint",
        input_snapshots=(),
        required_persistence_profile="degraded_observable",
        exact_replay=False,
    )
    manifest_store = _InMemoryRunManifestStore()
    manifest_store.save(manifest)
    ledger_store = _InMemoryRunLedgerStore()
    certification_service = HistoricalReplayCertificationService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        entry_id_factory=_repro_contract_entry_id_factory("entry-source-certification"),
    )

    result = certification_service.certify_historical_source_run(
        manifest_id=manifest.manifest_id,
        certifications=(
            HistoricalReplaySnapshotCertification(
                provider=manifest.provider,
                entity=manifest.entity,
                pipeline_name=manifest.pipeline_name,
                snapshot_id="historical-source-snapshot-1",
                content_hash="sha256:historical-source-snapshot-1",
                immutable_uri="file:///historical/source/snapshot-1.jsonl",
                bronze_batch_ref="bronze://historical/source/batch-1.jsonl",
                certification_artifact_ref=(
                    "control://historical/source-certification-1.json"
                ),
            ),
        ),
    )

    diagnostics = build_diagnostics_summary(
        manifest,
        tuple(ledger_store.list_entries(manifest.manifest_id)),
    )

    assert result.replay_occurrence_kind == "historical_source_replay_certified_parent"
    assert (
        result.broader_historical_exact_replay_state
        == "historical_source_replay_certified"
    )
    assert diagnostics["replay_occurrence_kind"] == (
        "historical_source_replay_certified_parent"
    )
    assert diagnostics["broader_historical_exact_replay_policy"] == (
        "certified_historical_exact_replay_tranche_supported"
    )
    assert diagnostics["broader_historical_exact_replay_boundary"] == (
        "historical_source_snapshot_certification"
    )
    assert diagnostics["broader_historical_exact_replay_state"] == (
        "historical_source_replay_certified"
    )


def test_reproducibility_contract_historical_composite_certification_requires_certified_source_lineage() -> (
    None
):
    source_manifest = _make_manifest(
        manifest_id="historical-composite-upstream-manifest",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000702")),
        execution_fingerprint="historical-composite-upstream-fingerprint",
        input_snapshots=(),
        required_persistence_profile="degraded_observable",
        exact_replay=False,
    )
    composite_manifest = replace(
        _make_manifest(
            manifest_id="historical-composite-manifest",
            run_id=RunID(UUID("00000000-0000-0000-0000-000000000703")),
            execution_fingerprint="historical-composite-fingerprint",
            input_snapshots=(),
            required_persistence_profile="degraded_observable",
            exact_replay=False,
        ),
        pipeline_name="composite_activity",
        provider="composite",
        entity="activity",
        launch_context={
            "limit": 25,
            "exact_replay": False,
            "execution_context": "composite",
            "required_persistence_profile": "degraded_observable",
        },
        runtime_config={
            "run_type": "incremental",
            "limit": 25,
            "exact_replay": False,
            "execution_context": "composite",
            "required_persistence_profile": "degraded_observable",
        },
        resolved_config={
            "provider": "composite",
            "entity": "activity",
            "run_type": "incremental",
            "required_persistence_profile": "degraded_observable",
            "execution_context": "composite",
        },
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query=None,
                input_snapshots=(),
            ),
        ),
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="f" * 40,
            source_revision_state="clean",
            dependency_lock_hash="d" * 64,
            config_hash=_VALID_CONFIG_HASH,
            resolved_config_hash=_VALID_CONFIG_HASH,
            effective_config_hash=_VALID_CONFIG_HASH,
            contract_ref="composite.activity",
            contract_version="1.0.0",
            contract_schema_hash="schema:composite.activity@1.0.0",
            dq_policy_ref="dq.policy.composite_activity",
            rule_bundle_version="bundle:composite.activity@1.0.0",
            dq_contract_compatibility_hash="c" * 64,
            effective_config_artifact_id="effective:composite.activity",
        ),
    )
    manifest_store = _InMemoryRunManifestStore()
    manifest_store.save(source_manifest)
    manifest_store.save(composite_manifest)
    ledger_store = _InMemoryRunLedgerStore()
    certification_service = HistoricalReplayCertificationService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        entry_id_factory=_repro_contract_entry_id_factory(
            "entry-composite-certification"
        ),
    )

    certification_service.certify_historical_source_run(
        manifest_id=source_manifest.manifest_id,
        certifications=(
            HistoricalReplaySnapshotCertification(
                provider=source_manifest.provider,
                entity=source_manifest.entity,
                pipeline_name=source_manifest.pipeline_name,
                snapshot_id="historical-composite-upstream-snapshot-1",
                content_hash="sha256:historical-composite-upstream-snapshot-1",
                immutable_uri="file:///historical/source/upstream-snapshot-1.jsonl",
                bronze_batch_ref="bronze://historical/source/upstream-batch-1.jsonl",
                certification_artifact_ref=(
                    "control://historical/source-upstream-certification.json"
                ),
            ),
        ),
    )

    result = certification_service.certify_historical_composite_run(
        manifest_id=composite_manifest.manifest_id,
        certifications=(
            HistoricalReplaySnapshotCertification(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                snapshot_id="historical-composite-snapshot-1",
                content_hash="sha256:historical-composite-snapshot-1",
                immutable_uri="file:///historical/composite/snapshot-1.jsonl",
                bronze_batch_ref="bronze://historical/composite/batch-1.jsonl",
                certification_artifact_ref=(
                    "control://historical/composite-certification-1.json"
                ),
                upstream_run_id=str(source_manifest.run_id),
                upstream_manifest_id=source_manifest.manifest_id,
            ),
        ),
    )

    diagnostics = build_diagnostics_summary(
        composite_manifest,
        tuple(ledger_store.list_entries(composite_manifest.manifest_id)),
    )

    assert result.replay_occurrence_kind == (
        "historical_composite_replay_certified_parent"
    )
    assert (
        result.broader_historical_exact_replay_state
        == "historical_composite_replay_certified"
    )
    assert diagnostics["replay_occurrence_kind"] == (
        "historical_composite_replay_certified_parent"
    )
    assert diagnostics["broader_historical_exact_replay_policy"] == (
        "certified_historical_exact_replay_tranche_supported"
    )
    assert diagnostics["broader_historical_exact_replay_boundary"] == (
        "historical_composite_certified_source_lineage"
    )
    assert diagnostics["broader_historical_exact_replay_state"] == (
        "historical_composite_replay_certified"
    )


def _family_context(family: str) -> tuple[str, str, str]:
    provider, entity = family.split(".", maxsplit=1)
    return provider, entity, f"{provider}_{entity}"


def test_reproducibility_contract_live_capture_materialized_snapshot_parent_state() -> (
    None
):
    manifest = _make_manifest(
        manifest_id="manifest-live-parent",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000611")),
        execution_fingerprint="fp-live-parent",
        input_snapshots=(),
        exact_replay=False,
        required_persistence_profile="degraded_observable",
        execution_context="ordinary",
    )
    ledger_entry = RunLedgerEntry(
        entry_id="entry-input-snapshot",
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        event_type="input_snapshot_published",
        event_family="input_snapshot",
        occurred_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        status="published",
        stage="bronze",
        details={
            "provider": "chembl",
            "entity": "activity",
            "pipeline_name": "chembl_activity",
            "query": "fixture://sample",
            "snapshot_id": "snapshot-1",
            "content_hash": "sha256:snapshot-1",
            "immutable_uri": "bronze://chembl/activity/2026-01-02/batch_1.jsonl.zst",
        },
    )

    summary = build_diagnostics_summary(manifest, (ledger_entry,))

    assert summary["replay_capability"] == "exact_replay_supported"
    assert summary["replay_capability_reason"] == (
        "materialized_live_capture_snapshot_envelope_present"
    )
    assert summary["replay_occurrence_kind"] == "materialized_replayable_parent"
    assert summary["replay_mode"] == "same_data_state_recovery"
    assert summary["replay_parentage"]["is_exact_replay"] is False
    assert summary["input_snapshot_materialization_mode"] == (
        "live_capture_snapshot_materialized"
    )
    assert (
        summary["replay_family_contract"]["post_capture_replayable_parent_supported"]
        is True
    )
    assert (
        summary["replay_family_contract"]["post_capture_replayable_parent_boundary"]
        == "ledger_materialized_live_capture_parent"
    )


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
        "required_persistence_profile": "degraded_observable",
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
        run_id=deterministic_run_uuid_from_callsite(
            "test_reproducibility_contract_suite"
        ),
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
        run_id=deterministic_run_uuid_from_callsite(
            "test_reproducibility_contract_suite"
        ),
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
        run_id=deterministic_run_uuid_from_callsite(
            "test_reproducibility_contract_suite"
        ),
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


def test_reproducibility_contract_cross_surface_identity_parity_suite() -> None:
    """Manifest, checkpoint, sidecar, and lineage surfaces must agree on run identity."""
    started_at = datetime(2025, 1, 1, tzinfo=UTC)
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000907"))
    manifest_id = "manifest-cross-surface-identity"
    execution_fingerprint = "fp-cross-surface-identity"
    run_context = RunContext.create(
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        started_at=started_at,
        provider="chembl",
        entity="activity",
        manifest_id=manifest_id,
        pipeline_version="1.0.0",
        git_commit="abc1234",
        dependency_lock_hash="sha256:test-lock-hash",
        config_hash=_VALID_CONFIG_HASH,
        resolved_config_hash="b" * 64,
        effective_config_hash="c" * 64,
        effective_config_artifact_id="eca-123",
        execution_fingerprint=execution_fingerprint,
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        contract_schema_hash="schema-hash-1",
        dq_policy_ref="chembl.activity.dq",
        rule_bundle_version="dq-rules.v1",
        dq_contract_compatibility_hash="compat-hash-1",
    )
    coordinator = MetadataCoordinator(run_context)
    silver_bundle = coordinator.create_silver_metadata_bundle(
        SilverMetadataInput(
            table_path="silver/chembl/activity",
            primary_keys=["activity_id"],
            mode=SilverWriteMode.MERGE,
            records=[{"activity_id": 1, "_source_batch_id": "batch-a"}],
            version_after=4,
            started_at=started_at,
            completed_at=started_at + timedelta(seconds=2),
        )
    )
    manifest = _make_manifest(
        manifest_id=manifest_id,
        run_id=run_id,
        execution_fingerprint=execution_fingerprint,
    )
    checkpoint = CheckpointMetadata(
        records_processed=1,
        dq_contract_compatibility_hash="compat-hash-1",
        pipeline_name="chembl_activity",
        run_type="incremental",
        pipeline_version="1.0.0",
        git_commit="abc1234",
        dependency_lock_hash="sha256:test-lock-hash",
        effective_config_hash="c" * 64,
        effective_config_artifact_id="eca-123",
        execution_fingerprint=execution_fingerprint,
        manifest_id=manifest_id,
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        run_context={
            "run_id": str(run_id),
            "manifest_id": manifest_id,
            "execution_fingerprint": execution_fingerprint,
            "effective_config_hash": "c" * 64,
            "effective_config_artifact_id": "eca-123",
        },
    )

    lineage_run_node = next(
        node
        for node in silver_bundle.lineage_fragment.nodes
        if node.node_type == LineageNodeType.RUN
    )
    lineage_manifest_node = next(
        node
        for node in silver_bundle.lineage_fragment.nodes
        if node.node_type == LineageNodeType.MANIFEST
    )

    assert silver_bundle.metadata.runtime.run_id == str(run_id)
    assert silver_bundle.metadata.runtime.manifest_id == manifest.manifest_id
    assert silver_bundle.lineage_fragment.run_id == str(run_id)
    assert silver_bundle.lineage_fragment.manifest_id == manifest.manifest_id
    assert checkpoint.run_context == {
        "run_id": str(run_id),
        "manifest_id": manifest_id,
        "execution_fingerprint": execution_fingerprint,
        "effective_config_hash": "c" * 64,
        "effective_config_artifact_id": "eca-123",
    }
    assert (
        manifest.code_provenance.effective_config_hash
        == checkpoint.effective_config_hash
        == silver_bundle.metadata.pipeline.effective_config_hash
        == lineage_run_node.attributes["effective_config_hash"]
        == lineage_manifest_node.attributes["effective_config_hash"]
    )
    assert (
        manifest.code_provenance.effective_config_artifact_id
        == checkpoint.effective_config_artifact_id
        == silver_bundle.metadata.pipeline.effective_config_artifact_id
        == lineage_run_node.attributes["effective_config_artifact_id"]
        == lineage_manifest_node.attributes["effective_config_artifact_id"]
    )
    assert (
        manifest.execution_fingerprint
        == checkpoint.execution_fingerprint
        == silver_bundle.metadata.pipeline.execution_fingerprint
        == lineage_run_node.attributes["execution_fingerprint"]
        == lineage_manifest_node.attributes["execution_fingerprint"]
    )
    assert (
        manifest.code_provenance.contract_ref
        == checkpoint.contract_ref
        == silver_bundle.metadata.pipeline.contract_ref
        == lineage_run_node.attributes["contract_ref"]
        == lineage_manifest_node.attributes["contract_ref"]
    )


def test_reproducibility_contract_historical_live_runs_without_snapshot_evidence_stay_bounded() -> (
    None
):
    manifest = _make_manifest(
        manifest_id="manifest-historical-live-no-snapshots",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000412")),
        execution_fingerprint="fp-historical-live-no-snapshots",
        exact_replay=False,
    )

    summary = build_diagnostics_summary(manifest, ())

    assert summary["replay_occurrence_kind"] == "ordinary_live_capture"
    assert summary["historical_live_run_upgrade_policy"] == (
        "input_snapshot_published_ledger_evidence_only"
    )
    assert summary["historical_live_run_upgrade_boundary"] == (
        "input_snapshot_published_ledger_evidence"
    )
    assert summary["broader_historical_exact_replay_policy"] == (
        "certified_historical_exact_replay_tranche_supported"
    )
    assert summary["broader_historical_exact_replay_boundary"] == (
        "historical_source_snapshot_certification"
    )
    assert summary["broader_historical_exact_replay_state"] == (
        "awaiting_historical_snapshot_certification"
    )
    assert summary["historical_live_run_upgrade_state"] == (
        "awaiting_input_snapshot_published_evidence"
    )
    assert summary["replay_capability"] == "rebuild_only"
    assert summary["replay_capability_reason"] == "immutable_input_snapshots_missing"


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
            "publication_status": "success",
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


@pytest.mark.asyncio
async def test_reproducibility_contract_forensic_grade_artifact_publication_recorder_emits_bronze_silver_gold_entries(
    tmp_path: Path,
) -> None:
    """Strict artifact-publication closure must emit ledger entries for active writer outputs."""
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000418"))
    manifest = _make_manifest(
        manifest_id="manifest-forensic-artifact-publication",
        run_id=run_id,
        execution_fingerprint="fp-forensic-artifact-publication",
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
    )
    manifest_store.save(manifest)
    ledger_service = RunLedgerService(
        ledger_port=ledger_store,
        manifest_id=manifest.manifest_id,
        run_id=run_id,
        _entry_id_factory=_repro_contract_entry_id_factory("entry-artifact-closure"),
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    ledger_service.record_manifest_created(manifest)

    writer = MetadataWriter(logger=NoOpLogger())

    def _record_artifact(
        layer: str,
        artifact_path: str,
        details: dict[str, object] | None = None,
    ) -> object:
        payload = details or {}
        return ledger_service.record_artifact_published(
            layer=layer,
            artifact_path=artifact_path,
            artifact_content_hash=str(
                payload.get("artifact_content_hash")
                or payload.get("content_hash")
                or "a" * 64
            ),
            dataset_ref=(
                str(payload["dataset_ref"]) if payload.get("dataset_ref") else None
            ),
            lineage_fragment_id=(
                str(payload["lineage_fragment_id"])
                if payload.get("lineage_fragment_id")
                else None
            ),
            details=payload,
        )

    writer.attach_artifact_recorder(_record_artifact)

    bronze_metadata = _make_bronze_metadata()
    bronze_metadata.runtime.run_id = str(run_id)
    bronze_metadata.runtime.manifest_id = manifest.manifest_id
    silver_metadata = _make_silver_metadata()
    silver_metadata.runtime.run_id = str(run_id)
    silver_metadata.runtime.manifest_id = manifest.manifest_id
    gold_metadata = _make_gold_metadata()
    gold_metadata.runtime.run_id = str(run_id)
    gold_metadata.runtime.manifest_id = manifest.manifest_id

    await writer.write_bronze_metadata(
        base_path=tmp_path / "bronze" / "chembl" / "activity",
        metadata=bronze_metadata,
        provider="chembl",
        entity="activity",
    )
    await writer.write_silver_metadata(
        base_path=tmp_path / "silver" / "chembl" / "activity",
        metadata=silver_metadata,
        provider="chembl",
        entity="activity",
    )
    await writer.write_gold_metadata(
        base_path=tmp_path / "gold" / "chembl" / "activity",
        metadata=gold_metadata,
        provider="chembl",
        entity="activity",
    )

    artifact_entries = [
        entry
        for entry in ledger_store.list_entries(manifest.manifest_id)
        if entry.event_type == "artifact_published"
    ]

    assert {entry.stage for entry in artifact_entries} == {"bronze", "silver", "gold"}
    assert all(entry.manifest_id == manifest.manifest_id for entry in artifact_entries)
    assert all(entry.run_id == run_id for entry in artifact_entries)
    assert all(
        entry.dataset_ref or entry.lineage_fragment_id for entry in artifact_entries
    )
    assert all(
        isinstance(entry.details, dict)
        and entry.details.get("artifact_path")
        and entry.details.get("metadata_path")
        for entry in artifact_entries
    )


@pytest.mark.parametrize("family", _PUBLISHED_SUPPORTED_SOURCE_FAMILIES)
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
        "supported_families": list(_PUBLISHED_SUPPORTED_BOUNDARY_FAMILIES),
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
    assert score["historical_replay_universe_exact_replay_claim"]["claimed"] is False
    assert score["executable_run_contract_claim"]["claimed"] is True
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


def _checkpoint_metadata_from_summary(
    manifest: RunManifest,
    summary: dict[str, object],
) -> CheckpointMetadata:
    return CheckpointMetadata(
        records_processed=1,
        dq_contract_compatibility_hash=manifest.code_provenance.dq_contract_compatibility_hash,
        pipeline_name=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        pipeline_version=manifest.code_provenance.pipeline_version,
        git_commit=manifest.code_provenance.git_commit,
        dependency_lock_hash=manifest.code_provenance.dependency_lock_hash,
        effective_config_hash=manifest.code_provenance.effective_config_hash,
        effective_config_artifact_id=manifest.code_provenance.effective_config_artifact_id,
        execution_fingerprint=manifest.execution_fingerprint,
        manifest_id=manifest.manifest_id,
        contract_ref=manifest.code_provenance.contract_ref,
        contract_version=manifest.code_provenance.contract_version,
        normalization_profile_ref="test-normalization-profile",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="sha256:test-normalization-profile",
        exact_replay=True,
        input_snapshot_ids=tuple(
            str(item) for item in summary.get("input_snapshot_ids", [])
        ),
        input_snapshot_fingerprint=str(summary["input_snapshot_identity_fingerprint"]),
        silver_filter_compatibility_mode="structural_only_compat",
    )


@pytest.mark.parametrize("family", _PUBLISHED_SUPPORTED_BOUNDARY_FAMILIES)
def test_reproducibility_contract_family_exact_replay_evidence_closure(
    family: str,
) -> None:
    """Every published supported family must expose replay evidence anchors."""
    provider, entity, pipeline_name = _family_context(family)
    run_id = deterministic_run_uuid_from_callsite("test_reproducibility_contract_suite")
    input_snapshot = RunInputSnapshotRef(
        snapshot_id=f"{family}:snapshot-1",
        content_hash="content-hash-1",
        immutable_uri=f"bronze://{provider}/{entity}/snapshot-1.jsonl.zst",
        query_fingerprint="query-hash-1",
        captured_at=datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
    )
    manifest = _make_manifest(
        manifest_id=f"manifest-family-{family.replace('.', '-')}",
        run_id=run_id,
        execution_fingerprint=f"fp-family-{family}",
        required_persistence_profile="forensic_grade",
        input_snapshots=(input_snapshot,),
        identity=_ManifestIdentity(
            pipeline_name=pipeline_name,
            provider=provider,
            entity=entity,
            contract_ref=family,
        ),
        execution_context="composite" if provider == "composite" else "ordinary",
    )
    ledger_entry = RunLedgerEntry(
        entry_id=f"entry-family-{family}",
        manifest_id=manifest.manifest_id,
        run_id=run_id,
        event_type="artifact_published",
        occurred_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        event_family="artifact",
        status="success",
        stage="silver",
        dataset_ref=f"silver:{family}@1",
        lineage_fragment_id=f"silver:{family}@1#lineage",
        details={
            "artifact_path": f"silver/{provider}/{entity}",
            "metadata_path": f"silver/{provider}/{entity}/_metadata.yaml",
            "artifact_kind": "layer_output",
            "artifact_semantics": "semantic_table",
            "execution_fingerprint": manifest.execution_fingerprint,
            "manifest_id": manifest.manifest_id,
            "run_id": str(run_id),
        },
    )

    summary = build_diagnostics_summary(manifest, (ledger_entry,))
    compatibility = CheckpointCompatibilityService(
        NoOpLogger()
    ).validate_checkpoint_compatibility(
        _checkpoint_metadata_from_summary(manifest, summary),
        _checkpoint_metadata_from_summary(manifest, summary),
    )

    assert summary["replay_capability"] == "exact_replay_supported"
    assert summary["input_snapshot_identity_fingerprint"]
    assert summary["produced_artifact_trace"]["complete"] is True
    assert summary["artifact_publication_closure"] == "closed"
    assert summary["resume_contract"]["continuation_mode"] == "exact_replay"
    assert compatibility.compatible is True


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
    assert score["historical_replay_universe_exact_replay_claim"]["claimed"] is False
    assert score["executable_run_contract_claim"]["claimed"] is True
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
        "snapshot_backed_source_runs_only"
    )
    assert (
        result.diagnostics["persistence_profile"]["required_profile_satisfied"] is False
    )
    assert result.diagnostics["persistence_profile"][
        "required_profile_missing_requirements"
    ] == [
        "strict_replay_execution_context_support",
        "exact_replay_capability",
        "immutable_input_snapshots",
        "produced_artifact_trace",
    ]
    assert result.diagnostics["alert_signals"]["strict_replay_boundary_gap"] is True
    assert (
        result.diagnostics["alert_signals"]["required_persistence_profile_gap"] is True
    )
    score = result.diagnostics["reproducibility_audit_score"]
    assert score["schema_version"] == "2.0"
    assert score["score_scope"] == "unsupported_boundary_run"
    assert score["supported_boundary_verdict"]["verdict"] == (
        "blocked_outside_supported_boundary"
    )
    assert score["supported_boundary_verdict"]["supported_boundary_satisfied"] is False
    assert score["historical_replay_universe_exact_replay_claim"]["claimed"] is False
    assert score["executable_run_contract_claim"]["claimed"] is True
    threshold_failures = {
        item["category"]: item for item in score["threshold_failures"]
    }
    assert score["required_profile"] == "replay_ready"
    assert score["thresholds_satisfied"] is False
    assert {"determinism", "replay_readiness"} <= set(threshold_failures)


def test_reproducibility_contract_composite_full_snapshot_envelope_rebuild_resume_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Composite matrix must prove stable rebuild/resume identity without replay claims."""
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
                    "required_persistence_profile": "degraded_observable",
                    "checkpoint_compatibility_policy": "hard_fail",
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
            lock=MagicMock(), clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)),
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
    assert first["replay_capability"] == "resume_only"
    assert second["replay_capability"] == "resume_only"
    assert first["launch_context"]["exact_replay"] is False
    assert first["launch_context"]["strict_exact_replay_supported"] is False
    assert first["launch_context"]["exact_replay_support_boundary"] == (
        "snapshot_backed_source_runs_only"
    )
    assert first["launch_context"]["composite_replay_semantics"] == (
        "rebuild_resume_only"
    )
    assert first["provider"] == "composite"
    assert first["entity"] == "publication"
    assert first["code_provenance"]["pipeline_version"] == "1.0.0"
    assert first["code_provenance"]["contract_ref"] == "composite.publication"
    assert first["code_provenance"]["contract_version"] == "1.0.0"
    assert first["code_provenance"]["contract_schema_hash"]
    assert first["code_provenance"]["dq_policy_ref"] == "composite.dq.v1"
    assert first["code_provenance"]["rule_bundle_version"] == "dq-rules.v1.0"
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
    evidence_path = evidence_dir / "composite_publication_rebuild_resume_matrix.json"
    evidence_path.write_text(
        json.dumps(
            {
                "pipeline_name": config.name,
                "case": "composite_cached_bronze_rebuild_resume",
                "replay_capability": first["replay_capability"],
                "exact_replay_claimed": False,
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
    assert evidence["case"] == "composite_cached_bronze_rebuild_resume"
    assert len(evidence["occurrences"]) == 2


def test_reproducibility_contract_composite_forensic_grade_matrix_rejects_full_snapshot_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Composite forensic-grade cannot claim strict exact replay from cached Bronze."""
    data_dir = tmp_path / "runtime"
    bronze_root = tmp_path / "cached-bronze"
    _write_composite_snapshot_envelope(bronze_root)
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_code_revision_provenance",
        lambda: SimpleNamespace(
            git_commit="test-clean-composite-forensic",
            source_revision_state="clean",
            dependency_lock_hash="sha256:test-lock-composite-forensic",
        ),
    )
    config = _build_replay_matrix_composite_config()
    runtime = CompositeRuntimeConfig(
        resume=True,
        use_cached_bronze=True,
        cached_bronze_path=str(bronze_root),
        cached_bronze_date="2026-01-01",
    )
    settings = Settings(
        data_dir=data_dir,
        pipeline={
            "control_plane": {
                "run_manifest_enabled": True,
                "run_ledger_enabled": True,
                "required_persistence_profile": "forensic_grade",
                "checkpoint_compatibility_policy": "hard_fail",
            }
        },
    )
    infra_context = CompositeInfrastructureContext(
        run_id=str(UUID("00000000-0000-0000-0000-000000000599")),
        settings=settings,
        logger=MagicMock(),
        metrics=MagicMock(),
        tracer=MagicMock(),
        storage=MagicMock(),
        lock=MagicMock(), clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)),
    )

    with pytest.raises(
        RuntimeError,
        match="outside the strict exact-replay support boundary",
    ):
        build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )


def test_reproducibility_contract_forensic_diff_exposes_byte_mismatch_inside_semantic_equivalence(
    tmp_path: Path,
) -> None:
    """Forensic diff must distinguish semantic replay from byte-equivalent artifacts."""
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    left_run_id = RunID(UUID("00000000-0000-0000-0000-000000000530"))
    right_run_id = RunID(UUID("00000000-0000-0000-0000-000000000531"))
    input_snapshots = (
        RunInputSnapshotRef(
            snapshot_id="snapshot-1",
            content_hash="content-hash-1",
            immutable_uri="file:///snapshots/bronze-1.jsonl.zst",
            query_fingerprint="query-hash-1",
            captured_at=datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
        ),
    )
    left_manifest = _make_manifest(
        manifest_id="manifest-byte-left",
        run_id=left_run_id,
        execution_fingerprint="fp-byte-shared",
        input_snapshots=input_snapshots,
    )
    right_manifest = _make_manifest(
        manifest_id="manifest-byte-right",
        run_id=right_run_id,
        execution_fingerprint="fp-byte-shared",
        input_snapshots=input_snapshots,
    )
    manifest_store.save(left_manifest)
    manifest_store.save(right_manifest)

    left_artifact = tmp_path / "left_metadata.yaml"
    right_artifact = tmp_path / "right_metadata.yaml"
    left_artifact.write_text("run_id: left\nvalue: stable\n", encoding="utf-8")
    right_artifact.write_text("run_id: right\nvalue: stable\n", encoding="utf-8")

    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-byte-left",
            manifest_id=left_manifest.manifest_id,
            run_id=left_run_id,
            event_type="artifact_published",
            occurred_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
            event_family="artifact",
            status="success",
            stage="silver",
            dataset_ref="silver:chembl.activity@1",
            lineage_fragment_id="silver:chembl.activity@1#lineage",
            details={
                "artifact_path": str(left_artifact),
                "metadata_path": str(left_artifact),
                "artifact_kind": "metadata_sidecar",
                "pipeline_name": "chembl_activity",
                "provider": "chembl",
                "entity": "activity",
                "run_id": str(left_run_id),
                "manifest_id": left_manifest.manifest_id,
            },
        )
    )
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-byte-right",
            manifest_id=right_manifest.manifest_id,
            run_id=right_run_id,
            event_type="artifact_published",
            occurred_at=datetime(2025, 1, 1, 0, 2, tzinfo=UTC),
            event_family="artifact",
            status="success",
            stage="silver",
            dataset_ref="silver:chembl.activity@1",
            lineage_fragment_id="silver:chembl.activity@1#lineage",
            details={
                "artifact_path": str(right_artifact),
                "metadata_path": str(right_artifact),
                "artifact_kind": "metadata_sidecar",
                "pipeline_name": "chembl_activity",
                "provider": "chembl",
                "entity": "activity",
                "run_id": str(right_run_id),
                "manifest_id": right_manifest.manifest_id,
            },
        )
    )

    payload = (
        ForensicRunDiffService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            artifact_byte_comparison_port=FileArtifactByteComparisonAdapter(),
        )
        .compare(
            left_manifest.manifest_id,
            right_manifest.manifest_id,
        )
        .to_dict()
    )

    assert payload["semantic_equivalent"] is True
    assert payload["occurrence_only"] is True
    assert payload["artifact_byte_equivalence"]["available"] is True
    assert payload["artifact_byte_equivalence"]["equivalent"] is True
    assert payload["artifact_byte_equivalence"]["semantic_equivalent"] is True
    assert payload["artifact_byte_equivalence"]["raw_byte_equivalent"] is False
    assert payload["artifact_byte_equivalence"]["occurrence_only"] is True
    assert payload["artifact_byte_equivalence"]["occurrence_only_artifacts"]


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
        "supported_families": list(_PUBLISHED_SUPPORTED_BOUNDARY_FAMILIES),
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
    assert score["score_scope"] == "unsupported_boundary_run"
    assert score["supported_boundary_verdict"]["verdict"] == (
        "blocked_outside_supported_boundary"
    )
    assert score["supported_boundary_verdict"]["supported_boundary_satisfied"] is False
    assert score["historical_replay_universe_exact_replay_claim"]["claimed"] is False
    assert score["executable_run_contract_claim"]["claimed"] is True
    threshold_failures = {
        item["category"]: item for item in score["threshold_failures"]
    }
    assert score["required_profile"] == "forensic_grade"
    assert score["thresholds_satisfied"] is False
    assert "lineage_completeness" in threshold_failures


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
