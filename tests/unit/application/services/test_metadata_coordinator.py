"""Unit tests for MetadataCoordinator service.

Tests centralized metadata creation for Bronze, Silver, and Gold layers.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from bioetl.composition.services.metadata_coordinator import (
    BronzeMetadataInput,
    GoldMetadataInput,
    MetadataCoordinator,
    SilverMetadataInput,
)
from bioetl.domain.ports.metadata_coordinator import SilverRef
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import (
    BronzeMetadata,
    GoldMetadata,
    LayerType,
    RunTypeEnum,
    SilverMetadata,
    SourceMetadata,
)
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext


@pytest.fixture
def run_context() -> RunContext:
    """Create a test RunContext."""
    return RunContext.create(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
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
        run_id = RunID(uuid4())
        started_at = datetime.now(UTC)

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
                run_id=RunID(uuid4()),
                run_type=RunType.INCREMENTAL,
                started_at=datetime.now(),  # Naive datetime
                provider="chembl",
                entity="activity",
            )

    def test_create_with_empty_provider_raises(self) -> None:
        """Test that empty provider raises ValueError."""
        with pytest.raises(ValueError, match="provider cannot be empty"):
            RunContext.create(
                run_id=RunID(uuid4()),
                run_type=RunType.INCREMENTAL,
                started_at=datetime.now(UTC),
                provider="",
                entity="activity",
            )

    def test_create_with_empty_entity_raises(self) -> None:
        """Test that empty entity raises ValueError."""
        with pytest.raises(ValueError, match="entity cannot be empty"):
            RunContext.create(
                run_id=RunID(uuid4()),
                run_type=RunType.INCREMENTAL,
                started_at=datetime.now(UTC),
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


class TestBronzeMetadata:
    """Tests for Bronze metadata creation."""

    def test_create_bronze_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test creating Bronze metadata."""
        started_at = datetime.now(UTC)
        completed_at = started_at + timedelta(seconds=5.5)

        input_data = BronzeMetadataInput(
            batch_id=BatchID(uuid4()),
            record_count=1000,
            compressed_size=50000,
            output_path="v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            started_at=started_at,
            completed_at=completed_at,
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert isinstance(metadata, BronzeMetadata)
        assert metadata.layer == LayerType.BRONZE
        assert metadata.version == "1.0"

    def test_bronze_runtime_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Bronze runtime metadata contains correct values."""
        started_at = datetime.now(UTC)
        completed_at = started_at + timedelta(seconds=3.0)

        input_data = BronzeMetadataInput(
            batch_id=BatchID(uuid4()),
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
        assert metadata.runtime.duration_seconds == 3.0

    def test_bronze_pipeline_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Bronze pipeline metadata uses context values."""
        input_data = BronzeMetadataInput(
            batch_id=BatchID(uuid4()),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert metadata.pipeline.name == "chembl_activity"
        assert metadata.pipeline.provider == "chembl"
        assert metadata.pipeline.entity == "activity"

    def test_bronze_output_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test Bronze output metadata contains file info."""
        input_data = BronzeMetadataInput(
            batch_id=BatchID(uuid4()),
            record_count=500,
            compressed_size=25000,
            output_path="v1/chembl/activity/2024-01-15/batch_abc.jsonl.zst",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        assert metadata.output.total_records == 500
        assert metadata.output.total_bytes == 25000
        assert len(metadata.output.files) == 1
        assert metadata.output.files[0].path == input_data.output_path
        assert metadata.output.files[0].record_count == 500

    def test_bronze_metadata_includes_query_string_from_input(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Bronze metadata should include query_string from BronzeMetadataInput."""
        input_data = BronzeMetadataInput(
            batch_id=BatchID(uuid4()),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
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
            batch_id=BatchID(uuid4()),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
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
            batch_id=BatchID(uuid4()),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            source_metadata=source,
            query_string="injected_query=value",
        )

        metadata = coordinator.create_bronze_metadata(input_data)

        # query_string should be injected from input_data
        assert metadata.source.query_string == "injected_query=value"
        # Other source_metadata fields should be preserved
        assert metadata.source.url == "https://www.ebi.ac.uk/chembl/api/data/activity"

    def test_bronze_metadata_query_string_defaults_to_none(
        self, coordinator: MetadataCoordinator
    ) -> None:
        """Bronze metadata query_string should default to None when not provided."""
        input_data = BronzeMetadataInput(
            batch_id=BatchID(uuid4()),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2024-01-15/batch.jsonl.zst",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
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

    def test_create_silver_metadata(self, coordinator: MetadataCoordinator) -> None:
        """Test creating Silver metadata."""
        records = [
            {
                "_run_id": str(coordinator.run_context.run_id),
                "_run_type": "incremental",
                "_source_batch_id": str(uuid4()),
                "_ingestion_ts": datetime.now(UTC).isoformat(),
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
        assert metadata.layer == LayerType.SILVER
        assert metadata.version == "1.0"

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
        batch_id_1 = str(uuid4())
        batch_id_2 = str(uuid4())
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
        assert metadata.layer == LayerType.GOLD
        assert metadata.version == "1.0"

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
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            started_at=datetime.now(UTC),
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
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            started_at=datetime.now(UTC),
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
        run_id = RunID(uuid4())
        started_at = datetime.now(UTC)

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
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            started_at=datetime.now(UTC),
            provider="chembl",
            entity="activity",
        )

        assert context.transform_version is None
        assert context.transform_steps == ()

    def test_silver_input_takes_precedence_over_run_context(self) -> None:
        """Test that SilverMetadataInput values take precedence over RunContext."""
        MetadataCoordinator.reset_environment_cache()

        context = RunContext.create(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            started_at=datetime.now(UTC),
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
            run_id=RunID(uuid4()),
            run_type=run_type,
            started_at=datetime.now(UTC),
            provider="test",
            entity="entity",
        )
        coordinator = MetadataCoordinator(context)

        input_data = BronzeMetadataInput(
            batch_id=BatchID(uuid4()),
            record_count=1,
            compressed_size=100,
            output_path="path",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
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
            batch_id=BatchID(uuid4()),
            record_count=10,
            compressed_size=1000,
            output_path="path",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
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
            batch_id=BatchID(uuid4()),
            record_count=10,
            compressed_size=1000,
            output_path="path",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
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
            batch_id=BatchID(uuid4()),
            record_count=10,
            compressed_size=1000,
            output_path="path",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
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
