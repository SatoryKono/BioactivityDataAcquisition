"""Unit tests for BronzeWriterSideEffectsMixin."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze.side_effects_mixin import (
    BronzeWriterSideEffectsMixin,
)


class _Host(BronzeWriterSideEffectsMixin):
    """Minimal host that wires the mixin for isolated testing."""

    def __init__(self, tmp_path: Path) -> None:
        self.logger = MagicMock()
        self._audit: AsyncMock | None = AsyncMock()
        self._metadata_writer = AsyncMock()
        self._metadata_coordinator = None
        self._flat_structure = False
        self.base_path = tmp_path

    def _build_full_bronze_metadata(self, **kwargs: object) -> MagicMock:  # type: ignore[override]
        return MagicMock()

    async def _calculate_checksum(self, path: Path) -> str:
        return "abc123checksum"


@pytest.mark.unit
class TestBronzeWriterSideEffectsMixin:
    """Tests for audit and metadata side effects after Bronze write."""

    @pytest.mark.asyncio
    async def test_log_bronze_audit_calls_audit_log_write(self, tmp_path: Path) -> None:
        """Should call audit.log_write when audit port is configured."""
        host = _Host(tmp_path)
        ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        await host._log_bronze_audit(
            run_id=RunID("run-1"),
            ingestion_ts=ts,
            relative_path="chembl/activity/2025-01-15/data.jsonl.zst",
            batch_id=BatchID("b-1"),
            run_type=RunType.INCREMENTAL,
            record_count=100,
            compressed_size=2048,
            uncompressed_size=4096,
            provider="chembl",
            entity="activity",
        )
        assert host._audit is not None
        host._audit.log_write.assert_awaited_once()
        entry = host._audit.log_write.call_args.args[0]
        assert isinstance(entry, AuditEntry)
        assert entry.layer == AuditLayer.BRONZE
        assert entry.operation == AuditOperation.WRITE

    @pytest.mark.asyncio
    async def test_log_bronze_audit_skips_when_audit_is_none(
        self, tmp_path: Path
    ) -> None:
        """Should silently skip audit when audit port is None."""
        host = _Host(tmp_path)
        host._audit = None
        ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        await host._log_bronze_audit(
            run_id=RunID("run-2"),
            ingestion_ts=ts,
            relative_path="chembl/activity/2025-01-15/data.jsonl.zst",
            batch_id=BatchID("b-2"),
            run_type=RunType.INCREMENTAL,
            record_count=50,
            compressed_size=1024,
            uncompressed_size=2048,
            provider="chembl",
            entity="activity",
        )
        # No exception raised, no audit call

    @pytest.mark.asyncio
    async def test_build_bronze_write_result_includes_checksum(
        self, tmp_path: Path
    ) -> None:
        """Should build BronzeWriteResult with checksum from _calculate_checksum."""
        from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

        host = _Host(tmp_path)
        prepared = MagicMock()
        prepared.full_path = tmp_path / "data.jsonl.zst"
        prepared.relative_path = "chembl/activity/2025-01-15/data.jsonl.zst"
        span = MagicMock()

        result = await host._build_bronze_write_result(
            prepared=prepared,
            batch_id=BatchID("b-res"),
            record_count=10,
            uncompressed_size=500,
            compressed_size=250,
            span=span,
        )
        assert isinstance(result, BronzeWriteResult)
        assert result.checksum_blake2 == "abc123checksum"
        assert result.record_count == 10
        span.set_attribute.assert_any_call("record_count", 10)
        span.set_attribute.assert_any_call("compressed_size", 250)
