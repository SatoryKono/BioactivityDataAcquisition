"""Integration tests for BronzeWriterSideEffectsMixin."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.lineage import MetadataLineageBundle
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.ports.metadata.coordinator import BronzeMetadataInput
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
        self._lineage_store = None
        self._flat_structure = False
        self.base_path = tmp_path

    async def _calculate_checksum(self, path: Path) -> str:
        await asyncio.sleep(0)
        return "abc123checksum"


@pytest.mark.integration
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

    @pytest.mark.asyncio
    async def test_maybe_write_bronze_metadata_persists_lineage_fragment(
        self, tmp_path: Path
    ) -> None:
        """Bundle-aware Bronze coordinator should persist lineage fragments."""

        class _Coordinator:
            def __init__(self) -> None:
                self.last_input: BronzeMetadataInput | None = None

            def create_bronze_metadata_bundle(
                self,
                input_data: BronzeMetadataInput,
            ) -> MetadataLineageBundle:
                self.last_input = input_data
                return MetadataLineageBundle(
                    metadata=metadata,
                    lineage_fragment=fragment,
                )

            def create_bronze_metadata(self, input_data: BronzeMetadataInput) -> object:
                self.last_input = input_data
                return metadata

        host = _Host(tmp_path)
        metadata = MagicMock()
        metadata.runtime.run_id = "run-1"
        metadata.output.lineage_fragment_id = None
        metadata.output.artifact_id = "bronze_batch:batch-1"
        produced_node = LineageNodeRef(
            node_type=LineageNodeType.BRONZE_BATCH,
            node_id="bronze_batch:batch-1",
            label="batch-1",
        )
        run_node = LineageNodeRef(
            node_type=LineageNodeType.RUN,
            node_id="run:run-1",
            label="run-1",
        )
        fragment = LineageGraphFragment(
            fragment_id="bronze:fragment-1",
            nodes=(produced_node, run_node),
            edges=(
                LineageEdge(
                    edge_type=LineageEdgeType.PRODUCED_BY,
                    source=produced_node,
                    target=run_node,
                    run_id="run-1",
                ),
            ),
            run_id="run-1",
        )
        coordinator = _Coordinator()
        host._metadata_coordinator = coordinator
        host._lineage_store = MagicMock()
        batch_path = tmp_path / "chembl" / "activity" / "file.jsonl.zst"
        batch_path.parent.mkdir(parents=True)
        batch_path.write_bytes(b"side-effect-bronze")

        await host._maybe_write_bronze_metadata(
            run_id=RunID("run-1"),
            run_type=RunType.INCREMENTAL,
            provider="chembl",
            entity="activity",
            batch_id=BatchID("batch-1"),
            record_count=2,
            compressed_size=128,
            relative_path="chembl/activity/file.jsonl.zst",
            ingestion_ts=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            duration=1.5,
            source_metadata=None,
        )

        host._metadata_writer.write_bronze_metadata.assert_awaited_once()
        host._lineage_store.save.assert_called_once_with(fragment)
        assert metadata.output.lineage_fragment_id == "bronze:fragment-1"
        assert coordinator.last_input is not None
        assert len(coordinator.last_input.input_snapshots) == 1
        assert coordinator.last_input.input_snapshots[0].immutable_uri == (
            "bronze://chembl/activity/file.jsonl.zst"
        )

    @pytest.mark.asyncio
    async def test_maybe_write_bronze_metadata_fails_closed_without_coordinator(
        self, tmp_path: Path
    ) -> None:
        host = _Host(tmp_path)
        batch_path = tmp_path / "chembl" / "activity" / "file.jsonl.zst"
        batch_path.parent.mkdir(parents=True)
        batch_path.write_bytes(b"side-effect-bronze")

        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinator with create_bronze_metadata_bundle is required",
        ):
            await host._maybe_write_bronze_metadata(
                run_id=RunID("run-1"),
                run_type=RunType.INCREMENTAL,
                provider="chembl",
                entity="activity",
                batch_id=BatchID("batch-1"),
                record_count=2,
                compressed_size=128,
                relative_path="chembl/activity/file.jsonl.zst",
                ingestion_ts=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
                duration=1.5,
                source_metadata=None,
            )
