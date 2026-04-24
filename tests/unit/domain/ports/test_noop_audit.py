"""Unit tests for NoOpAudit."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bioetl.domain.ports.audit import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.ports.noop import NoOpAudit
from bioetl.domain.types import RunID


@pytest.fixture
def run_id() -> RunID:
    """Generate a unique run ID."""
    return RunID(uuid4())


@pytest.fixture
def sample_entry(run_id: RunID) -> AuditEntry:
    """Create a sample audit entry."""
    return AuditEntry(
        run_id=run_id,
        timestamp=datetime.now(UTC),
        layer=AuditLayer.BRONZE,
        table_name="test_table",
        operation=AuditOperation.WRITE,
        records_count=100,
    )


@pytest.mark.unit
class TestNoOpAudit:
    """Tests for NoOpAudit implementation."""

    @pytest.mark.asyncio
    async def test_log_write_does_nothing(self, sample_entry: AuditEntry) -> None:
        """Test log_write is a no-op."""
        audit = NoOpAudit()
        # Should not raise
        await audit.log_write(sample_entry)

    @pytest.mark.asyncio
    async def test_get_entries_returns_empty_list(self, run_id: RunID) -> None:
        """Test get_entries always returns empty list."""
        audit = NoOpAudit()
        entries = await audit.get_entries()
        assert entries == []

        # With filters
        entries = await audit.get_entries(
            run_id=run_id,
            layer=AuditLayer.SILVER,
            table_name="test",
        )
        assert entries == []

    @pytest.mark.asyncio
    async def test_aclose_is_idempotent(self) -> None:
        """Test aclose can be called multiple times."""
        audit = NoOpAudit()
        await audit.aclose()
        await audit.aclose()  # Should not raise

    @pytest.mark.asyncio
    async def test_no_state_after_log_write(
        self, sample_entry: AuditEntry, run_id: RunID
    ) -> None:
        """Test log_write does not store entries."""
        audit = NoOpAudit()
        await audit.log_write(sample_entry)
        await audit.log_write(sample_entry)

        # Entries should still be empty
        entries = await audit.get_entries(run_id=run_id)
        assert entries == []

    def test_log_event_is_sync_noop(self) -> None:
        """log_event uses the sync no-op shape expected by storage helpers."""
        audit = NoOpAudit()

        assert (
            audit.log_event(
                "SilverWrite",
                {"status": "ok"},
                timestamp=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
            )
            is None
        )
