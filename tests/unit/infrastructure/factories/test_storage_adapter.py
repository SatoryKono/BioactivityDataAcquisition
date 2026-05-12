"""Unit tests for StorageBundle."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.composition.factories.storage.bundle import StorageBundle
from bioetl.domain.ports import (
    BronzeStoragePort,
    GoldStoragePort,
    SilverStoragePort,
    StorageLifecyclePort,
    StorageMaintenancePort,
)
from bioetl.domain.types import RunType

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-storage-adapter-"))
BRONZE_ROOT = str(TEST_ROOT / "bronze")
SILVER_ROOT = str(TEST_ROOT / "silver")
GOLD_ROOT = str(TEST_ROOT / "gold")
SILVER_TABLE_PATH = TEST_ROOT / "silver" / "table"
GOLD_TABLE_PATH = TEST_ROOT / "gold" / "table"


@pytest.fixture
def mock_bronze_writer() -> MagicMock:
    """Create mock bronze writer."""
    writer = MagicMock()
    writer.write_bronze = AsyncMock()
    writer.cleanup_old_files = AsyncMock()
    writer.base_path = BRONZE_ROOT
    return writer


@pytest.fixture
def mock_silver_writer() -> MagicMock:
    """Create mock silver writer."""
    writer = MagicMock()
    writer.write_silver = AsyncMock()
    writer.write_silver_merged = AsyncMock()
    writer.read_silver = AsyncMock(return_value=[{"id": 1}])
    writer.vacuum = AsyncMock()
    writer.clear = MagicMock(return_value=1)
    writer.get_table_path = MagicMock(return_value=SILVER_TABLE_PATH)
    writer.base_path = SILVER_ROOT
    writer.csv_exporter = None
    return writer


@pytest.fixture
def mock_gold_writer() -> MagicMock:
    """Create mock gold writer."""
    writer = MagicMock()
    writer.write_gold = AsyncMock()
    writer.write_gold_merged = AsyncMock()
    writer.clear = MagicMock(return_value=1)
    writer.get_table_path = MagicMock(return_value=GOLD_TABLE_PATH)
    writer.base_path = GOLD_ROOT
    writer.csv_exporter = None
    return writer


@pytest.fixture
def storage_adapter(
    mock_bronze_writer: MagicMock,
    mock_silver_writer: MagicMock,
    mock_gold_writer: MagicMock,
) -> StorageBundle:
    """Create StorageBundle with mocked writers."""
    return StorageBundle(
        bronze_writer=mock_bronze_writer,
        silver_writer=mock_silver_writer,
        gold_writer=mock_gold_writer,
    )


@pytest.mark.unit
class TestStorageBundleInit:
    """Tests for StorageBundle initialization."""

    def test_init(
        self,
        mock_bronze_writer: MagicMock,
        mock_silver_writer: MagicMock,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Test adapter initialization."""
        adapter = StorageBundle(
            bronze_writer=mock_bronze_writer,
            silver_writer=mock_silver_writer,
            gold_writer=mock_gold_writer,
        )

        assert adapter.bronze is mock_bronze_writer
        assert adapter.silver is mock_silver_writer
        assert adapter.gold is mock_gold_writer

    @pytest.mark.parametrize(
        "protocol",
        [
            BronzeStoragePort,
            SilverStoragePort,
            GoldStoragePort,
            StorageMaintenancePort,
            StorageLifecyclePort,
        ],
        ids=lambda protocol: protocol.__name__,
    )
    def test_implements_narrow_storage_ports(
        self,
        storage_adapter: StorageBundle,
        protocol: type[object],
    ) -> None:
        """StorageBundle implements the narrow storage protocols."""
        assert isinstance(storage_adapter, protocol)

    def test_requires_silver_schema_marker(
        self, storage_adapter: StorageBundle
    ) -> None:
        """Test that REQUIRES_SILVER_SCHEMA is set."""
        assert storage_adapter.REQUIRES_SILVER_SCHEMA is True


@pytest.mark.unit
class TestStorageBundleWriteBronze:
    """Tests for write_bronze method."""

    @pytest.mark.asyncio
    async def test_write_bronze_delegates(
        self,
        storage_adapter: StorageBundle,
        mock_bronze_writer: MagicMock,
    ) -> None:
        """Test that write_bronze delegates to bronze writer."""
        records = iter([b'{"id": 1}\n', b'{"id": 2}\n'])
        date = datetime(2024, 1, 15)
        batch_id = uuid4()
        run_id = uuid4()
        run_type = RunType.INCREMENTAL
        # Fixed timestamp for deterministic tests (ADR-014)
        ingestion_ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        await storage_adapter.write_bronze(
            records=records,
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        mock_bronze_writer.write_bronze.assert_called_once()
        call_kwargs = mock_bronze_writer.write_bronze.call_args[1]
        assert call_kwargs["provider"] == "chembl"
        assert call_kwargs["entity"] == "activity"
        assert call_kwargs["date"] == date
        assert call_kwargs["batch_id"] == batch_id
        assert call_kwargs["run_id"] == run_id
        assert call_kwargs["run_type"] == run_type
        assert call_kwargs["ingestion_ts"] == ingestion_ts


@pytest.mark.unit
class TestStorageBundleWriteSilver:
    """Tests for write_silver method."""

    @pytest.mark.asyncio
    async def test_write_silver_delegates(
        self,
        storage_adapter: StorageBundle,
        mock_silver_writer: MagicMock,
    ) -> None:
        """Test that write_silver delegates to silver writer."""
        records = [{"id": 1, "name": "test"}]
        schema = MagicMock()

        await storage_adapter.write_silver(
            table_name="test_table",
            records=records,
            primary_keys=["id"],
            schema=schema,
            mode="merge",
        )

        mock_silver_writer.write_silver.assert_called_once()
        call_kwargs = mock_silver_writer.write_silver.call_args[1]
        assert call_kwargs["table_name"] == "test_table"
        assert call_kwargs["records"] == records
        assert call_kwargs["primary_keys"] == ["id"]
        assert call_kwargs["schema"] is schema

    @pytest.mark.asyncio
    async def test_write_silver_default_mode(
        self,
        storage_adapter: StorageBundle,
        mock_silver_writer: MagicMock,
    ) -> None:
        """Test write_silver uses default merge mode."""
        await storage_adapter.write_silver(
            table_name="test",
            records=[],
            primary_keys=["id"],
            schema=MagicMock(),
        )

        mock_silver_writer.write_silver.assert_called_once()


@pytest.mark.unit
class TestStorageBundleWriteGold:
    """Tests for write_gold method."""

    @pytest.mark.asyncio
    async def test_write_gold_delegates(
        self,
        storage_adapter: StorageBundle,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Test that write_gold delegates to gold writer."""
        records = [{"id": 1, "aggregated_value": 100}]
        mock_schema = MagicMock()

        await storage_adapter.write_gold(
            table_name="gold_table",
            records=records,
            schema=mock_schema,
            mode="overwrite",
        )

        mock_gold_writer.write_gold.assert_called_once()
        call_kwargs = mock_gold_writer.write_gold.call_args[1]
        assert call_kwargs["table_name"] == "gold_table"
        assert call_kwargs["records"] == records
        assert call_kwargs["schema"] == mock_schema
        assert call_kwargs["mode"] == "overwrite"

    @pytest.mark.asyncio
    async def test_write_gold_append_mode(
        self,
        storage_adapter: StorageBundle,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Test write_gold with append mode."""
        mock_schema = MagicMock()
        await storage_adapter.write_gold(
            table_name="gold_table",
            records=[{"id": 1}],
            schema=mock_schema,
            mode="append",
        )

        call_kwargs = mock_gold_writer.write_gold.call_args[1]
        assert call_kwargs["mode"] == "append"

    @pytest.mark.asyncio
    async def test_write_gold_default_mode(
        self,
        storage_adapter: StorageBundle,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Test write_gold uses default overwrite mode."""
        mock_schema = MagicMock()
        await storage_adapter.write_gold(
            table_name="test",
            records=[],
            schema=mock_schema,
        )

        call_kwargs = mock_gold_writer.write_gold.call_args[1]
        assert call_kwargs["mode"] == "overwrite"

    @pytest.mark.asyncio
    async def test_write_gold_passes_scd_config(
        self,
        storage_adapter: StorageBundle,
        mock_gold_writer: MagicMock,
    ) -> None:
        """SCD config is forwarded unchanged to the gold writer."""
        mock_schema = MagicMock()
        scd_config = {"business_key": "entity_id", "valid_from_col": "valid_from"}

        await storage_adapter.write_gold(
            table_name="gold_table",
            records=[{"entity_id": "1"}],
            schema=mock_schema,
            mode="scd2",
            scd_config=scd_config,
        )

        call_kwargs = mock_gold_writer.write_gold.call_args[1]
        assert call_kwargs["mode"] == "scd2"
        assert call_kwargs["scd_config"] == scd_config


@pytest.mark.unit
class TestStorageBundleClose:
    """Tests for aclose method."""

    @pytest.mark.asyncio
    async def test_aclose(self, storage_adapter: StorageBundle) -> None:
        """Test aclose completes without error."""
        # Should not raise
        await storage_adapter.aclose()

    @pytest.mark.asyncio
    async def test_aclose_is_noop(self, storage_adapter: StorageBundle) -> None:
        """Test aclose is a no-op (writers don't need cleanup)."""
        # Can be called multiple times
        await storage_adapter.aclose()
        await storage_adapter.aclose()


@pytest.mark.unit
class TestStorageBundleOptimize:
    """Tests for optimize method."""

    @pytest.mark.asyncio
    async def test_optimize_delegates_to_vacuum(
        self,
        storage_adapter: StorageBundle,
        mock_silver_writer: MagicMock,
    ) -> None:
        """Test that optimize calls vacuum."""
        # Mock vacuum method on adapter since it calls self.vacuum
        storage_adapter.vacuum = AsyncMock()  # type: ignore

        await storage_adapter.optimize(
            table_name="chembl.activity", retention_hours=168, dry_run=True
        )

        storage_adapter.vacuum.assert_called_once_with("chembl.activity", 168, True)

    @pytest.mark.asyncio
    async def test_optimize_calls_bronze_cleanup(
        self,
        storage_adapter: StorageBundle,
        mock_bronze_writer: MagicMock,
    ) -> None:
        """Test that optimize calls bronze cleanup for valid table names."""
        storage_adapter.vacuum = AsyncMock()  # type: ignore

        await storage_adapter.optimize(
            table_name="chembl.activity", retention_hours=168, dry_run=False
        )

        mock_bronze_writer.cleanup_old_files.assert_called_once()
        call_kwargs = mock_bronze_writer.cleanup_old_files.call_args[1]
        assert call_kwargs["provider"] == "chembl"
        assert call_kwargs["entity"] == "activity"
        assert "cutoff_date" in call_kwargs
        assert call_kwargs["dry_run"] is False

    @pytest.mark.asyncio
    async def test_optimize_skips_bronze_cleanup_for_no_dot(
        self,
        storage_adapter: StorageBundle,
        mock_bronze_writer: MagicMock,
    ) -> None:
        """Test that optimize skips bronze cleanup if table name has no dot."""
        storage_adapter.vacuum = AsyncMock()  # type: ignore

        await storage_adapter.optimize(
            table_name="invalid_table_name",
            retention_hours=168,
        )

        mock_bronze_writer.cleanup_old_files.assert_not_called()


@pytest.mark.unit
class TestStorageBundleWriteGoldMerged:
    """Tests for composite Gold schema binding in write_gold_merged."""

    @pytest.mark.asyncio
    async def test_write_gold_merged_binds_composite_publication_schema(
        self,
        storage_adapter: StorageBundle,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Composite publication table should pass bound schema to GoldWriter."""
        await storage_adapter.write_gold_merged(
            table_name="composite/publication",
            records=[{"entity_id": "pub:1", "content_hash": "h1"}],
        )

        call_kwargs = mock_gold_writer.write_gold_merged.call_args[1]
        assert call_kwargs["schema"].__name__ == "CompositePublicationGoldSchema"

    @pytest.mark.asyncio
    async def test_write_gold_merged_unknown_table_uses_no_schema(
        self,
        storage_adapter: StorageBundle,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Unknown merged Gold tables fail before the writer is called."""
        with pytest.raises(ValueError, match="registered strict schema"):
            await storage_adapter.write_gold_merged(
                table_name="custom/merged",
                records=[{"entity_id": "x", "content_hash": "y"}],
            )

        mock_gold_writer.write_gold_merged.assert_not_called()


@pytest.mark.unit
class TestStorageBundleAdditionalPaths:
    """Additional tests to cover maintenance and utility branches."""

    def test_get_table_path_defaults_to_silver_layer(
        self, storage_adapter: StorageBundle, mock_silver_writer: MagicMock
    ) -> None:
        """get_table_path should resolve via Silver writer by default."""
        result = storage_adapter.get_table_path("chembl.activity")

        assert result == SILVER_TABLE_PATH
        mock_silver_writer.get_table_path.assert_called_once_with("chembl.activity")

    def test_get_table_path_gold_layer_uses_gold_writer(
        self, storage_adapter: StorageBundle, mock_gold_writer: MagicMock
    ) -> None:
        """get_table_path(layer='gold') should resolve via Gold writer."""
        result = storage_adapter.get_table_path("chembl.activity", layer="gold")

        assert result == GOLD_TABLE_PATH
        mock_gold_writer.get_table_path.assert_called_once_with("chembl.activity")

    @pytest.mark.asyncio
    async def test_read_silver_delegates(
        self, storage_adapter: StorageBundle, mock_silver_writer: MagicMock
    ) -> None:
        """read_silver should delegate to Silver writer."""
        mock_silver_writer.read_silver.return_value = [{"id": 42}]

        rows = await storage_adapter.read_silver("chembl.activity", columns=["id"])

        assert rows == [{"id": 42}]
        mock_silver_writer.read_silver.assert_called_once_with(
            "chembl.activity", columns=["id"]
        )

    @pytest.mark.asyncio
    async def test_write_silver_merged_delegates(
        self, storage_adapter: StorageBundle, mock_silver_writer: MagicMock
    ) -> None:
        """write_silver_merged should pass through optional parameters."""
        await storage_adapter.write_silver_merged(
            table_name="composite/publication",
            records=[{"id": 1}],
            primary_keys=["id"],
            run_id="run-1",
            sources_used=["chembl_publication"],
            preserve_column_order=True,
        )

        mock_silver_writer.write_silver_merged.assert_called_once_with(
            "composite/publication",
            [{"id": 1}],
            ["id"],
            schema=storage_adapter._COMPOSITE_GOLD_SCHEMAS["composite/publication"],
            run_id="run-1",
            sources_used=["chembl_publication"],
            preserve_column_order=True,
        )

    @pytest.mark.asyncio
    async def test_clear_csv_counts_list_and_int_results(
        self,
        storage_adapter: StorageBundle,
        mock_silver_writer: MagicMock,
        mock_gold_writer: MagicMock,
    ) -> None:
        """clear_csv should handle both list and int exporter return types."""
        silver_exporter = MagicMock()
        silver_exporter.clear = MagicMock(return_value=["a.csv", "b.csv"])
        gold_exporter = MagicMock()
        gold_exporter.clear = MagicMock(return_value=3)
        mock_silver_writer.csv_exporter = silver_exporter
        mock_gold_writer.csv_exporter = gold_exporter

        deleted = await storage_adapter.clear_csv("chembl.activity")

        assert deleted == 5
        silver_exporter.clear.assert_called_once_with("chembl.activity")
        gold_exporter.clear.assert_called_once_with("chembl.activity")

    @pytest.mark.asyncio
    async def test_clear_delta_with_table_name(
        self,
        storage_adapter: StorageBundle,
        mock_silver_writer: MagicMock,
        mock_gold_writer: MagicMock,
    ) -> None:
        """clear_delta should clear both layers when table_name is provided."""
        mock_silver_writer.clear.return_value = 2
        mock_gold_writer.clear.return_value = 4

        deleted = await storage_adapter.clear_delta("chembl.activity")

        assert deleted == 6
        mock_silver_writer.clear.assert_called_once_with("chembl.activity")
        mock_gold_writer.clear.assert_called_once_with("chembl.activity")

    @pytest.mark.asyncio
    async def test_clear_delta_without_table_name_noop(
        self,
        storage_adapter: StorageBundle,
        mock_silver_writer: MagicMock,
        mock_gold_writer: MagicMock,
    ) -> None:
        """clear_delta should return 0 when no specific table is given."""
        deleted = await storage_adapter.clear_delta(None)
        assert deleted == 0
        mock_silver_writer.clear.assert_not_called()
        mock_gold_writer.clear.assert_not_called()

    def test_preview_layer_counts_files(
        self, storage_adapter: StorageBundle, tmp_path: Path
    ) -> None:
        """_preview_layer should count files only when table path exists."""
        table_dir = tmp_path / "silver" / "chembl" / "activity"
        table_dir.mkdir(parents=True)
        (table_dir / "part-0001.parquet").write_text("x", encoding="utf-8")
        (table_dir / "_delta_log").mkdir()
        (table_dir / "_delta_log" / "00000000000000000001.json").write_text(
            "{}", encoding="utf-8"
        )

        writer = MagicMock()
        writer.get_table_path.return_value = table_dir

        preview = storage_adapter._preview_layer(writer, "chembl.activity")

        assert preview["exists"] is True
        assert preview["file_count"] == 2
        assert preview["path"] == str(table_dir)

    @pytest.mark.asyncio
    async def test_health_check_status_transitions(
        self, storage_adapter: StorageBundle, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """health_check should map writable-layer count to HealthStatus."""
        monkeypatch.setattr(
            storage_adapter, "_check_directory_writable", lambda _: True
        )
        assert await storage_adapter.health_check() == "HEALTHY"

        states = iter([True, False, True])
        monkeypatch.setattr(
            storage_adapter, "_check_directory_writable", lambda _: next(states)
        )
        assert await storage_adapter.health_check() == "DEGRADED"

        monkeypatch.setattr(
            storage_adapter, "_check_directory_writable", lambda _: False
        )
        assert await storage_adapter.health_check() == "UNHEALTHY"

    @pytest.mark.asyncio
    async def test_vacuum_returns_zero_when_tables_absent(
        self, storage_adapter: StorageBundle, tmp_path: Path
    ) -> None:
        """vacuum should do nothing if Silver and Gold table paths do not exist."""
        storage_adapter.silver.get_table_path = MagicMock(
            return_value=tmp_path / "missing_silver"
        )
        storage_adapter.gold.get_table_path = MagicMock(
            return_value=tmp_path / "missing_gold"
        )

        removed = await storage_adapter.vacuum("chembl.activity", retention_hours=24)

        assert removed == 0

    @pytest.mark.asyncio
    async def test_vacuum_skips_metadata_only_gold_directory(
        self, storage_adapter: StorageBundle, tmp_path: Path
    ) -> None:
        """vacuum should ignore Gold directories that are not real Delta tables."""
        silver_table = tmp_path / "silver_table"
        (silver_table / "_delta_log").mkdir(parents=True)
        (silver_table / "_delta_log" / "00000000000000000000.json").write_text(
            "{}",
            encoding="utf-8",
        )
        gold_table = tmp_path / "gold_table"
        gold_table.mkdir()
        (gold_table / "chembl_activity_metadata.yaml").write_text(
            "metadata: true\n",
            encoding="utf-8",
        )

        storage_adapter.silver.get_table_path = MagicMock(return_value=silver_table)
        storage_adapter.gold.get_table_path = MagicMock(return_value=gold_table)
        storage_adapter.silver.vacuum = AsyncMock(return_value=["silver-file.parquet"])

        removed = await storage_adapter.vacuum("chembl.activity", retention_hours=24)

        assert removed == 1
        storage_adapter.silver.vacuum.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_archive_copies_silver_and_gold_and_optional_remove_source(
        self, storage_adapter: StorageBundle, tmp_path: Path
    ) -> None:
        """archive should copy both layers and optionally remove source directories."""
        silver_src = tmp_path / "silver_src"
        gold_src = tmp_path / "gold_src"
        silver_src.mkdir()
        gold_src.mkdir()
        (silver_src / "part-0001.parquet").write_text("s", encoding="utf-8")
        (gold_src / "part-0001.parquet").write_text("g", encoding="utf-8")

        storage_adapter.silver.get_table_path = MagicMock(return_value=silver_src)
        storage_adapter.gold.get_table_path = MagicMock(return_value=gold_src)

        target_root = tmp_path / "archive"
        copied = await storage_adapter.archive(
            "chembl.activity", str(target_root), remove_source=True
        )

        assert copied == 2
        assert (target_root / "silver" / "chembl" / "activity").exists()
        assert (target_root / "gold" / "chembl" / "activity").exists()
        assert not silver_src.exists()
        assert not gold_src.exists()

    @pytest.mark.asyncio
    async def test_cleanup_bronze_delegates(
        self, storage_adapter: StorageBundle, mock_bronze_writer: MagicMock
    ) -> None:
        """cleanup_bronze should delegate to Bronze writer."""
        expected = {"files_deleted": 3, "bytes_freed": 100}
        mock_bronze_writer.cleanup_old_files.return_value = expected
        cutoff = datetime(2026, 1, 1, tzinfo=UTC)

        result = await storage_adapter.cleanup_bronze(cutoff_date=cutoff, dry_run=True)

        assert result == expected
        mock_bronze_writer.cleanup_old_files.assert_called_once_with(
            cutoff_date=cutoff, dry_run=True
        )

    def test_check_directory_writable_false_on_oserror(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_check_directory_writable should return False on filesystem exceptions."""

        def _raise_oserror(*args: object, **kwargs: object) -> None:
            raise OSError("denied")

        monkeypatch.setattr(Path, "mkdir", _raise_oserror)
        assert StorageBundle._check_directory_writable(tmp_path / "x") is False
