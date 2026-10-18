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
"""Integration tests for BronzeWriter cleanup and sidecar metadata behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.domain.ports import MetricsPort
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from tests.testing_support.bronze_writer import (
    batch_id,
    ingestion_ts,
    noop_logger,
    noop_metrics,
    run_id,
    run_type,
    sample_records,
)

# Re-export shared fixtures for pytest discovery in this module.
_FIXTURE_IMPORTS = (
    batch_id,
    ingestion_ts,
    noop_logger,
    noop_metrics,
    run_id,
    run_type,
    sample_records,
)


class _BundleCoordinator:
    """Coordinator stub that exposes the canonical bundle API explicitly."""

    def __init__(
        self, metadata: object, lineage_fragment: object | None = None
    ) -> None:
        self.metadata = metadata
        self.lineage_fragment = lineage_fragment
        self.last_input: object | None = None

    def create_bronze_lineage_sidecar(
        self,
        *,
        provider: str,
        entity: str,
        batch_id: BatchID,
        ingestion_ts: datetime,
    ) -> dict[str, str]:
        return {
            "provider": provider,
            "entity": entity,
            "batch_id": str(batch_id),
            "ingestion_ts": ingestion_ts.isoformat(),
        }

    def create_bronze_metadata_bundle(self, input_data: object) -> object:
        self.last_input = input_data
        return SimpleNamespace(
            metadata=self.metadata,
            lineage_fragment=self.lineage_fragment,
        )


@pytest.mark.integration
class TestBronzeWriterMetadataSidecar:
    """Tests for BronzeWriter rich metadata sidecar integration."""

    @pytest.mark.asyncio
    async def test_metadata_writer_called_when_save_metadata_enabled(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        noop_metrics: MetricsPort,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that MetadataWriter is called when save_metadata=True."""
        from unittest.mock import AsyncMock

        mock_metadata_writer = AsyncMock()
        mock_metadata_writer.write_bronze_metadata = AsyncMock(
            return_value="/path/to/_metadata.yaml"
        )
        mock_bundle = MagicMock()
        mock_bundle.metadata = MagicMock()
        mock_bundle.lineage_fragment = MagicMock()
        mock_coordinator = _BundleCoordinator(
            metadata=mock_bundle.metadata,
            lineage_fragment=mock_bundle.lineage_fragment,
        )

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=noop_metrics,
            metadata_writer=mock_metadata_writer,
            save_metadata=True,
            metadata_coordinator=mock_coordinator,
        )

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=ingestion_ts,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify metadata writer was called
        mock_metadata_writer.write_bronze_metadata.assert_called_once()
        call_args = mock_metadata_writer.write_bronze_metadata.call_args

        # Verify correct arguments were passed
        assert "base_path" in call_args.kwargs
        assert "metadata" in call_args.kwargs

        # Verify metadata structure
        metadata = call_args.kwargs["metadata"]
        assert metadata is mock_bundle.metadata

    @pytest.mark.asyncio
    async def test_metadata_writer_not_called_when_save_metadata_disabled(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        noop_metrics: MetricsPort,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that MetadataWriter is NOT called when save_metadata=False."""
        from unittest.mock import AsyncMock

        mock_metadata_writer = AsyncMock()
        mock_metadata_writer.write_bronze_metadata = AsyncMock()

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=noop_metrics,
            metadata_writer=mock_metadata_writer,
            save_metadata=False,  # Disabled
        )

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=ingestion_ts,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        # Verify metadata writer was NOT called
        mock_metadata_writer.write_bronze_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_write_bronze_fails_closed_when_save_metadata_enabled_without_coordinator(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        noop_metrics: MetricsPort,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Canonical Bronze metadata publication must require a coordinator."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=noop_metrics,
            save_metadata=True,
        )

        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinator with create_bronze_metadata_bundle is required",
        ):
            await writer.write_bronze(
                records=iter(sample_records),
                provider="chembl",
                entity="activity",
                date=ingestion_ts,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
            )

    @pytest.mark.asyncio
    async def test_build_full_bronze_metadata_structure(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        noop_metrics: MetricsPort,
        batch_id: BatchID,
        run_id: RunID,
        ingestion_ts: datetime,
    ) -> None:
        """Legacy Bronze sidecar builder should be blocked outside coordinator flow."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=noop_metrics,
        )

        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinator with create_bronze_metadata_bundle is required",
        ):
            writer._build_full_bronze_metadata(
                run_id=run_id,
                run_type=RunType.INCREMENTAL,
                provider="chembl",
                entity="activity",
                batch_id=batch_id,
                record_count=100,
                compressed_size=5000,
                output_path="v1/chembl/activity/2024-01-15/batch_abc.jsonl.zst",
                started_at=ingestion_ts,
                completed_at=ingestion_ts,
                duration_seconds=1.5,
            )

    @pytest.mark.asyncio
    async def test_metadata_run_type_mapping(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        noop_metrics: MetricsPort,
        batch_id: BatchID,
        run_id: RunID,
        ingestion_ts: datetime,
    ) -> None:
        """Legacy Bronze sidecar builder should be blocked for every run type."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=noop_metrics,
        )

        run_type_mappings = [
            (RunType.INCREMENTAL, "incremental"),
            (RunType.BACKFILL, "backfill"),
            (RunType.REBUILD, "rebuild"),
        ]

        for run_type_value, expected_value in run_type_mappings:
            del expected_value
            with pytest.raises(
                RuntimeError,
                match="MetadataCoordinator with create_bronze_metadata_bundle is required",
            ):
                writer._build_full_bronze_metadata(
                    run_id=run_id,
                    run_type=run_type_value,
                    provider="chembl",
                    entity="activity",
                    batch_id=batch_id,
                    record_count=10,
                    compressed_size=100,
                    output_path="test.jsonl.zst",
                    started_at=ingestion_ts,
                    completed_at=ingestion_ts,
                    duration_seconds=0.1,
                )


@pytest.mark.integration
class TestBronzeWriterQueryString:
    """Tests for BronzeWriter query_string extraction for metadata."""

    @pytest.mark.asyncio
    async def test_query_string_extracted_from_source_metadata(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        noop_metrics: MetricsPort,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test that query_string is extracted from source_metadata for BronzeMetadataInput."""
        from unittest.mock import AsyncMock, MagicMock

        from bioetl.domain.models.metadata import SourceMetadata
        from bioetl.domain.ports import BronzeMetadataInput

        # Create mock metadata coordinator
        mock_bundle = MagicMock()
        mock_bundle.metadata = MagicMock()
        mock_bundle.lineage_fragment = MagicMock()
        mock_coordinator = _BundleCoordinator(
            metadata=mock_bundle.metadata,
            lineage_fragment=mock_bundle.lineage_fragment,
        )

        # Create mock metadata writer
        mock_metadata_writer = AsyncMock()
        mock_metadata_writer.write_bronze_metadata = AsyncMock(
            return_value="/path/to/_metadata.yaml"
        )

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=noop_metrics,
            metadata_writer=mock_metadata_writer,
            save_metadata=True,
            metadata_coordinator=mock_coordinator,
        )

        # Create source_metadata with query_string
        source_metadata = SourceMetadata(
            type="api",
            url="https://www.ebi.ac.uk/chembl/api/data/activity",
            query_string="assay_type=B&standard_type=IC50",
        )

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=ingestion_ts,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            source_metadata=source_metadata,
        )

        # Verify create_bronze_metadata_bundle was called with BronzeMetadataInput
        bronze_input = mock_coordinator.last_input
        assert isinstance(bronze_input, BronzeMetadataInput)

        # Verify query_string was extracted from source_metadata
        assert bronze_input.query_string == "assay_type=B&standard_type=IC50"
        # Also verify source_metadata was passed
        assert bronze_input.source_metadata is source_metadata

    @pytest.mark.asyncio
    async def test_query_string_none_when_source_metadata_has_no_query(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        noop_metrics: MetricsPort,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test query_string is None when source_metadata doesn't have query_string."""
        from unittest.mock import AsyncMock, MagicMock

        from bioetl.domain.models.metadata import SourceMetadata

        mock_bundle = MagicMock()
        mock_bundle.metadata = MagicMock()
        mock_bundle.lineage_fragment = MagicMock()
        mock_coordinator = _BundleCoordinator(
            metadata=mock_bundle.metadata,
            lineage_fragment=mock_bundle.lineage_fragment,
        )

        mock_metadata_writer = AsyncMock()
        mock_metadata_writer.write_bronze_metadata = AsyncMock()

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=noop_metrics,
            metadata_writer=mock_metadata_writer,
            save_metadata=True,
            metadata_coordinator=mock_coordinator,
        )

        # Create source_metadata WITHOUT query_string
        source_metadata = SourceMetadata(
            type="api",
            url="https://www.ebi.ac.uk/chembl/api/data/activity",
            # No query_string - defaults to None
        )

        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=ingestion_ts,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            source_metadata=source_metadata,
        )

        # Verify create_bronze_metadata_bundle was called
        bronze_input = mock_coordinator.last_input

        # query_string should be None
        assert bronze_input.query_string is None

    @pytest.mark.asyncio
    async def test_query_string_none_when_no_source_metadata(
        self,
        tmp_path: Path,
        noop_logger: NoOpLogger,
        noop_metrics: MetricsPort,
        sample_records: list[bytes],
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> None:
        """Test query_string is None when source_metadata is not provided."""
        from unittest.mock import AsyncMock, MagicMock

        mock_bundle = MagicMock()
        mock_bundle.metadata = MagicMock()
        mock_bundle.lineage_fragment = MagicMock()
        mock_coordinator = _BundleCoordinator(
            metadata=mock_bundle.metadata,
            lineage_fragment=mock_bundle.lineage_fragment,
        )

        mock_metadata_writer = AsyncMock()
        mock_metadata_writer.write_bronze_metadata = AsyncMock()

        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=noop_metrics,
            metadata_writer=mock_metadata_writer,
            save_metadata=True,
            metadata_coordinator=mock_coordinator,
        )

        # No source_metadata provided
        await writer.write_bronze(
            records=iter(sample_records),
            provider="chembl",
            entity="activity",
            date=ingestion_ts,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            # source_metadata not passed - defaults to None
        )

        bronze_input = mock_coordinator.last_input

        # Both should be None
        assert bronze_input.source_metadata is None
        assert bronze_input.query_string is None


@pytest.mark.integration
class TestBronzeWriteResult:
    """Tests for BronzeWriteResult value object (REQ-LINEAGE-001)."""

    def test_bronze_write_result_creation(self, batch_id: BatchID) -> None:
        """Test valid BronzeWriteResult creation."""
        result = BronzeWriteResult(
            batch_id=batch_id,
            relative_path="v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            absolute_path="/data/bronze/v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            record_count=100,
            compressed_size=5000,
            uncompressed_size=20000,
            checksum_blake2="abc123def456",
        )

        assert result.batch_id == batch_id
        assert result.record_count == 100
        assert result.compressed_size == 5000
        assert result.uncompressed_size == 20000

    def test_bronze_write_result_is_frozen(self, batch_id: BatchID) -> None:
        """Test BronzeWriteResult is immutable (frozen dataclass)."""
        result = BronzeWriteResult(
            batch_id=batch_id,
            relative_path="v1/test/path.jsonl.zst",
            absolute_path="/data/bronze/v1/test/path.jsonl.zst",
            record_count=10,
            compressed_size=100,
            uncompressed_size=500,
            checksum_blake2="abc123",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            result.record_count = 50  # type: ignore[misc]

    def test_bronze_write_result_compression_ratio(self, batch_id: BatchID) -> None:
        """Test compression_ratio property calculation."""
        result = BronzeWriteResult(
            batch_id=batch_id,
            relative_path="v1/test/path.jsonl.zst",
            absolute_path="/data/bronze/v1/test/path.jsonl.zst",
            record_count=10,
            compressed_size=1000,
            uncompressed_size=4000,
            checksum_blake2="abc123",
        )

        assert result.compression_ratio == pytest.approx(4.0)  # 4000 / 1000

    def test_bronze_write_result_compression_ratio_zero_uncompressed(
        self, batch_id: BatchID
    ) -> None:
        """Test compression_ratio returns 1.0 for zero uncompressed_size."""
        result = BronzeWriteResult(
            batch_id=batch_id,
            relative_path="v1/test/path.jsonl.zst",
            absolute_path="/data/bronze/v1/test/path.jsonl.zst",
            record_count=0,
            compressed_size=100,
            uncompressed_size=0,
            checksum_blake2="abc123",
        )

        assert result.compression_ratio == pytest.approx(1.0)

    def test_bronze_write_result_validation_negative_record_count(
        self, batch_id: BatchID
    ) -> None:
        """Test BronzeWriteResult rejects negative record_count."""
        with pytest.raises(ValueError, match="record_count must be non-negative"):
            BronzeWriteResult(
                batch_id=batch_id,
                relative_path="v1/test/path.jsonl.zst",
                absolute_path="/data/bronze/v1/test/path.jsonl.zst",
                record_count=-1,
                compressed_size=100,
                uncompressed_size=500,
                checksum_blake2="abc123",
            )

    def test_bronze_write_result_validation_negative_compressed_size(
        self, batch_id: BatchID
    ) -> None:
        """Test BronzeWriteResult rejects negative compressed_size."""
        with pytest.raises(ValueError, match="compressed_size must be non-negative"):
            BronzeWriteResult(
                batch_id=batch_id,
                relative_path="v1/test/path.jsonl.zst",
                absolute_path="/data/bronze/v1/test/path.jsonl.zst",
                record_count=10,
                compressed_size=-100,
                uncompressed_size=500,
                checksum_blake2="abc123",
            )

    def test_bronze_write_result_validation_empty_path(self, batch_id: BatchID) -> None:
        """Test BronzeWriteResult rejects empty paths."""
        with pytest.raises(ValueError, match="relative_path cannot be empty"):
            BronzeWriteResult(
                batch_id=batch_id,
                relative_path="",
                absolute_path="/data/bronze/v1/test/path.jsonl.zst",
                record_count=10,
                compressed_size=100,
                uncompressed_size=500,
                checksum_blake2="abc123",
            )

    def test_bronze_write_result_validation_empty_checksum(
        self, batch_id: BatchID
    ) -> None:
        """Test BronzeWriteResult rejects empty checksum."""
        with pytest.raises(ValueError, match="checksum_blake2 cannot be empty"):
            BronzeWriteResult(
                batch_id=batch_id,
                relative_path="v1/test/path.jsonl.zst",
                absolute_path="/data/bronze/v1/test/path.jsonl.zst",
                record_count=10,
                compressed_size=100,
                uncompressed_size=500,
                checksum_blake2="",
            )


@pytest.mark.integration
class TestBronzeWriterCleanupFiltered:
    """Tests for BronzeWriter filtered cleanup operations."""

    def test_find_old_date_dirs_filtered_by_provider(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test _find_old_date_dirs filters by provider."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        # Setup
        (tmp_path / "p1" / "e1" / "2024-01-01").mkdir(parents=True)
        (tmp_path / "p2" / "e1" / "2024-01-01").mkdir(parents=True)

        cutoff = "2024-06-01"
        result = writer._find_old_date_dirs(cutoff, provider="p1")

        assert len(result) == 1
        assert "p1" in str(result[0])

    def test_find_old_date_dirs_filtered_by_entity(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test _find_old_date_dirs filters by entity (requires provider)."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        # Setup
        (tmp_path / "p1" / "e1" / "2024-01-01").mkdir(parents=True)
        (tmp_path / "p1" / "e2" / "2024-01-01").mkdir(parents=True)

        cutoff = "2024-06-01"
        result = writer._find_old_date_dirs(cutoff, provider="p1", entity="e1")

        assert len(result) == 1
        assert "e1" in str(result[0])

    @pytest.mark.asyncio
    async def test_cleanup_old_files_filtered(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test cleanup_old_files respects provider/entity filters."""
        writer = BronzeWriter(
            base_path=tmp_path,
            logger=noop_logger,
            metrics=NoOpMetrics(),
        )

        # Setup
        p1_e1 = tmp_path / "p1" / "e1" / "2024-01-01"
        p1_e1.mkdir(parents=True)
        (p1_e1 / "file").touch()

        p2_e1 = tmp_path / "p2" / "e1" / "2024-01-01"
        p2_e1.mkdir(parents=True)
        (p2_e1 / "file").touch()

        cutoff = datetime(2024, 6, 1, tzinfo=UTC)

        # Cleanup only p1
        result = await writer.cleanup_old_files(cutoff, provider="p1")

        assert result["files_removed"] == 1
        assert not p1_e1.exists()
        assert p2_e1.exists()
