"""Golden fixtures for reproducibility control-plane surfaces."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.services.control_plane.effective_config_service import (
    EffectiveConfigService,
)
from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.application.services.control_plane.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.application.services.lineage import MetadataCoordinator
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunArtifactRef,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import EnvironmentMetadata, InputSnapshotRef, SourceMetadata
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
    SilverRef,
)
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.run_context import RunContext

FIXTURE_DIR = Path("tests/fixtures/golden/reproducibility")
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"
_FIXED_TIME = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)


class _InMemoryRunManifestStore:
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


def _save_fixture(name: str, payload: dict[str, object]) -> None:
    fixture_path = FIXTURE_DIR / f"{name}.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_fixture(name: str) -> dict[str, object]:
    fixture_path = FIXTURE_DIR / f"{name}.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _assert_matches_fixture(name: str, payload: dict[str, object]) -> None:
    if UPDATE_SNAPSHOTS:
        _save_fixture(name, payload)
        pytest.skip(f"Updated reproducibility golden fixture {name}")

    fixture_path = FIXTURE_DIR / f"{name}.json"
    if not fixture_path.exists():
        pytest.fail(
            f"Missing reproducibility golden fixture {fixture_path}. "
            "Run with UPDATE_SNAPSHOTS=1 to create it."
        )

    assert payload == _load_fixture(name)


def _make_manifest() -> RunManifest:
    return RunManifest(
        manifest_id="manifest-golden-001",
        execution_fingerprint="fp-golden-001",
        schema_version="1.0",
        created_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000901")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={
            "limit": 25,
            "exact_replay": True,
            "execution_context": "ordinary",
            "required_persistence_profile": "replay_ready",
        },
        runtime_config={"run_type": "incremental", "limit": 25, "exact_replay": True},
        resolved_config={"provider": "chembl", "entity": "activity", "limit": 25},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            source_revision_state="clean",
            config_hash="a" * 64,
            resolved_config_hash="b" * 64,
            effective_config_hash="c" * 64,
            contract_ref="chembl.activity",
            contract_version="1.2.0",
            contract_schema_hash="d" * 64,
            dq_policy_ref="chembl_activity.gold",
            rule_bundle_version="2026.03",
            dq_contract_compatibility_hash="e" * 64,
            effective_config_artifact_id="eca-golden-001",
        ),
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query="assay_type=B",
                input_snapshots=(
                    RunInputSnapshotRef(
                        snapshot_id="snapshot-golden-001",
                        content_hash="f" * 64,
                        immutable_uri="s3://bioetl-bronze/chembl/activity/batch-001.jsonl.zst",
                        query_fingerprint="g" * 64,
                        storage_provider="s3",
                        object_bucket="bioetl-bronze",
                        object_key="chembl/activity/batch-001.jsonl.zst",
                        object_version_id="version-001",
                        etag="etag-001",
                        last_modified="2025-01-01T11:55:00Z",
                        captured_at=datetime(2025, 1, 1, 11, 55, tzinfo=UTC),
                    ),
                ),
            ),
        ),
        planned_artifacts=(
            RunArtifactRef(layer="silver", path="silver/chembl/activity"),
        ),
    )


def _prime_environment_metadata() -> None:
    MetadataCoordinator.reset_environment_cache()
    MetadataCoordinator._cached_environment = EnvironmentMetadata(
        hostname="golden-host",
        python_version="3.12.0",
        bioetl_version="0.0-test",
    )


def _make_run_context(*, run_id: str) -> RunContext:
    return RunContext.create(
        run_id=RunID(UUID(run_id)),
        run_type=RunType.INCREMENTAL,
        started_at=_FIXED_TIME,
        provider="chembl",
        entity="activity",
        pipeline_version="1.0.0",
        git_commit="abc1234",
        config_hash="a" * 64,
        resolved_config_hash="b" * 64,
        effective_config_hash="c" * 64,
        manifest_id="manifest-golden-001",
        contract_ref="chembl.activity",
        contract_version="1.2.0",
        contract_schema_hash="d" * 64,
        dq_policy_ref="chembl_activity.gold",
        rule_bundle_version="2026.03",
        dq_contract_compatibility_hash="e" * 64,
        effective_config_artifact_id="eca-golden-001",
        execution_fingerprint="fp-golden-001",
    )


def _make_effective_config_artifact_payload() -> dict[str, object]:
    service = EffectiveConfigService()
    artifact = service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={
            "pipeline": {"name": "chembl_activity", "version": "1.0.0"},
            "settings": {"limit": 25, "exact_replay": True},
        },
        runtime_overrides={
            "cli": {"limit": 25},
            "runtime": {"exact_replay": True},
        },
        source_refs=[
            ConfigSourceRef(
                source_type="file",
                source_path="configs/entities/chembl/activity.yaml",
                source_hash="1" * 64,
                raw_source_hash="2" * 64,
                priority=10,
            )
        ],
    )
    payload = json.loads(service.serialize_artifact(artifact))
    payload["occurrence_envelope"] = {
        "created_at": _FIXED_TIME.isoformat(),
        "resolved_config_timestamp": _FIXED_TIME.isoformat(),
        "effective_execution_timestamp": _FIXED_TIME.isoformat(),
    }
    return payload


def _make_bronze_sidecar_payload() -> dict[str, object]:
    _prime_environment_metadata()
    context = _make_run_context(run_id="00000000-0000-0000-0000-000000000902")
    coordinator = MetadataCoordinator(context)
    source_metadata = SourceMetadata(
        type="api",
        url="https://www.ebi.ac.uk/chembl/api/data/activity",
        query_string="assay_type=B",
        input_snapshots=[
            InputSnapshotRef(
                snapshot_id="snapshot-golden-001",
                content_hash="f" * 64,
                immutable_uri="s3://bioetl-bronze/chembl/activity/batch-001.jsonl.zst",
                query_fingerprint="g" * 64,
                storage_provider="s3",
                object_bucket="bioetl-bronze",
                object_key="chembl/activity/batch-001.jsonl.zst",
                object_version_id="version-001",
                etag="etag-001",
                last_modified="2025-01-01T11:55:00Z",
                captured_at=datetime(2025, 1, 1, 11, 55, tzinfo=UTC),
            )
        ],
    )
    metadata = coordinator.create_bronze_metadata(
        BronzeMetadataInput(
            batch_id=BatchID(UUID("00000000-0000-0000-0000-000000000903")),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2025-01-01/batch-001.jsonl.zst",
            started_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
            completed_at=datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC),
            source_metadata=source_metadata,
        )
    )
    return metadata.model_dump(mode="json")


def _make_silver_sidecar_payload() -> dict[str, object]:
    _prime_environment_metadata()
    coordinator = MetadataCoordinator(
        _make_run_context(run_id="00000000-0000-0000-0000-000000000904")
    )
    bronze_ref = BronzeWriteResult(
        batch_id=BatchID(UUID("00000000-0000-0000-0000-000000000905")),
        relative_path="v1/chembl/activity/2025-01-01/batch-001.jsonl.zst",
        absolute_path="/data/bronze/chembl/activity/2025-01-01/batch-001.jsonl.zst",
        record_count=100,
        compressed_size=5000,
        uncompressed_size=10000,
        checksum_blake2="b" * 64,
    )
    metadata = coordinator.create_silver_metadata(
        SilverMetadataInput(
            table_path="silver/chembl/activity",
            primary_keys=["activity_chembl_id"],
            mode=SilverWriteMode.MERGE,
            records=[
                {
                    "activity_chembl_id": "CHEMBL25",
                    "standard_type": "IC50",
                    "standard_value": 42.0,
                }
            ],
            bronze_refs=[bronze_ref],
            version_before=3,
            version_after=4,
            transform_version="1.0.0",
            transform_steps=("normalize_values", "compute_content_hash"),
            dq_report_path="reports/silver_dq.json",
            partition_by=["standard_type"],
            started_at=_FIXED_TIME,
            completed_at=datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC),
            total_bytes=2048,
        )
    )
    return metadata.model_dump(mode="json")


def _make_gold_sidecar_payload() -> dict[str, object]:
    _prime_environment_metadata()
    coordinator = MetadataCoordinator(
        _make_run_context(run_id="00000000-0000-0000-0000-000000000906")
    )
    metadata = coordinator.create_gold_metadata(
        GoldMetadataInput(
            table_path="gold/chembl/activity",
            table_name="chembl.activity",
            mode=GoldWriteMode.OVERWRITE,
            records=[
                {
                    "activity_chembl_id": "CHEMBL25",
                    "standard_type": "IC50",
                    "activity_bucket": "potent",
                }
            ],
            started_at=_FIXED_TIME,
            completed_at=datetime(2025, 1, 1, 12, 0, 7, tzinfo=UTC),
            silver_refs=[
                SilverRef(
                    table_name="chembl.activity",
                    table_path="silver/chembl/activity",
                    delta_version=4,
                )
            ],
            transform_version="1.0.0",
            transform_steps=("project_gold_contract", "deduplicate"),
            dq_report_path="reports/gold_dq.json",
            total_bytes=1024,
            partition_count=1,
            schema_validation_enabled=True,
            schema_validation_strict=True,
            contract_ref="chembl.activity.gold",
            contract_version="1.2.0",
        )
    )
    return metadata.model_dump(mode="json", by_alias=True)


def _make_run_manifest_inspection_payload() -> dict[str, object]:
    store = _InMemoryRunManifestStore()
    manifest = _make_manifest()
    store.save(manifest)
    return RunManifestInspectionService(manifest_port=store).show(
        manifest.manifest_id
    ).to_dict()


def _make_composite_checkpoint_state_payload() -> dict[str, object]:
    state = CompositeCheckpointState(
        composite_name="publication_analytics",
        run_id="00000000-0000-0000-0000-000000000907",
        state=CompositePipelineState.ENRICHING,
        seed_completed=True,
        seed_result=SeedResult(
            pipeline_name="chembl_publication",
            records_extracted=120,
            records_silver=120,
            keys_generated=120,
            duration_seconds=3.5,
            started_at=_FIXED_TIME,
            completed_at=datetime(2025, 1, 1, 12, 0, 3, tzinfo=UTC),
        ),
        completed_dependencies=frozenset({"pubmed_publication"}),
        dependency_results={
            "pubmed_publication": DependencyResult(
                pipeline_name="pubmed_publication",
                status=DependencyStatus.SUCCESS,
                records_extracted=120,
                records_silver=118,
                duration_seconds=4.0,
                started_at=_FIXED_TIME,
                completed_at=datetime(2025, 1, 1, 12, 0, 4, tzinfo=UTC),
            )
        },
        completed_enrichers=frozenset({"mesh"}),
        enrichment_results={
            "mesh": EnrichmentResult(
                enricher_name="mesh",
                status=EnrichmentStatus.PARTIAL,
                records_input=118,
                records_enriched=110,
                records_not_found=8,
                dq_error_rate=0.02,
                duration_seconds=2.0,
                started_at=datetime(2025, 1, 1, 12, 0, 4, tzinfo=UTC),
                completed_at=datetime(2025, 1, 1, 12, 0, 6, tzinfo=UTC),
            )
        },
        merge_completed=False,
        checkpoint_schema_version="1.0.0",
        effective_config_hash="c" * 64,
        effective_config_artifact_id="eca-golden-001",
        execution_fingerprint="fp-golden-001",
        dq_contract_compatibility_hash="e" * 64,
        contract_ref="composite.publication",
        contract_version="1.0.0",
        manifest_id="manifest-golden-001",
        composite_run_identity="composite-publication-golden-001",
        last_event_id="entry-003",
        last_event_occurred_at=datetime(2025, 1, 1, 12, 0, 6, tzinfo=UTC),
        created_at=_FIXED_TIME,
        updated_at=datetime(2025, 1, 1, 12, 0, 6, tzinfo=UTC),
    )
    return state.to_dict()


def test_effective_config_artifact_golden_fixture() -> None:
    _assert_matches_fixture(
        "effective_config_artifact_v1",
        _make_effective_config_artifact_payload(),
    )


def test_run_manifest_golden_fixture() -> None:
    _assert_matches_fixture("run_manifest_v1", _make_manifest().to_dict())


def test_bronze_sidecar_golden_fixture() -> None:
    _assert_matches_fixture("bronze_sidecar_v1", _make_bronze_sidecar_payload())


def test_silver_sidecar_golden_fixture() -> None:
    _assert_matches_fixture("silver_sidecar_v1", _make_silver_sidecar_payload())


def test_gold_sidecar_golden_fixture() -> None:
    _assert_matches_fixture("gold_sidecar_v1", _make_gold_sidecar_payload())


def test_run_manifest_inspection_golden_fixture() -> None:
    _assert_matches_fixture(
        "run_manifest_inspection_v1",
        _make_run_manifest_inspection_payload(),
    )


def test_composite_checkpoint_state_golden_fixture() -> None:
    _assert_matches_fixture(
        "composite_checkpoint_state_v1",
        _make_composite_checkpoint_state_payload(),
    )


def test_diagnostics_summary_golden_fixture() -> None:
    _assert_matches_fixture(
        "diagnostics_summary_v1",
        build_diagnostics_summary(_make_manifest(), ()),
    )
