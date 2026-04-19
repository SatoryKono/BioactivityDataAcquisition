"""SilverWriter lineage/audit/export unit tests."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.application.services.lineage import MetadataLineageBundle
from bioetl.domain.medallion import SilverWriteMode
from tests.unit.infrastructure.storage._lineage_fragment_helpers import (
    make_produced_artifact_fragment,
)

pytestmark = pytest.mark.unit

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-silver-writer-lineage-"))
SILVER_BASE_PATH = TEST_ROOT / "silver"


def _silver_table_path(table_name: str) -> str:
    return str(SILVER_BASE_PATH / table_name.replace(".", "/"))


def _make_bundle_safe_metadata(run_id: str = "test-run") -> MagicMock:
    """Create metadata mocks compatible with MetadataLineageBundle identity checks."""
    metadata = MagicMock()
    metadata.runtime = SimpleNamespace(run_id=run_id, manifest_id=None)
    metadata.output = SimpleNamespace(lineage_fragment_id=None, artifact_id=None)
    return metadata


class TestSilverWriterAudit:
    """Tests for SilverWriter audit logging."""

    @pytest.mark.asyncio
    async def test_log_silver_audit_skips_when_no_audit(self, noop_logger):
        """Test _log_silver_audit does nothing when audit is None."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.domain.types import BatchID, RunID, RunType
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

        # Should not raise, just return early
        await writer._log_silver_audit(
            table_name="test.table",
            records=[{"entity_id": "CHEMBL1"}],
            mode=SilverWriteMode.MERGE,
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            source_batch_id=BatchID(uuid4()),
            ingestion_ts=datetime(2025, 1, 1, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_log_silver_audit_missing_run_id_raises(self, noop_logger):
        """Test _log_silver_audit fails closed when run_id is missing."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.domain.types import BatchID, RunType
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH), logger=noop_logger, audit=mock_audit
        )

        with pytest.raises(ValueError, match="run_id is required"):
            await writer._log_silver_audit(
                table_name="test.table",
                records=[{"entity_id": "CHEMBL1"}],
                mode=SilverWriteMode.MERGE,
                run_id=None,
                run_type=RunType.INCREMENTAL,
                source_batch_id=BatchID(uuid4()),
                ingestion_ts=datetime(2025, 1, 1, tzinfo=UTC),
            )

        mock_audit.log_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_silver_audit_with_valid_data(self, noop_logger):
        """Test _log_silver_audit logs correctly with valid data."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.domain.types import BatchID, RunID, RunType
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        mock_audit.log_write = AsyncMock()

        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH), logger=noop_logger, audit=mock_audit
        )

        valid_uuid = uuid4()
        await writer._log_silver_audit(
            table_name="test.table",
            records=[{"entity_id": "CHEMBL1"}],
            mode=SilverWriteMode.MERGE,
            run_id=RunID(valid_uuid),
            run_type=RunType.INCREMENTAL,
            source_batch_id=BatchID(uuid4()),
            ingestion_ts=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        mock_audit.log_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_silver_audit_with_datetime_ingestion_ts(self, noop_logger):
        """Test _log_silver_audit handles datetime ingestion_ts."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.domain.types import BatchID, RunID, RunType
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        mock_audit.log_write = AsyncMock()

        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH), logger=noop_logger, audit=mock_audit
        )

        valid_uuid = uuid4()
        ingestion_dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        await writer._log_silver_audit(
            table_name="test.table",
            records=[{"entity_id": "CHEMBL1"}],
            mode=SilverWriteMode.APPEND,
            run_id=RunID(valid_uuid),
            run_type=RunType.BACKFILL,
            source_batch_id=BatchID(uuid4()),
            ingestion_ts=ingestion_dt,
        )

        mock_audit.log_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_silver_audit_missing_ingestion_ts_raises(self, noop_logger):
        """Test _log_silver_audit fails closed when ingestion_ts is missing."""
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.domain.types import BatchID, RunID, RunType
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        mock_audit.log_write = AsyncMock()

        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH), logger=noop_logger, audit=mock_audit
        )

        valid_uuid = uuid4()
        with pytest.raises(ValueError, match="ingestion_ts is required"):
            await writer._log_silver_audit(
                table_name="test.table",
                records=[{"entity_id": "CHEMBL1"}],
                mode=SilverWriteMode.DELETE,
                run_id=RunID(valid_uuid),
                run_type=RunType.REBUILD,
                source_batch_id=BatchID(uuid4()),
                ingestion_ts=None,
            )

        mock_audit.log_write.assert_not_called()


@pytest.mark.unit
class TestSilverWriterCsvExport:
    """Tests for SilverWriter CSV export integration."""

    @pytest.mark.asyncio
    async def test_write_silver_with_csv_exporter(self, noop_logger, valid_records):
        """Test write_silver calls CSV exporter when configured."""

        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_exporter = MagicMock()
        mock_exporter.export = AsyncMock()

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(
                base_path=str(SILVER_BASE_PATH),
                logger=noop_logger,
                csv_exporter=mock_exporter,
            )

            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="append",
            )

            mock_exporter.export.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_silver_csv_exporter_with_merge_passes_primary_keys(
        self, noop_logger, valid_records, tmp_path
    ):
        """Test CSV exporter receives primary_keys when mode is merge."""
        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_exporter = MagicMock()
        export_calls = []

        async def capture_export(*args, **kwargs):
            await asyncio.sleep(0)
            export_calls.append(kwargs)

        mock_exporter.export = capture_export

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(
                base_path=str(tmp_path / "silver"),
                logger=noop_logger,
                csv_exporter=mock_exporter,
            )

            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
            )

            assert len(export_calls) == 1
            assert export_calls[0]["primary_keys"] == ["entity_id"]


@pytest.mark.unit
class TestSilverWriterLineage:
    """Tests for SilverWriter lineage tracking (REQ-LINEAGE-001)."""

    @pytest.mark.asyncio
    async def test_write_silver_without_bronze_refs(
        self, noop_logger, valid_records, tmp_path
    ):
        """Test write_silver works without bronze_refs (backward compatibility)."""
        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(
                base_path=str(tmp_path / "silver"), logger=noop_logger
            )

            # Should not raise when bronze_refs not provided
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
            )

    @pytest.mark.asyncio
    async def test_write_silver_with_bronze_refs(
        self, noop_logger, valid_records, tmp_path
    ):
        """Test write_silver accepts bronze_refs parameter."""
        from uuid import uuid4

        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.types import BatchID
        from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        bronze_result = BronzeWriteResult(
            batch_id=BatchID(uuid4()),
            relative_path="v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            absolute_path="/data/bronze/v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            record_count=100,
            compressed_size=5000,
            uncompressed_size=20000,
            checksum_blake2="abc123def456",
        )

        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(
                base_path=str(tmp_path / "silver"), logger=noop_logger
            )

            # Should not raise with bronze_refs
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
                bronze_refs=[bronze_result],
            )

    @pytest.mark.asyncio
    async def test_write_silver_metadata_includes_bronze_paths(
        self, noop_logger, valid_records, mock_metadata_coordinator
    ):
        """Test _write_silver_metadata populates bronze_paths from bronze_refs."""
        from uuid import uuid4

        from bioetl.domain.types import BatchID
        from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        bronze_result_1 = BronzeWriteResult(
            batch_id=BatchID(uuid4()),
            relative_path="v1/chembl/activity/2024-01-15/batch_001.jsonl.zst",
            absolute_path="/data/bronze/v1/chembl/activity/2024-01-15/batch_001.jsonl.zst",
            record_count=50,
            compressed_size=2500,
            uncompressed_size=10000,
            checksum_blake2="abc123",
        )

        bronze_result_2 = BronzeWriteResult(
            batch_id=BatchID(uuid4()),
            relative_path="v1/chembl/activity/2024-01-15/batch_002.jsonl.zst",
            absolute_path="/data/bronze/v1/chembl/activity/2024-01-15/batch_002.jsonl.zst",
            record_count=50,
            compressed_size=2500,
            uncompressed_size=10000,
            checksum_blake2="def456",
        )

        mock_metadata_writer = MagicMock()
        write_calls = []

        async def capture_write(
            table_path,
            metadata,
            *,
            table_name=None,
            flat_structure=False,
            provider=None,
            entity=None,
        ):
            await asyncio.sleep(0)
            write_calls.append({"table_path": table_path, "metadata": metadata})

        mock_metadata_writer.write_silver_metadata = capture_write

        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metadata_writer=mock_metadata_writer,
            metadata_coordinator=mock_metadata_coordinator,
        )

        await writer._write_silver_metadata(
            table_path=_silver_table_path("test.table"),
            table_name="test_table",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=[bronze_result_1, bronze_result_2],
        )

        # Verify metadata writer was called with bronze_paths
        assert len(write_calls) == 1
        metadata = write_calls[0]["metadata"]
        lineage = metadata.lineage
        assert len(lineage.bronze_paths) == 2
        assert (
            "v1/chembl/activity/2024-01-15/batch_001.jsonl.zst" in lineage.bronze_paths
        )
        assert (
            "v1/chembl/activity/2024-01-15/batch_002.jsonl.zst" in lineage.bronze_paths
        )

    @pytest.mark.asyncio
    async def test_write_silver_metadata_empty_bronze_paths_when_no_refs(
        self, noop_logger, valid_records, mock_metadata_coordinator
    ):
        """Test _write_silver_metadata has empty bronze_paths when bronze_refs=None."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        mock_metadata_writer = MagicMock()
        write_calls = []

        async def capture_write(
            table_path,
            metadata,
            *,
            table_name=None,
            flat_structure=False,
            provider=None,
            entity=None,
        ):
            await asyncio.sleep(0)
            write_calls.append({"table_path": table_path, "metadata": metadata})

        mock_metadata_writer.write_silver_metadata = capture_write

        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metadata_writer=mock_metadata_writer,
            metadata_coordinator=mock_metadata_coordinator,
        )

        await writer._write_silver_metadata(
            table_path=_silver_table_path("test.table"),
            table_name="test_table",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=None,  # No bronze refs
        )

        # Verify metadata writer was called with empty bronze_paths
        assert len(write_calls) == 1
        metadata = write_calls[0]["metadata"]
        lineage = metadata.lineage
        assert lineage.bronze_paths == []

    @pytest.mark.asyncio
    async def test_write_silver_metadata_resolves_provider_entity_and_version(
        self, noop_logger, valid_records, mock_metadata_coordinator
    ):
        """Standard Silver metadata path should preserve version and resolved target."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        metadata = _make_bundle_safe_metadata()
        captured_input = None

        def create_silver_metadata_bundle(input_data: object) -> MetadataLineageBundle:
            nonlocal captured_input
            captured_input = input_data
            return MetadataLineageBundle(
                metadata=metadata,
                lineage_fragment=make_produced_artifact_fragment(
                    fragment_id="silver:standard-fragment",
                    layer="silver",
                    logical_name="chembl.activity",
                ),
            )

        mock_metadata_coordinator.create_silver_metadata_bundle = (
            create_silver_metadata_bundle
        )
        mock_metadata_writer = MagicMock()
        mock_metadata_writer.write_silver_metadata = AsyncMock()

        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metadata_writer=mock_metadata_writer,
            metadata_coordinator=mock_metadata_coordinator,
        )

        await writer._write_silver_metadata(
            table_path=_silver_table_path("chembl.activity"),
            table_name="chembl.activity",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            version_after=7,
        )

        if captured_input is None:
            pytest.fail("metadata coordinator did not capture SilverMetadataInput")
        silver_input = captured_input
        assert silver_input.version_after == 7
        mock_metadata_writer.write_silver_metadata.assert_awaited_once_with(
            _silver_table_path("chembl.activity"),
            metadata,
            table_name="chembl.activity",
            flat_structure=False,
            provider="chembl",
            entity="activity",
        )

    @pytest.mark.asyncio
    async def test_write_silver_metadata_uses_canonical_file_handoff(
        self, noop_logger, valid_records, mock_metadata_coordinator
    ):
        """Standard and merged metadata flows should converge on one file handoff."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        metadata = _make_bundle_safe_metadata()

        def create_silver_metadata_bundle(input_data: object) -> MetadataLineageBundle:
            _ = input_data
            return MetadataLineageBundle(
                metadata=metadata,
                lineage_fragment=make_produced_artifact_fragment(
                    fragment_id="silver:canonical-handoff-fragment",
                    layer="silver",
                    logical_name="chembl.activity",
                ),
            )

        mock_metadata_coordinator.create_silver_metadata_bundle = (
            create_silver_metadata_bundle
        )
        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metadata_writer=MagicMock(),
            metadata_coordinator=mock_metadata_coordinator,
        )
        writer._write_silver_metadata_file = AsyncMock()  # type: ignore[method-assign]

        await writer._write_silver_metadata(
            table_path=_silver_table_path("chembl.activity"),
            table_name="chembl.activity",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            version_after=7,
        )

        writer._write_silver_metadata_file.assert_awaited_once_with(
            table_path=_silver_table_path("chembl.activity"),
            metadata=metadata,
            table_name="chembl.activity",
            provider_name="chembl",
            entity_name="activity",
        )

    @pytest.mark.asyncio
    async def test_write_silver_metadata_persists_lineage_fragment(
        self, noop_logger, valid_records
    ):
        """Concrete bundle-aware coordinators should materialize lineage fragments."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        metadata = _make_bundle_safe_metadata()
        fragment = make_produced_artifact_fragment(
            fragment_id="silver:fragment-1",
            layer="silver",
            logical_name="chembl.activity",
        )

        class _Coordinator:
            def create_silver_metadata_bundle(
                self,
                input_data: object,
            ) -> MetadataLineageBundle:
                _ = input_data
                return MetadataLineageBundle(
                    metadata=metadata,
                    lineage_fragment=fragment,
                )

            def create_silver_metadata(self, input_data: object) -> object:
                _ = input_data
                return metadata

        lineage_store = MagicMock()
        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metadata_writer=MagicMock(),
            metadata_coordinator=_Coordinator(),
            lineage_store=lineage_store,
        )
        writer._write_silver_metadata_file = AsyncMock()  # type: ignore[method-assign]

        await writer._write_silver_metadata(
            table_path=_silver_table_path("chembl.activity"),
            table_name="chembl.activity",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            version_after=7,
        )

        lineage_store.save.assert_called_once_with(fragment)

    @pytest.mark.asyncio
    async def test_write_silver_merged_metadata_resolves_provider_entity(
        self, noop_logger, valid_records
    ):
        """Merged Silver metadata path should reuse resolved provider/entity."""
        from bioetl.application.services.lineage import (
            MetadataLineageBundle,
        )
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        metadata = _make_bundle_safe_metadata()
        mock_metadata_writer = MagicMock()
        mock_metadata_writer.write_silver_metadata = AsyncMock()

        class _Coordinator:
            last_input: object | None = None

            def create_silver_metadata_bundle(
                self,
                input_data: object,
            ) -> MetadataLineageBundle:
                self.last_input = input_data
                return MetadataLineageBundle(
                    metadata=metadata,
                    lineage_fragment=make_produced_artifact_fragment(
                        fragment_id="silver:merged-input-fragment",
                        layer="silver",
                        logical_name="composite.publication",
                    ),
                )

        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metadata_writer=mock_metadata_writer,
            metadata_coordinator=_Coordinator(),
        )
        writer._get_delta_version = AsyncMock(return_value=11)  # type: ignore[method-assign]
        await writer._write_silver_merged_metadata(
            table_path=_silver_table_path("composite.publication"),
            table_name="composite.publication",
            records=valid_records,
            primary_keys=["entity_id"],
            run_id="run-1",
            completed_at="2025-01-15T12:00:00Z",
        )

        input_arg = writer._metadata_coordinator.last_input
        assert input_arg.table_path == _silver_table_path("composite.publication")
        assert input_arg.mode == SilverWriteMode.DELETE
        assert input_arg.version_after == 11
        mock_metadata_writer.write_silver_metadata.assert_awaited_once_with(
            _silver_table_path("composite.publication"),
            metadata,
            table_name="composite.publication",
            flat_structure=False,
            provider="composite",
            entity="publication",
        )

    @pytest.mark.asyncio
    async def test_write_silver_merged_metadata_uses_canonical_file_handoff(
        self, noop_logger, valid_records
    ):
        """Merged metadata flow should converge on the same canonical file handoff."""
        from bioetl.application.services.lineage import (
            MetadataLineageBundle,
        )
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        metadata = _make_bundle_safe_metadata(run_id="run-1")

        class _Coordinator:
            def create_silver_metadata_bundle(
                self,
                input_data: object,
            ) -> MetadataLineageBundle:
                _ = input_data
                return MetadataLineageBundle(
                    metadata=metadata,
                    lineage_fragment=make_produced_artifact_fragment(
                        fragment_id="silver:merged-handoff-fragment",
                        layer="silver",
                        logical_name="composite.publication",
                    ),
                )

        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metadata_writer=MagicMock(),
            metadata_coordinator=_Coordinator(),
        )
        writer._get_delta_version = AsyncMock(return_value=11)  # type: ignore[method-assign]
        writer._write_silver_metadata_file = AsyncMock()  # type: ignore[method-assign]

        await writer._write_silver_merged_metadata(
            table_path=_silver_table_path("composite.publication"),
            table_name="composite.publication",
            records=valid_records,
            primary_keys=["entity_id"],
            run_id="run-1",
            completed_at="2025-01-15T12:00:00Z",
        )

        writer._write_silver_metadata_file.assert_awaited_once_with(
            table_path=_silver_table_path("composite.publication"),
            metadata=metadata,
            table_name="composite.publication",
            provider_name="composite",
            entity_name="publication",
        )

    @pytest.mark.asyncio
    async def test_write_silver_merged_metadata_persists_lineage_fragment(
        self, noop_logger, valid_records
    ):
        """Merged Silver metadata should persist canonical lineage fragments too."""
        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.domain.ports import SilverMetadataInput
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        metadata = _make_bundle_safe_metadata(run_id="run-1")
        fragment = make_produced_artifact_fragment(
            fragment_id="silver:merged-fragment-1",
            layer="silver",
            logical_name="composite.publication",
        )
        captured_input: SilverMetadataInput | None = None

        class _Coordinator:
            def create_silver_metadata_bundle(
                self,
                input_data: SilverMetadataInput,
            ) -> MetadataLineageBundle:
                nonlocal captured_input
                captured_input = input_data
                return MetadataLineageBundle(
                    metadata=metadata,
                    lineage_fragment=fragment,
                )

            def create_silver_metadata(self, input_data: object) -> object:
                _ = input_data
                return metadata

        lineage_store = MagicMock()
        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metadata_writer=MagicMock(),
            metadata_coordinator=_Coordinator(),
            lineage_store=lineage_store,
        )
        writer._get_delta_version = AsyncMock(return_value=11)  # type: ignore[method-assign]
        writer._write_silver_metadata_file = AsyncMock()  # type: ignore[method-assign]

        await writer._write_silver_merged_metadata(
            table_path=_silver_table_path("composite.publication"),
            table_name="composite.publication",
            records=valid_records,
            primary_keys=["entity_id"],
            run_id="run-1",
            completed_at="2025-01-15T12:00:00Z",
        )

        if captured_input is None:
            pytest.fail(
                "merged metadata coordinator did not capture SilverMetadataInput"
            )
        assert captured_input.mode is SilverWriteMode.DELETE
        assert captured_input.version_after == 11
        assert captured_input.records == valid_records
        writer._write_silver_metadata_file.assert_awaited_once_with(
            table_path=_silver_table_path("composite.publication"),
            metadata=metadata,
            table_name="composite.publication",
            provider_name="composite",
            entity_name="publication",
        )
        lineage_store.save.assert_called_once_with(fragment)

    @pytest.mark.asyncio
    async def test_metadata_write_paths_fail_closed_without_metadata_coordinator(
        self, valid_records
    ):
        """Standard and merged metadata writes must fail closed without coordinator."""
        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        logger = MagicMock()
        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=logger,
            metadata_coordinator=None,
        )

        with pytest.raises(
            RuntimeError,
            match="create_silver_metadata_bundle is required for Silver metadata publication",
        ):
            writer._metadata_writer = MagicMock()
            await writer._write_silver_metadata(
                table_path=_silver_table_path("chembl.activity"),
                table_name="chembl.activity",
                records=valid_records,
                primary_keys=["entity_id"],
                mode=SilverWriteMode.MERGE,
            )
        with pytest.raises(
            RuntimeError,
            match="create_silver_metadata_bundle is required for Silver metadata publication",
        ):
            writer._metadata_writer = MagicMock()
            await writer._write_silver_merged_metadata(
                table_path=_silver_table_path("composite.publication"),
                table_name="composite.publication",
                records=valid_records,
                primary_keys=["entity_id"],
            )
