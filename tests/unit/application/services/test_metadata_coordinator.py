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

pytestmark = pytest.mark.unit

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












