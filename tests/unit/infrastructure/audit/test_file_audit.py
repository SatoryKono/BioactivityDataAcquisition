"""Unit tests for FileAuditAdapter."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.domain.ports.audit import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import RunID
from bioetl.infrastructure.audit.file_audit import FileAuditAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.fixture
def noop_logger() -> NoOpLogger:
    """Provide a NoOpLogger for tests."""
    return NoOpLogger()


@pytest.fixture
def run_id() -> RunID:
    """Generate a unique run ID."""
    return RunID(uuid4())


@pytest.fixture
def sample_entry(run_id: RunID) -> AuditEntry:
    """Create a sample audit entry."""
    return AuditEntry(
        run_id=run_id,
        timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        layer=AuditLayer.BRONZE,
        table_name="bronze/v1/chembl/activity/2024-01-15/batch_1234.jsonl.zst",
        operation=AuditOperation.WRITE,
        records_count=100,
        metadata={
            "provider": "chembl",
            "entity": "activity",
            "batch_id": "1234",
        },
    )


@pytest.mark.unit
class TestAuditEntry:
    """Tests for AuditEntry dataclass."""

    def test_audit_entry_creation(self, run_id: RunID) -> None:
        """Test AuditEntry can be created with required fields."""
        entry = AuditEntry(
            run_id=run_id,
            timestamp=datetime.now(UTC),
            layer=AuditLayer.SILVER,
            table_name="chembl.activity",
            operation=AuditOperation.MERGE,
            records_count=50,
        )
        assert entry.run_id == run_id
        assert entry.layer == AuditLayer.SILVER
        assert entry.records_count == 50
        assert entry.metadata == {}

    def test_audit_entry_to_dict(self, sample_entry: AuditEntry) -> None:
        """Test AuditEntry serialization to dict."""
        result = sample_entry.to_dict()
        assert result["layer"] == "bronze"
        assert result["operation"] == "write"
        assert result["records_count"] == 100
        assert result["metadata"]["provider"] == "chembl"
        assert "timestamp" in result
        assert "run_id" in result

    def test_audit_entry_is_frozen(self, sample_entry: AuditEntry) -> None:
        """Test AuditEntry is immutable."""
        with pytest.raises(AttributeError):
            sample_entry.records_count = 200  # type: ignore[misc]


@pytest.mark.unit
class TestFileAuditAdapter:
    """Tests for FileAuditAdapter."""

    @pytest.mark.asyncio
    async def test_log_write_creates_file(
        self, tmp_path: Path, noop_logger: NoOpLogger, sample_entry: AuditEntry
    ) -> None:
        """Test log_write creates audit file."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        await adapter.log_write(sample_entry)

        # Check file was created
        date_str = sample_entry.timestamp.strftime("%Y-%m-%d")
        audit_file = tmp_path / "audit" / f"audit_{date_str}.jsonl"
        assert audit_file.exists()

        # Check content
        content = audit_file.read_text()
        data = json.loads(content.strip())
        assert data["layer"] == "bronze"
        assert data["records_count"] == 100

    @pytest.mark.asyncio
    async def test_log_write_appends_entries(
        self, tmp_path: Path, noop_logger: NoOpLogger, run_id: RunID
    ) -> None:
        """Test log_write appends multiple entries."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        timestamp = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        # Write two entries
        entry1 = AuditEntry(
            run_id=run_id,
            timestamp=timestamp,
            layer=AuditLayer.BRONZE,
            table_name="table1",
            operation=AuditOperation.WRITE,
            records_count=10,
        )
        entry2 = AuditEntry(
            run_id=run_id,
            timestamp=timestamp,
            layer=AuditLayer.SILVER,
            table_name="table2",
            operation=AuditOperation.MERGE,
            records_count=20,
        )

        await adapter.log_write(entry1)
        await adapter.log_write(entry2)

        # Check both entries are in the file
        date_str = timestamp.strftime("%Y-%m-%d")
        audit_file = tmp_path / "audit" / f"audit_{date_str}.jsonl"
        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_get_entries_returns_all(
        self, tmp_path: Path, noop_logger: NoOpLogger, run_id: RunID
    ) -> None:
        """Test get_entries returns all entries."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        timestamp = datetime.now(UTC)

        # Write entries
        for i in range(5):
            entry = AuditEntry(
                run_id=run_id,
                timestamp=timestamp,
                layer=AuditLayer.BRONZE,
                table_name=f"table_{i}",
                operation=AuditOperation.WRITE,
                records_count=i * 10,
            )
            await adapter.log_write(entry)

        # Query entries
        entries = await adapter.get_entries()
        assert len(entries) == 5

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_run_id(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test get_entries filters by run_id."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        timestamp = datetime.now(UTC)

        run_id_1 = RunID(uuid4())
        run_id_2 = RunID(uuid4())

        # Write entries with different run_ids
        await adapter.log_write(
            AuditEntry(
                run_id=run_id_1,
                timestamp=timestamp,
                layer=AuditLayer.BRONZE,
                table_name="table_1",
                operation=AuditOperation.WRITE,
                records_count=10,
            )
        )
        await adapter.log_write(
            AuditEntry(
                run_id=run_id_2,
                timestamp=timestamp,
                layer=AuditLayer.BRONZE,
                table_name="table_2",
                operation=AuditOperation.WRITE,
                records_count=20,
            )
        )

        # Filter by run_id
        entries = await adapter.get_entries(run_id=run_id_1)
        assert len(entries) == 1
        assert entries[0].run_id == run_id_1

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_layer(
        self, tmp_path: Path, noop_logger: NoOpLogger, run_id: RunID
    ) -> None:
        """Test get_entries filters by layer."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        timestamp = datetime.now(UTC)

        # Write entries with different layers
        for layer in [AuditLayer.BRONZE, AuditLayer.SILVER, AuditLayer.GOLD]:
            await adapter.log_write(
                AuditEntry(
                    run_id=run_id,
                    timestamp=timestamp,
                    layer=layer,
                    table_name=f"table_{layer.value}",
                    operation=AuditOperation.WRITE,
                    records_count=10,
                )
            )

        # Filter by Silver layer
        entries = await adapter.get_entries(layer=AuditLayer.SILVER)
        assert len(entries) == 1
        assert entries[0].layer == AuditLayer.SILVER

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_table_name(
        self, tmp_path: Path, noop_logger: NoOpLogger, run_id: RunID
    ) -> None:
        """Test get_entries filters by table_name."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        timestamp = datetime.now(UTC)

        # Write entries with different table names
        for table in ["chembl.activity", "pubchem.compound", "uniprot.protein"]:
            await adapter.log_write(
                AuditEntry(
                    run_id=run_id,
                    timestamp=timestamp,
                    layer=AuditLayer.SILVER,
                    table_name=table,
                    operation=AuditOperation.MERGE,
                    records_count=10,
                )
            )

        # Filter by table name
        entries = await adapter.get_entries(table_name="pubchem.compound")
        assert len(entries) == 1
        assert entries[0].table_name == "pubchem.compound"

    @pytest.mark.asyncio
    async def test_get_entries_filter_by_time_range(
        self, tmp_path: Path, noop_logger: NoOpLogger, run_id: RunID
    ) -> None:
        """Test get_entries filters by time range."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        base_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        # Write entries at different times
        for i in range(3):
            await adapter.log_write(
                AuditEntry(
                    run_id=run_id,
                    timestamp=base_time + timedelta(hours=i),
                    layer=AuditLayer.BRONZE,
                    table_name=f"table_{i}",
                    operation=AuditOperation.WRITE,
                    records_count=10,
                )
            )

        # Filter by time range
        entries = await adapter.get_entries(
            start_time=base_time + timedelta(hours=1),
            end_time=base_time + timedelta(hours=2),
        )
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_get_entries_respects_limit(
        self, tmp_path: Path, noop_logger: NoOpLogger, run_id: RunID
    ) -> None:
        """Test get_entries respects limit parameter."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        timestamp = datetime.now(UTC)

        # Write 10 entries
        for i in range(10):
            await adapter.log_write(
                AuditEntry(
                    run_id=run_id,
                    timestamp=timestamp,
                    layer=AuditLayer.BRONZE,
                    table_name=f"table_{i}",
                    operation=AuditOperation.WRITE,
                    records_count=10,
                )
            )

        # Query with limit
        entries = await adapter.get_entries(limit=5)
        assert len(entries) == 5

    @pytest.mark.asyncio
    async def test_get_entries_empty_directory(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test get_entries returns empty list for non-existent directory."""
        adapter = FileAuditAdapter(tmp_path / "nonexistent", noop_logger)
        entries = await adapter.get_entries()
        assert entries == []

    @pytest.mark.asyncio
    async def test_aclose_prevents_further_writes(
        self, tmp_path: Path, noop_logger: NoOpLogger, sample_entry: AuditEntry
    ) -> None:
        """Test aclose prevents further operations."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        await adapter.aclose()

        with pytest.raises(RuntimeError, match="has been closed"):
            await adapter.log_write(sample_entry)

    @pytest.mark.asyncio
    async def test_aclose_is_idempotent(
        self, tmp_path: Path, noop_logger: NoOpLogger
    ) -> None:
        """Test aclose can be called multiple times."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        await adapter.aclose()
        await adapter.aclose()  # Should not raise


@pytest.mark.unit
class TestFileAuditAdapterEdgeCases:
    """Edge case tests for FileAuditAdapter."""

    @pytest.mark.asyncio
    async def test_handles_special_characters_in_metadata(
        self, tmp_path: Path, noop_logger: NoOpLogger, run_id: RunID
    ) -> None:
        """Test adapter handles special characters in metadata."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)
        entry = AuditEntry(
            run_id=run_id,
            timestamp=datetime.now(UTC),
            layer=AuditLayer.BRONZE,
            table_name="test_table",
            operation=AuditOperation.WRITE,
            records_count=1,
            metadata={
                "message": 'Quote "test" and newline\n',
                "unicode": "Привет мир",
            },
        )

        await adapter.log_write(entry)
        entries = await adapter.get_entries()

        assert len(entries) == 1
        assert entries[0].metadata["unicode"] == "Привет мир"

    @pytest.mark.asyncio
    async def test_handles_multiple_days(
        self, tmp_path: Path, noop_logger: NoOpLogger, run_id: RunID
    ) -> None:
        """Test adapter creates separate files for different days."""
        adapter = FileAuditAdapter(tmp_path / "audit", noop_logger)

        # Write entries for different days
        for day in [1, 2, 3]:
            await adapter.log_write(
                AuditEntry(
                    run_id=run_id,
                    timestamp=datetime(2024, 1, day, 12, 0, 0, tzinfo=UTC),
                    layer=AuditLayer.BRONZE,
                    table_name=f"table_day_{day}",
                    operation=AuditOperation.WRITE,
                    records_count=10,
                )
            )

        # Check separate files were created
        audit_dir = tmp_path / "audit"
        files = list(audit_dir.glob("audit_*.jsonl"))
        assert len(files) == 3

        # Query all entries
        entries = await adapter.get_entries()
        assert len(entries) == 3
