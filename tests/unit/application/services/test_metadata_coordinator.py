"""Unit tests for MetadataCoordinator service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bioetl.application.services.lineage import (
    MetadataCoordinator,
    MetadataLineageBundleResult,
)
from bioetl.domain.lineage import LineageEdgeType, LineageNodeType
from bioetl.domain.medallion import GoldWriteMode, Layer, SilverWriteMode
from bioetl.domain.models.metadata import (
    BronzeMetadata,
    CompositeOutputExt,
    GoldMetadata,
    InputSnapshotRef,
    RunTypeEnum,
    SilverMetadata,
    SourceMetadata,
)
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
    SilverRef,
)
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite
_FIXED_TIME = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def run_context() -> RunContext:
    """Create a test RunContext."""
    return RunContext.create(
        run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
        run_type=RunType.INCREMENTAL,
        started_at=_FIXED_TIME,
        provider="chembl",
        entity="activity",
    )


@pytest.fixture
def coordinator(run_context: RunContext) -> MetadataCoordinator:
    """Create a MetadataCoordinator with test context."""
    # Reset environment cache before each test
    MetadataCoordinator.reset_environment_cache()
    return MetadataCoordinator(run_context)


class TestRunContext:
    """Tests for RunContext value object."""

    def test_create_with_valid_data(self) -> None:
        """Test creating RunContext with valid data."""
        run_id = RunID(deterministic_uuid_from_callsite("replay-sensitive"))
        started_at = _FIXED_TIME

        context = RunContext.create(
            run_id=run_id,
            run_type=RunType.BACKFILL,
            started_at=started_at,
            provider="pubchem",
            entity="compound",
        )

        assert context.run_id == run_id
        assert context.run_type == RunType.BACKFILL
        assert context.started_at == started_at
        assert context.provider == "pubchem"
        assert context.entity == "compound"
        assert context.pipeline_name == "pubchem_compound"

    def test_create_with_naive_datetime_raises(self) -> None:
        """Test that naive datetime raises ValueError."""
        with pytest.raises(ValueError, match="timezone-aware"):
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=datetime(2025, 1, 1, 12, 0),  # Naive datetime
                provider="chembl",
                entity="activity",
            )

    def test_create_with_empty_provider_raises(self) -> None:
        """Test that empty provider raises ValueError."""
        with pytest.raises(ValueError, match="provider cannot be empty"):
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="",
                entity="activity",
            )

    def test_create_with_empty_entity_raises(self) -> None:
        """Test that empty entity raises ValueError."""
        with pytest.raises(ValueError, match="entity cannot be empty"):
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="",
            )

    def test_context_is_immutable(self, run_context: RunContext) -> None:
        """Test that RunContext is immutable (frozen)."""
        with pytest.raises(AttributeError):
            run_context.provider = "new_provider"  # type: ignore[misc]


class TestMetadataCoordinator:
    """Tests for MetadataCoordinator service."""

    def test_run_context_accessible(self, coordinator: MetadataCoordinator) -> None:
        """Test that run_context is accessible."""
        assert coordinator.run_context is not None
        assert coordinator.run_context.provider == "chembl"
        assert coordinator.run_context.entity == "activity"

    def test_create_bronze_lineage_sidecar_projects_minimum_control_plane_anchors(
        self,
    ) -> None:
        """Legacy Bronze sidecar must carry the minimum control-plane anchors."""
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("bronze-sidecar")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            manifest_id="manifest-sidecar-001",
            execution_fingerprint="fingerprint-sidecar-001",
            effective_config_hash="e" * 64,
        )
        coordinator = MetadataCoordinator(context)

        sidecar = coordinator.create_bronze_lineage_sidecar(
            provider="chembl",
            entity="activity",
            batch_id=BatchID("batch-001"),
            ingestion_ts=_FIXED_TIME,
        )

        assert sidecar["run_id"] == str(context.run_id)
        assert sidecar["manifest_id"] == "manifest-sidecar-001"
        assert sidecar["execution_fingerprint"] == "fingerprint-sidecar-001"
        assert sidecar["effective_config_hash"] == "e" * 64
        assert sidecar["sidecar_truth_boundary"] == (
            "legacy_lineage_projection_non_authoritative"
        )
        assert "run_manifest" in sidecar["authoritative_replay_artifacts"]

    def test_environment_metadata_cached(self, run_context: RunContext) -> None:
        """Test that environment metadata is cached at class level."""
        MetadataCoordinator.reset_environment_cache()

        coord1 = MetadataCoordinator(run_context)
        env1 = coord1._get_environment_metadata()

        coord2 = MetadataCoordinator(run_context)
        env2 = coord2._get_environment_metadata()

        # Should be the exact same object (cached)
        assert env1 is env2

    def test_environment_metadata_has_all_fields(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that environment metadata contains all required fields."""
        env = coordinator._get_environment_metadata()

        assert env.hostname
        assert env.python_version
        assert env.bioetl_version

    def test_strict_profiles_require_manifest_closure_for_bronze_bundle(self) -> None:
        """Replay-grade persistence profiles must fail closed without manifest_id."""
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("strict-lineage")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            required_persistence_profile="replay_ready",
        )
        coordinator = MetadataCoordinator(context)
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("strict-bronze-batch")),
            record_count=10,
            compressed_size=512,
            output_path="v1/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )

        with pytest.raises(
            ValueError,
            match=r"Strict sidecar lineage closure requires runtime\.manifest_id",
        ):
            coordinator.create_bronze_metadata_bundle(input_data)

    def test_degraded_profile_allows_bronze_bundle_without_manifest_id(self) -> None:
        """Degraded observable runs may emit sidecars without strict manifest closure."""
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("degraded-lineage")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            required_persistence_profile="degraded_observable",
        )
        coordinator = MetadataCoordinator(context)
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("degraded-bronze-batch")),
            record_count=10,
            compressed_size=512,
            output_path="v1/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )

        bundle = coordinator.create_bronze_metadata_bundle(input_data)

        assert isinstance(bundle, MetadataLineageBundleResult)


class TestBronzeMetadata:
    """Tests for Bronze metadata creation."""

    def test_create_bronze_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test creating Bronze metadata."""
        started_at = _FIXED_TIME
        completed_at = started_at + timedelta(seconds=5.5)

        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=1000,
            compressed_size=50000,
            output_path="v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            started_at=started_at,
            completed_at=completed_at,
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert isinstance(metadata, BronzeMetadata)
        assert metadata.layer == Layer.BRONZE
        assert metadata.version == "1.1"  # ADR-029 version bump
        assert metadata.output.artifact_id == f"bronze_batch:{input_data.batch_id}"
        assert isinstance(metadata.output.content_hash, str)
        assert len(metadata.output.content_hash) == 64
        int(metadata.output.content_hash, 16)

    def test_bronze_output_content_hash_is_deterministic(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Bronze output content_hash should track semantic emitted file identity."""
        started_at = _FIXED_TIME
        completed_at = started_at + timedelta(seconds=1)
        batch_id = BatchID(deterministic_uuid_from_callsite("replay-sensitive"))
        input_data = BronzeMetadataInput(
            batch_id=batch_id,
            record_count=1000,
            compressed_size=50000,
            output_path="v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            started_at=started_at,
            completed_at=completed_at,
            output_content_hash="a" * 64,
        )
        same_input = BronzeMetadataInput(
            batch_id=batch_id,
            record_count=1000,
            compressed_size=50000,
            output_path="v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            started_at=started_at,
            completed_at=completed_at,
            output_content_hash="a" * 64,
        )
        same_content_different_path = BronzeMetadataInput(
            batch_id=batch_id,
            record_count=1000,
            compressed_size=50000,
            output_path="v1/chembl/activity/2024-01-15/batch_456.jsonl.zst",
            started_at=started_at,
            completed_at=completed_at,
            output_content_hash="a" * 64,
        )
        changed_input = BronzeMetadataInput(
            batch_id=batch_id,
            record_count=1000,
            compressed_size=50000,
            output_path="v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            started_at=started_at,
            completed_at=completed_at,
            output_content_hash="b" * 64,
        )

        first = coordinator.create_bronze_metadata(input_data)
        second = coordinator.create_bronze_metadata(same_input)
        moved = coordinator.create_bronze_metadata(same_content_different_path)
        changed = coordinator.create_bronze_metadata(changed_input)

        assert first.output.content_hash == second.output.content_hash
        assert first.output.content_hash == moved.output.content_hash
        assert first.output.content_hash != changed.output.content_hash

    def test_bronze_runtime_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Bronze runtime metadata contains correct values."""
        started_at = _FIXED_TIME
        completed_at = started_at + timedelta(seconds=3.0)

        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=started_at,
            completed_at=completed_at,
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert metadata.runtime.run_id == str(coordinator.run_context.run_id)
        assert metadata.runtime.run_type == RunTypeEnum.INCREMENTAL
        assert metadata.runtime.started_at_utc == started_at
        assert metadata.runtime.completed_at_utc == completed_at
        assert metadata.runtime.duration_seconds == pytest.approx(3.0)
        assert metadata.runtime.exact_replay is False
        assert metadata.runtime.replay_of_run_id is None
        assert metadata.runtime.replay_of_manifest_id is None
        assert metadata.runtime.input_snapshot_fingerprint is None
        assert metadata.output.artifact_id == f"bronze_batch:{input_data.batch_id}"

    def test_bronze_runtime_metadata_carries_replay_parentage_and_snapshot_fingerprint(
        self,
    ) -> None:
        """Bronze sidecars should expose exact replay parentage and snapshot identity."""
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            exact_replay=True,
            replay_of_run_id="run-parent-1",
            replay_of_manifest_id="manifest-parent-1",
        )
        coordinator = MetadataCoordinator(context)
        snapshot = InputSnapshotRef(
            snapshot_id="snapshot-1",
            content_hash="sha256:snapshot-1",
            immutable_uri="file:///immutable/snapshot-1.json",
        )
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME + timedelta(seconds=1),
            source_metadata=SourceMetadata(
                type="api",
                input_snapshots=[snapshot],
            ),
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert metadata.runtime.exact_replay is True
        assert metadata.runtime.replay_of_run_id == "run-parent-1"
        assert metadata.runtime.replay_of_manifest_id == "manifest-parent-1"
        assert metadata.runtime.input_snapshot_fingerprint == (
            compute_input_snapshot_identity_fingerprint([snapshot])
        )

    def test_bronze_pipeline_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Bronze pipeline metadata uses context values."""
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert metadata.pipeline.name == "chembl_activity"
        assert metadata.pipeline.provider == "chembl"
        assert metadata.pipeline.entity == "activity"

    def test_bronze_pipeline_metadata_includes_contract_identity(self) -> None:
        """Bronze pipeline metadata should expose resolved contract identity fields."""
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            dependency_lock_hash="sha256:deps-001",
            config_hash="a" * 64,
            effective_config_hash="b" * 64,
            effective_config_artifact_id="artifact-001",
            execution_fingerprint="fingerprint-001",
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            contract_schema_hash="schema-hash-123",
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1.0",
            dq_contract_compatibility_hash="dq-hash-001",
        )
        coordinator = MetadataCoordinator(context)
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=25,
            compressed_size=2048,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert metadata.pipeline.dependency_lock_hash == "sha256:deps-001"
        assert metadata.pipeline.config_hash == "a" * 64
        assert metadata.pipeline.effective_config_hash == "b" * 64
        assert metadata.pipeline.effective_config_artifact_id == "artifact-001"
        assert metadata.pipeline.execution_fingerprint == "fingerprint-001"
        assert metadata.pipeline.contract_ref == "chembl.activity"
        assert metadata.pipeline.contract_version == "1.0.0"
        assert metadata.pipeline.contract_schema_hash == "schema-hash-123"
        assert metadata.pipeline.dq_policy_ref == "chembl.dq.v1"
        assert metadata.pipeline.rule_bundle_version == "dq-rules.v1.0"
        assert metadata.pipeline.dq_contract_compatibility_hash == "dq-hash-001"

    def test_bronze_pipeline_metadata_does_not_alias_effective_hash(self) -> None:
        """Sidecar metadata keeps legacy config_hash separate from effective hash."""
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            config_hash="legacy-config-hash",
            resolved_config_hash="resolved-config-hash",
            effective_config_hash=None,
        )
        coordinator = MetadataCoordinator(context)
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=25,
            compressed_size=2048,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert metadata.pipeline.config_hash == "legacy-config-hash"
        assert metadata.pipeline.resolved_config_hash == "resolved-config-hash"
        assert metadata.pipeline.effective_config_hash is None

    def test_bronze_output_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Bronze output metadata contains file info (ADR-029 unified structure)."""
        started_at = _FIXED_TIME
        completed_at = started_at

        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=500,
            compressed_size=25000,
            output_path="v1/chembl/activity/2024-01-15/batch_abc.jsonl.zst",
            started_at=started_at,
            completed_at=completed_at,
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        # Unified output (ADR-029)
        assert metadata.output.record_count == 500
        assert metadata.output.total_bytes == 25000
        assert metadata.output.write_started_at == started_at
        assert metadata.output.write_completed_at == completed_at

        # Bronze-specific extension
        assert len(metadata.output_ext.files) == 1
        assert metadata.output_ext.files[0].path == input_data.output_path
        assert metadata.output_ext.files[0].record_count == 500

    def test_bronze_metadata_includes_query_string_from_input(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Bronze metadata should include query_string from BronzeMetadataInput."""
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
            query_string="assay_type=B&standard_type=IC50",
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert metadata.source.query_string == "assay_type=B&standard_type=IC50"

    def test_bronze_metadata_preserves_source_query_string(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Should preserve query_string from source_metadata if already set."""
        source = SourceMetadata(
            type="api",
            url="https://www.ebi.ac.uk/chembl/api/data/activity",
            query_string="original_query=value",
        )
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
            source_metadata=source,
            query_string="override_query=should_be_ignored",
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        # Original query_string from source_metadata should be preserved
        assert metadata.source.query_string == "original_query=value"

    def test_bronze_metadata_injects_query_string_when_source_has_none(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Should inject query_string into source_metadata if source has query_string=None."""
        source = SourceMetadata(
            type="api",
            url="https://www.ebi.ac.uk/chembl/api/data/activity",
            # query_string is None by default
        )
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
            source_metadata=source,
            query_string="injected_query=value",
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        # query_string should be injected from input_data
        assert metadata.source.query_string == "injected_query=value"
        # Other source_metadata fields should be preserved
        assert metadata.source.url == "https://www.ebi.ac.uk/chembl/api/data/activity"

    def test_bronze_metadata_preserves_input_snapshot_refs(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Bronze metadata should persist immutable input snapshot references."""
        source = SourceMetadata(
            type="api",
            url="https://www.ebi.ac.uk/chembl/api/data/activity",
            input_snapshots=[
                InputSnapshotRef(
                    snapshot_id="chembl-activity-batch-001",
                    content_hash="a" * 64,
                    immutable_uri="snapshots/chembl/activity/batch-001.jsonl.zst",
                    query_fingerprint="f" * 64,
                    storage_provider="s3",
                    object_bucket="bioetl-bronze",
                    object_key="chembl/activity/batch-001.jsonl.zst",
                    object_version_id="version-001",
                )
            ],
        )
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
            source_metadata=source,
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert len(metadata.source.input_snapshots) == 1
        assert metadata.source.input_snapshots[0].snapshot_id == (
            "chembl-activity-batch-001"
        )
        assert metadata.source.input_snapshots[0].content_hash == "a" * 64
        assert metadata.source.input_snapshots[0].storage_provider == "s3"
        assert metadata.source.input_snapshots[0].object_bucket == "bioetl-bronze"
        assert (
            metadata.source.input_snapshots[0].object_key
            == "chembl/activity/batch-001.jsonl.zst"
        )
        assert metadata.source.input_snapshots[0].object_version_id == "version-001"

    def test_bronze_metadata_query_string_defaults_to_none(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Bronze metadata query_string should default to None when not provided."""
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
            # No query_string provided
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert metadata.source.query_string is None


class TestSourceMetadataQueryString:
    """Tests for SourceMetadata query_string field."""

    def test_source_metadata_with_query_string(self) -> None:
        """SourceMetadata should store query_string."""
        source = SourceMetadata(
            type="api",
            url="https://www.ebi.ac.uk/chembl/api/data/activity",
            query_string="assay_type=B&standard_type=IC50",
        )

        assert source.query_string == "assay_type=B&standard_type=IC50"
        assert source.type == "api"

    def test_source_metadata_query_string_default_none(self) -> None:
        """SourceMetadata.query_string defaults to None."""
        source = SourceMetadata(type="api")

        assert source.query_string is None

    def test_source_metadata_model_copy_with_query_string(self) -> None:
        """SourceMetadata.model_copy should work with query_string update."""
        source = SourceMetadata(
            type="api",
            url="https://example.com",
        )

        updated = source.model_copy(update={"query_string": "new_query=value"})

        assert updated.query_string == "new_query=value"
        assert updated.url == "https://example.com"  # Original preserved
        assert source.query_string is None  # Original unchanged


class TestSilverMetadata:
    """Tests for Silver metadata creation."""

    def test_pipeline_metadata_carries_normalization_profile_identity(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            normalization_profile_ref="chembl.activity",
            normalization_profile_version="2.0.0",
            normalization_profile_hash="a" * 64,
        )
        metadata = MetadataCoordinator(context).create_silver_metadata(
            SilverMetadataInput(
                table_path="/data/silver/chembl/activity",
                records=[
                    {
                        "_run_id": str(context.run_id),
                        "_run_type": "incremental",
                        "_source_batch_id": str(
                            deterministic_uuid_from_callsite("replay-sensitive")
                        ),
                        "_ingestion_ts": _FIXED_TIME.isoformat(),
                        "chembl_id": "CHEMBL123",
                    }
                ],
                primary_keys=["chembl_id"],
                mode=SilverWriteMode.MERGE,
                dq_metrics=None,
                started_at=_FIXED_TIME,
                completed_at=_FIXED_TIME,
            )
        )

        assert metadata.pipeline.normalization_profile_ref == "chembl.activity"
        assert metadata.pipeline.normalization_profile_version == "2.0.0"
        assert metadata.pipeline.normalization_profile_hash == "a" * 64

    def test_create_silver_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test creating Silver metadata."""
        records = [
            {
                "_run_id": str(coordinator.run_context.run_id),
                "_run_type": "incremental",
                "_source_batch_id": str(
                    deterministic_uuid_from_callsite("replay-sensitive")
                ),
                "_ingestion_ts": _FIXED_TIME.isoformat(),
                "chembl_id": "CHEMBL123",
            }
        ]

        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["chembl_id"],
            mode=SilverWriteMode.MERGE,
            version_after=5,
        )

        metadata = coordinator.create_silver_metadata(input_data)

        assert isinstance(metadata, SilverMetadata)
        assert metadata.layer == Layer.SILVER
        assert metadata.version == "1.1"  # ADR-029 version bump

    def test_silver_with_empty_records_raises(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that empty records raises ValueError."""
        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=[],
            primary_keys=["chembl_id"],
            mode=SilverWriteMode.MERGE,
        )

        with pytest.raises(ValueError, match="without records"):
            coordinator.create_silver_metadata(input_data)

    def test_silver_lineage_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Silver lineage metadata extracts batch IDs."""
        batch_id_1 = str(deterministic_uuid_from_callsite("replay-sensitive"))
        batch_id_2 = str(deterministic_uuid_from_callsite("replay-sensitive"))
        records = [
            {"_source_batch_id": batch_id_1, "id": 1},
            {"_source_batch_id": batch_id_2, "id": 2},
            {"_source_batch_id": batch_id_1, "id": 3},  # Duplicate batch_id
        ]

        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )

        metadata = coordinator.create_silver_metadata(input_data)

        # Should deduplicate batch IDs
        assert len(metadata.lineage.source_batch_ids) == 2
        assert batch_id_1 in metadata.lineage.source_batch_ids
        assert batch_id_2 in metadata.lineage.source_batch_ids

    def test_silver_delta_metrics(self, coordinator: MetadataCoordinator) -> None:
        """Test Silver Delta metrics."""
        records = [{"id": i} for i in range(10)]

        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.APPEND,
            version_after=10,
        )

        metadata = coordinator.create_silver_metadata(input_data)

        assert metadata.delta.operation == "append"
        assert metadata.delta.primary_key == ["id"]
        assert metadata.delta.version_after == 10
        assert metadata.delta.rows_inserted == 10

    def test_silver_metadata_includes_rule_provenance(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Silver metadata should include DQ rule provenance when provided."""
        records = [{"id": 1}]
        provenance = [
            {
                "rule_id": "R_TRACE_01",
                "config_path": "configs/entities/chembl/activity.yaml",
                "layer": "gold",
                "field": "value",
                "severity": "error",
                "decision": "quarantine",
            }
        ]

        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            dq_rule_provenance=provenance,
        )

        metadata = coordinator.create_silver_metadata(input_data)

        assert metadata.dq_summary.rule_provenance == provenance

    def test_silver_metadata_surfaces_composite_cv_trace_in_dq_summary(self) -> None:
        """Composite CV markers should become DQ summary counts and provenance."""
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="composite",
            entity="publication",
            contract_version="2.0.0",
        )
        coordinator = MetadataCoordinator(context)
        input_data = SilverMetadataInput(
            table_path="/data/silver/composite/publication",
            records=[
                {"id": 1, "_cv_warn": True},
                {"id": 2, "_cv_error": True, "_cv_quarantine": True},
            ],
            primary_keys=["id"],
            mode=SilverWriteMode.DELETE,
            dq_report_path="reports/dq/composite-publication.json",
        )

        metadata = coordinator.create_silver_metadata(input_data)

        assert metadata.dq_summary.warning_records == 1
        assert metadata.dq_summary.error_records == 1
        assert metadata.dq_summary.valid_records == 1
        assert metadata.dq_summary.validation_passed is False
        assert metadata.dq_summary.error_rate == pytest.approx(0.5)
        assert metadata.dq_summary.rule_provenance == [
            {
                "rule_id": "composite.cross_validation.warning",
                "contract_version": "2.0.0",
                "config_path": "cross_validation",
                "layer": "composite",
                "field": None,
                "severity": "warning",
                "decision": "warn",
                "violation_kind": "cross_validation_mismatch",
                "report_artifact_path": "reports/dq/composite-publication.json",
                "record_count": "1",
            },
            {
                "rule_id": "composite.cross_validation.quarantine",
                "contract_version": "2.0.0",
                "config_path": "cross_validation",
                "layer": "composite",
                "field": None,
                "severity": "error",
                "decision": "quarantine",
                "violation_kind": "cross_validation_mismatch",
                "report_artifact_path": "reports/dq/composite-publication.json",
                "record_count": "1",
            },
        ]

    def test_silver_mode_to_operation_mapping(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Silver write mode to Delta operation mapping."""
        records = [{"id": 1}]

        # Test MERGE mode
        input_merge = SilverMetadataInput(
            table_path="/data/silver/t",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )
        assert (
            coordinator.create_silver_metadata(input_merge).delta.operation == "merge"
        )

        # Test APPEND mode
        input_append = SilverMetadataInput(
            table_path="/data/silver/t",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.APPEND,
        )
        assert (
            coordinator.create_silver_metadata(input_append).delta.operation == "append"
        )

        # Test DELETE mode (maps to overwrite)
        input_delete = SilverMetadataInput(
            table_path="/data/silver/t",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.DELETE,
        )
        assert (
            coordinator.create_silver_metadata(input_delete).delta.operation
            == "overwrite"
        )


class TestGoldMetadata:
    """Tests for Gold metadata creation."""

    def test_create_gold_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test creating Gold metadata."""
        records = [{"compound_id": "CMP123", "activity_value": 5.5}]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert isinstance(metadata, GoldMetadata)
        assert metadata.layer == Layer.GOLD
        assert metadata.version == "1.1"  # ADR-029 version bump

    def test_gold_with_empty_records_raises(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that empty records raises ValueError."""
        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=[],
            mode=GoldWriteMode.OVERWRITE,
        )

        with pytest.raises(ValueError, match="without records"):
            coordinator.create_gold_metadata(input_data)

    def test_gold_scd2_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Gold SCD2 metadata creation."""
        records = [{"compound_id": "CMP123", "value": 1.0}]
        scd_config = {
            "valid_from_col": "effective_from",
            "valid_to_col": "effective_to",
            "current_flag_col": "is_active",
        }

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.SCD2,
            scd_config=scd_config,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.scd is not None
        assert metadata.scd.enabled is True
        assert metadata.scd.effective_date_column == "effective_from"
        assert metadata.scd.end_date_column == "effective_to"
        assert metadata.scd.current_flag_column == "is_active"

    def test_gold_without_scd2_has_no_scd_metadata(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Gold without SCD2 mode has no SCD metadata."""
        records = [{"id": 1}]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.APPEND,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.scd is None

    def test_gold_output_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Gold output metadata."""
        records = [{"id": i} for i in range(25)]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.output.record_count == 25

    def test_gold_composite_output_extension(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test composite records are mapped to CompositeOutputExt metadata."""
        records = [
            {
                "id": 1,
                "_source_providers": "['seed', 'openalex']",
                "_enrichment_status": "{'openalex': 'ok'}",
            }
        ]

        input_data = GoldMetadataInput(
            table_path="/data/gold/composite/publication",
            table_name="composite.publication",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            composite_run_id="comp-run-123",
            lineage_created_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            schema_validation_enabled=True,
            schema_validation_strict=True,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.output.composite_run_id == "comp-run-123"
        assert isinstance(metadata.output_ext, CompositeOutputExt)
        assert metadata.output_ext.composite_run_id == "comp-run-123"
        assert metadata.output_ext.source_providers == ["seed", "openalex"]
        assert metadata.output_ext.enrichment_status == {"openalex": "ok"}
        assert metadata.output_ext.schema_validation.enabled is True
        assert metadata.output_ext.schema_validation.strict is True
        assert metadata.output_ext.schema_validation.status == "passed"

    def test_gold_lineage_with_silver_refs(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Gold lineage metadata with Silver source references (REQ-LINEAGE-002)."""
        records = [{"compound_id": "CMP123", "activity_value": 5.5}]
        silver_refs = [
            SilverRef(
                table_name="chembl.activity",
                table_path="/data/silver/chembl/activity",
                delta_version=42,
            )
        ]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=silver_refs,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.lineage.source_tables == {"chembl.activity": 42}

    def test_gold_lineage_without_silver_refs(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Gold lineage metadata is empty when no Silver refs provided (backward compat)."""
        records = [{"id": 1}]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=None,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.lineage.source_tables == {}

    def test_gold_lineage_with_multiple_silver_sources(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Gold lineage with multiple Silver table sources."""
        records = [{"compound_id": "CMP123", "target_id": "TGT456", "activity": 1.0}]
        silver_refs = [
            SilverRef(
                table_name="chembl.compound",
                table_path="/data/silver/chembl/compound",
                delta_version=10,
            ),
            SilverRef(
                table_name="chembl.target",
                table_path="/data/silver/chembl/target",
                delta_version=20,
            ),
            SilverRef(
                table_name="chembl.activity",
                table_path="/data/silver/chembl/activity",
                delta_version=30,
            ),
        ]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/compound_activity",
            table_name="chembl.compound_activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=silver_refs,
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.lineage.source_tables == {
            "chembl.compound": 10,
            "chembl.target": 20,
            "chembl.activity": 30,
        }


class TestTransformVersionTracking:
    """Tests for transform version and steps tracking in metadata."""

    def test_silver_lineage_includes_transform_version_from_input(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Silver lineage includes transform_version from SilverMetadataInput."""
        records = [{"id": 1}]

        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            transform_version="1.0.0",
            transform_steps=("normalize_values", "add_metadata"),
        )

        metadata = coordinator.create_silver_metadata(input_data)

        assert metadata.lineage.transform_version == "1.0.0"
        assert metadata.lineage.transform_steps == ["normalize_values", "add_metadata"]

    def test_gold_lineage_includes_transform_version_from_input(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test Gold lineage includes transform_version from GoldMetadataInput."""
        records = [{"id": 1}]

        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            transform_version="2.1.0",
            transform_steps=("flatten_json", "validate_schema"),
        )

        metadata = coordinator.create_gold_metadata(input_data)

        assert metadata.lineage.transform_version == "2.1.0"
        assert metadata.lineage.transform_steps == ["flatten_json", "validate_schema"]

    def test_silver_uses_run_context_transform_when_input_none(self) -> None:
        """Test Silver falls back to RunContext transform info when input is None."""
        MetadataCoordinator.reset_environment_cache()

        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            transform_version="3.0.0",
            transform_steps=("step1", "step2", "step3"),
        )
        coord = MetadataCoordinator(context)

        records = [{"id": 1}]
        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            # transform_version and transform_steps are None
        )

        metadata = coord.create_silver_metadata(input_data)

        # Should fall back to RunContext values
        assert metadata.lineage.transform_version == "3.0.0"
        assert metadata.lineage.transform_steps == ["step1", "step2", "step3"]

    def test_gold_uses_run_context_transform_when_input_none(self) -> None:
        """Test Gold falls back to RunContext transform info when input is None."""
        MetadataCoordinator.reset_environment_cache()

        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            transform_version="4.0.0",
            transform_steps=("transform_step_a", "transform_step_b"),
        )
        coord = MetadataCoordinator(context)

        records = [{"id": 1}]
        input_data = GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            # transform_version and transform_steps are None
        )

        metadata = coord.create_gold_metadata(input_data)

        # Should fall back to RunContext values
        assert metadata.lineage.transform_version == "4.0.0"
        assert metadata.lineage.transform_steps == [
            "transform_step_a",
            "transform_step_b",
        ]

    def test_run_context_with_transform_info(self) -> None:
        """Test RunContext can be created with transform version and steps."""
        run_id = RunID(deterministic_uuid_from_callsite("replay-sensitive"))
        started_at = _FIXED_TIME

        context = RunContext.create(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            started_at=started_at,
            provider="chembl",
            entity="activity",
            transform_version="1.2.3",
            transform_steps=("step1", "step2"),
        )

        assert context.transform_version == "1.2.3"
        assert context.transform_steps == ("step1", "step2")

    def test_run_context_defaults_empty_transform(self) -> None:
        """Test RunContext defaults to None/empty for transform fields."""
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
        )

        assert context.transform_version is None
        assert context.transform_steps == ()

    def test_silver_input_takes_precedence_over_run_context(self) -> None:
        """Test that SilverMetadataInput values take precedence over RunContext."""
        MetadataCoordinator.reset_environment_cache()

        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            transform_version="1.0.0",
            transform_steps=("context_step",),
        )
        coord = MetadataCoordinator(context)

        records = [{"id": 1}]
        input_data = SilverMetadataInput(
            table_path="/data/silver/chembl/activity",
            records=records,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            transform_version="2.0.0",  # Different from context
            transform_steps=("input_step1", "input_step2"),  # Different from context
        )

        metadata = coord.create_silver_metadata(input_data)

        # Input values should take precedence
        assert metadata.lineage.transform_version == "2.0.0"
        assert metadata.lineage.transform_steps == ["input_step1", "input_step2"]


class TestRunTypeMappings:
    """Tests for RunType to RunTypeEnum mapping."""

    @pytest.mark.parametrize(
        "run_type,expected_enum",
        [
            (RunType.INCREMENTAL, RunTypeEnum.INCREMENTAL),
            (RunType.BACKFILL, RunTypeEnum.BACKFILL),
            (RunType.REBUILD, RunTypeEnum.REBUILD),
        ],
    )
    def test_run_type_mapping(
        self, run_type: RunType, expected_enum: RunTypeEnum
    ) -> None:
        """Test RunType to RunTypeEnum mapping."""
        MetadataCoordinator.reset_environment_cache()

        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=run_type,
            started_at=_FIXED_TIME,
            provider="test",
            entity="entity",
        )
        coordinator = MetadataCoordinator(context)

        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=1,
            compressed_size=100,
            output_path="path",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )

        metadata = coordinator.create_bronze_metadata(input_data)
        assert metadata.runtime.run_type == expected_enum


class TestConsistencyAcrossLayers:
    """Tests for metadata consistency across layers."""

    def test_run_id_consistent_across_layers(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that run_id is consistent across Bronze, Silver, Gold."""
        run_id_str = str(coordinator.run_context.run_id)

        # Bronze
        bronze_input = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=10,
            compressed_size=1000,
            output_path="path",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )
        bronze = coordinator.create_bronze_metadata(bronze_input)

        # Silver
        silver_input = SilverMetadataInput(
            table_path="/silver/t",
            records=[{"id": 1}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )
        silver = coordinator.create_silver_metadata(silver_input)

        # Gold
        gold_input = GoldMetadataInput(
            table_path="/gold/t",
            table_name="t",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
        )
        gold = coordinator.create_gold_metadata(gold_input)

        # All should have the same run_id
        assert bronze.runtime.run_id == run_id_str
        assert silver.runtime.run_id == run_id_str
        assert gold.runtime.run_id == run_id_str

    def test_pipeline_metadata_consistent_across_layers(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that pipeline metadata is consistent across layers."""
        bronze_input = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=10,
            compressed_size=1000,
            output_path="path",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )
        bronze = coordinator.create_bronze_metadata(bronze_input)

        silver_input = SilverMetadataInput(
            table_path="/silver/t",
            records=[{"id": 1}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )
        silver = coordinator.create_silver_metadata(silver_input)

        gold_input = GoldMetadataInput(
            table_path="/gold/t",
            table_name="t",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
        )
        gold = coordinator.create_gold_metadata(gold_input)

        # All should have consistent pipeline metadata
        assert (
            bronze.pipeline.provider
            == silver.pipeline.provider
            == gold.pipeline.provider
        )
        assert bronze.pipeline.entity == silver.pipeline.entity == gold.pipeline.entity
        assert bronze.pipeline.name == silver.pipeline.name == gold.pipeline.name

    def test_environment_metadata_consistent_across_layers(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Test that environment metadata is consistent (same object)."""
        bronze_input = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=10,
            compressed_size=1000,
            output_path="path",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )
        bronze = coordinator.create_bronze_metadata(bronze_input)

        silver_input = SilverMetadataInput(
            table_path="/silver/t",
            records=[{"id": 1}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )
        silver = coordinator.create_silver_metadata(silver_input)

        gold_input = GoldMetadataInput(
            table_path="/gold/t",
            table_name="t",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
        )
        gold = coordinator.create_gold_metadata(gold_input)

        # Environment should be the same cached object
        assert bronze.environment is silver.environment is gold.environment


class TestLineageFragments:
    """Tests for canonical lineage fragment assembly."""

    class _FakeGoldSchema:
        class Config:
            version = "7.0"
            strict = True

        @staticmethod
        def to_schema() -> object:
            class _Column:
                dtype = "string"
                nullable = False

            class _Schema:
                columns = {"compound_id": _Column()}

            return _Schema()

    def test_bronze_fragment_links_source_request_run_and_batch(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            manifest_id="manifest-001",
            execution_fingerprint="fingerprint-001",
            config_hash="a" * 64,
            effective_config_hash="b" * 64,
            effective_config_artifact_id="artifact-001",
            dq_contract_compatibility_hash="dq-hash-001",
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            contract_schema_hash="schema-hash-123",
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1.0",
        )
        coordinator = MetadataCoordinator(context)
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=50,
            compressed_size=1024,
            output_path="v1/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
            source_metadata=SourceMetadata(
                type="api",
                url="https://www.ebi.ac.uk/chembl/api/data/activity",
                query_string="assay_type=B",
                api_version="v33",
            ),
        )

        fragment = coordinator.build_bronze_lineage_fragment(input_data)

        node_types = {node.node_type for node in fragment.nodes}
        assert fragment.fragment_id.startswith("bronze:")
        assert fragment.manifest_id == "manifest-001"
        assert LineageNodeType.MANIFEST in node_types
        assert LineageNodeType.RUN in node_types
        assert LineageNodeType.SOURCE_SYSTEM in node_types
        assert LineageNodeType.SOURCE_REQUEST in node_types
        assert LineageNodeType.BRONZE_BATCH in node_types
        run = next(
            node for node in fragment.nodes if node.node_type == LineageNodeType.RUN
        )
        manifest = next(
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.MANIFEST
        )
        assert run.attributes["contract_ref"] == "chembl.activity"
        assert run.attributes["execution_fingerprint"] == "fingerprint-001"
        assert run.attributes["config_hash"] == "a" * 64
        assert run.attributes["effective_config_hash"] == "b" * 64
        assert run.attributes["effective_config_artifact_id"] == "artifact-001"
        assert run.attributes["dq_contract_compatibility_hash"] == "dq-hash-001"
        assert run.attributes["contract_version"] == "1.0.0"
        assert run.attributes["contract_schema_hash"] == "schema-hash-123"
        assert run.attributes["dq_policy_ref"] == "chembl.dq.v1"
        assert run.attributes["rule_bundle_version"] == "dq-rules.v1.0"
        assert manifest.attributes["contract_ref"] == "chembl.activity"
        assert manifest.attributes["execution_fingerprint"] == "fingerprint-001"
        assert manifest.attributes["config_hash"] == "a" * 64
        assert manifest.attributes["effective_config_hash"] == "b" * 64
        assert manifest.attributes["effective_config_artifact_id"] == "artifact-001"
        assert manifest.attributes["dq_contract_compatibility_hash"] == "dq-hash-001"
        assert manifest.attributes["contract_version"] == "1.0.0"
        assert any(
            edge.edge_type == LineageEdgeType.PRODUCED_BY for edge in fragment.edges
        )
        assert any(
            edge.edge_type == LineageEdgeType.EXPLAINS for edge in fragment.edges
        )

    def test_bronze_fragment_id_is_stable_across_run_ids(self) -> None:
        """Bronze fragment identity must not depend on run_id."""
        batch_id = BatchID(deterministic_uuid_from_callsite("replay-sensitive"))
        input_data = BronzeMetadataInput(
            batch_id=batch_id,
            record_count=50,
            compressed_size=1024,
            output_path="v1/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
            source_metadata=SourceMetadata(
                type="api",
                url="https://www.ebi.ac.uk/chembl/api/data/activity",
                query_string="assay_type=B",
                api_version="v33",
            ),
        )
        fragment_first = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
            )
        ).build_bronze_lineage_fragment(input_data)
        fragment_second = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
            )
        ).build_bronze_lineage_fragment(input_data)

        assert fragment_first.fragment_id == fragment_second.fragment_id

    def test_silver_fragment_uses_bronze_refs_and_transform_chain(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            transform_version="2.1.0",
            transform_steps=("normalize", "validate"),
        )
        coordinator = MetadataCoordinator(context)
        bronze_ref = BronzeWriteResult(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            relative_path="chembl/activity/2026-03-24/batch-1.jsonl.zst",
            absolute_path="/data/output/bronze/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            record_count=25,
            compressed_size=100,
            uncompressed_size=300,
            checksum_blake2="abc123",
        )
        input_data = SilverMetadataInput(
            table_path="/data/output/silver/chembl/activity",
            records=[{"id": 1, "_source_batch_id": str(bronze_ref.batch_id)}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=[bronze_ref],
            version_after=7,
        )

        fragment = coordinator.build_silver_lineage_fragment(input_data)

        dataset_nodes = [
            node for node in fragment.nodes if node.node_type == LineageNodeType.DATASET
        ]
        transform_nodes = [
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.TRANSFORM
        ]
        assert fragment.fragment_id.startswith("silver:")
        assert len(dataset_nodes) == 1
        assert dataset_nodes[0].node_id == "silver:chembl.activity@7"
        assert len(transform_nodes) == 2
        assert any(
            edge.edge_type == LineageEdgeType.DERIVED_FROM
            and edge.target.node_type == LineageNodeType.BRONZE_BATCH
            for edge in fragment.edges
        )
        assert any(
            edge.edge_type == LineageEdgeType.PRODUCED_BY
            and edge.target.node_type == LineageNodeType.TRANSFORM
            for edge in fragment.edges
        )

    def test_silver_fragment_id_is_stable_across_run_ids(self) -> None:
        """Silver fragment identity must not depend on run_id."""
        bronze_ref = BronzeWriteResult(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            relative_path="chembl/activity/2026-03-24/batch-1.jsonl.zst",
            absolute_path="/data/output/bronze/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            record_count=25,
            compressed_size=100,
            uncompressed_size=300,
            checksum_blake2="abc123",
        )
        input_data = SilverMetadataInput(
            table_path="/data/output/silver/chembl/activity",
            records=[{"id": 1, "_source_batch_id": str(bronze_ref.batch_id)}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=[bronze_ref],
            version_after=7,
        )
        fragment_first = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
                transform_version="2.1.0",
                transform_steps=("normalize", "validate"),
            )
        ).build_silver_lineage_fragment(input_data)
        fragment_second = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
                transform_version="2.1.0",
                transform_steps=("normalize", "validate"),
            )
        ).build_silver_lineage_fragment(input_data)

        assert fragment_first.fragment_id == fragment_second.fragment_id

    def test_silver_fragment_exposes_composite_source_and_cv_summary(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="composite",
            entity="publication",
        )
        coordinator = MetadataCoordinator(context)
        input_data = SilverMetadataInput(
            table_path="/data/output/silver/composite/publication",
            records=[
                {
                    "id": 1,
                    "_source_providers": "['seed', 'crossref']",
                    "_enrichment_status": "{'crossref': 'success'}",
                    "_field_sources": "{'doi': 'seed', 'title': 'crossref'}",
                    "_seed_record_id": "seed-123",
                    "_cv_warn": True,
                },
                {
                    "id": 2,
                    "_field_sources": "{'abstract': 'crossref'}",
                    "_cv_error": True,
                    "_cv_quarantine": True,
                },
            ],
            primary_keys=["id"],
            mode=SilverWriteMode.DELETE,
            version_after=11,
            composite_run_id="comp-run-456",
        )

        fragment = coordinator.build_silver_lineage_fragment(input_data)

        silver_dataset = next(
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.DATASET
            and node.node_id == "silver:composite.publication@11"
        )
        crossref_source = next(
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.SOURCE_SYSTEM
            and node.node_id == "source_system:crossref"
        )

        assert silver_dataset.attributes["composite_run_id"] == "comp-run-456"
        assert silver_dataset.attributes["source_providers"] == ["seed", "crossref"]
        assert silver_dataset.attributes["provider_fields"] == {
            "crossref": ["abstract", "title"],
            "seed": ["doi"],
        }
        assert silver_dataset.attributes["cv_warn_count"] == 1
        assert silver_dataset.attributes["cv_error_count"] == 1
        assert silver_dataset.attributes["cv_quarantine_count"] == 1
        assert crossref_source.attributes["selected_fields"] == ["abstract", "title"]
        assert any(
            edge.edge_type == LineageEdgeType.DERIVED_FROM
            and edge.source.node_id == silver_dataset.node_id
            and edge.target.node_id == crossref_source.node_id
            for edge in fragment.edges
        )

    def test_gold_fragment_links_silver_refs_schema_and_transforms(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.REBUILD,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            transform_version="3.0.0",
            transform_steps=("merge", "rank"),
            manifest_id="manifest-002",
        )
        coordinator = MetadataCoordinator(context)
        silver_ref = SilverRef(
            table_name="chembl.activity",
            table_path="/data/output/silver/chembl/activity",
            delta_version=9,
        )
        input_data = GoldMetadataInput(
            table_path="/data/output/gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=[silver_ref],
            gold_schema=self._FakeGoldSchema,
        )

        fragment = coordinator.build_gold_lineage_fragment(input_data)

        node_types = {node.node_type for node in fragment.nodes}
        assert fragment.fragment_id.startswith("gold:")
        assert LineageNodeType.DATASET in node_types
        assert LineageNodeType.SCHEMA in node_types
        assert LineageNodeType.TRANSFORM in node_types
        assert LineageNodeType.MANIFEST in node_types
        assert any(
            edge.edge_type == LineageEdgeType.DERIVED_FROM
            and edge.target.node_id == "silver:chembl.activity@9"
            for edge in fragment.edges
        )
        assert any(
            edge.edge_type == LineageEdgeType.USED_SCHEMA
            and edge.target.node_type == LineageNodeType.SCHEMA
            for edge in fragment.edges
        )
        assert any(
            edge.edge_type == LineageEdgeType.EXPLAINS for edge in fragment.edges
        )

    def test_gold_fragment_id_is_stable_across_run_ids(self) -> None:
        """Gold fragment identity must not depend on run_id."""
        input_data = GoldMetadataInput(
            table_path="/data/output/gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=[
                SilverRef(
                    table_name="chembl.activity",
                    table_path="/data/output/silver/chembl/activity",
                    delta_version=9,
                )
            ],
            gold_schema=self._FakeGoldSchema,
        )
        fragment_first = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.REBUILD,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
                transform_version="3.0.0",
                transform_steps=("merge", "rank"),
            )
        ).build_gold_lineage_fragment(input_data)
        fragment_second = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.REBUILD,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
                transform_version="3.0.0",
                transform_steps=("merge", "rank"),
            )
        ).build_gold_lineage_fragment(input_data)

        assert fragment_first.fragment_id == fragment_second.fragment_id

    def test_gold_fragment_exposes_composite_source_and_cv_summary(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.REBUILD,
            started_at=_FIXED_TIME,
            provider="composite",
            entity="publication",
            manifest_id="manifest-003",
        )
        coordinator = MetadataCoordinator(context)
        input_data = GoldMetadataInput(
            table_path="/data/output/gold/composite/publication",
            table_name="composite.publication",
            records=[
                {
                    "id": 1,
                    "_source_providers": "['seed', 'openalex']",
                    "_enrichment_status": "{'openalex': 'success'}",
                    "_field_sources": "{'title': 'openalex', 'doi': 'seed'}",
                    "_seed_record_id": "seed-001",
                    "_cv_warn": True,
                    "_cv_error": False,
                    "_cv_quarantine": False,
                },
                {
                    "id": 2,
                    "_field_sources": "{'abstract': 'openalex'}",
                    "_cv_warn": False,
                    "_cv_error": True,
                    "_cv_quarantine": True,
                },
            ],
            mode=GoldWriteMode.OVERWRITE,
            composite_run_id="comp-run-123",
            lineage_created_at=datetime(2026, 3, 24, 10, 0, tzinfo=UTC),
        )

        fragment = coordinator.build_gold_lineage_fragment(input_data)

        gold_dataset = next(
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.DATASET
            and node.node_id == "gold:composite.publication"
        )
        openalex_source = next(
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.SOURCE_SYSTEM
            and node.node_id == "source_system:openalex"
        )
        openalex_edge = next(
            edge
            for edge in fragment.edges
            if edge.edge_type == LineageEdgeType.DERIVED_FROM
            and edge.source.node_id == gold_dataset.node_id
            and edge.target.node_id == openalex_source.node_id
        )

        assert gold_dataset.attributes["composite_run_id"] == "comp-run-123"
        assert gold_dataset.attributes["composite_name"] == "composite.publication"
        assert gold_dataset.attributes["source_providers"] == ["seed", "openalex"]
        assert gold_dataset.attributes["seed_record_id"] == "seed-001"
        assert gold_dataset.attributes["field_sources"] == {
            "title": "openalex",
            "doi": "seed",
        }
        assert gold_dataset.attributes["provider_fields"] == {
            "openalex": ["abstract", "title"],
            "seed": ["doi"],
        }
        assert gold_dataset.attributes["cv_warn_count"] == 1
        assert gold_dataset.attributes["cv_error_count"] == 1
        assert gold_dataset.attributes["cv_quarantine_count"] == 1
        assert openalex_source.attributes["selected_fields"] == ["abstract", "title"]
        assert openalex_source.attributes["enrichment_status"] == "success"
        assert openalex_edge.attributes["selected_field_count"] == 2
        assert openalex_edge.attributes["enrichment_status"] == "success"

    def test_silver_metadata_bundle_keeps_metadata_and_fragment_aligned(
        self, coordinator: MetadataCoordinator
    ) -> None:
        input_data = SilverMetadataInput(
            table_path="/data/output/silver/chembl/activity",
            records=[{"id": 1, "_source_batch_id": "batch-001"}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            version_after=4,
            transform_steps=("normalize", "validate"),
        )

        bundle = coordinator.create_silver_metadata_bundle(input_data)

        assert isinstance(bundle, MetadataLineageBundleResult)
        assert bundle.metadata.lineage.source_batch_ids == ["batch-001"]
        assert bundle.metadata.lineage.transform_steps == ["normalize", "validate"]
        assert bundle.metadata.output.artifact_id == "silver:chembl.activity@4"
        assert (
            bundle.metadata.output.lineage_fragment_id
            == bundle.lineage_fragment.fragment_id
        )
        assert any(
            node.node_id == "silver:chembl.activity@4"
            for node in bundle.lineage_fragment.nodes
        )
        assert bundle.lineage_fragment.run_id == str(coordinator.run_context.run_id)

    def test_gold_metadata_bundle_keeps_schema_and_upstream_refs_aligned(
        self, coordinator: MetadataCoordinator
    ) -> None:
        input_data = GoldMetadataInput(
            table_path="/data/output/gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=[
                SilverRef(
                    table_name="chembl.activity",
                    table_path="/data/output/silver/chembl/activity",
                    delta_version=12,
                )
            ],
            transform_steps=("merge",),
            gold_schema=self._FakeGoldSchema,
        )

        bundle = coordinator.create_gold_metadata_bundle(input_data)

        assert isinstance(bundle, MetadataLineageBundleResult)
        assert bundle.metadata.lineage.source_tables == {"chembl.activity": 12}
        assert bundle.metadata.lineage.transform_steps == ["merge"]
        assert bundle.metadata.output.artifact_id == "gold:chembl.activity"
        assert (
            bundle.metadata.output.lineage_fragment_id
            == bundle.lineage_fragment.fragment_id
        )
        assert any(
            edge.edge_type == LineageEdgeType.USED_SCHEMA
            for edge in bundle.lineage_fragment.edges
        )

    def test_bronze_metadata_bundle_sets_lineage_fragment_anchor(
        self, coordinator: MetadataCoordinator
    ) -> None:
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=10,
            compressed_size=512,
            output_path="v1/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )

        bundle = coordinator.create_bronze_metadata_bundle(input_data)

        assert isinstance(bundle, MetadataLineageBundleResult)
        assert (
            bundle.metadata.output.artifact_id == f"bronze_batch:{input_data.batch_id}"
        )
        assert (
            bundle.metadata.output.lineage_fragment_id
            == bundle.lineage_fragment.fragment_id
        )
