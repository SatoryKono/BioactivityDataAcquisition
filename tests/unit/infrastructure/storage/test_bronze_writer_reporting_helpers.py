"""Unit tests for Bronze reporting and metadata helper builders."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.models.metadata import InputSnapshotRef
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze.reporting_helpers import (
    BronzeAuditWriteRequest,
    BronzeMetadataInputRequest,
    build_bronze_audit_entry,
    build_bronze_metadata_input,
)


@pytest.mark.unit
class TestBuildBronzeAuditEntry:
    """Tests for Bronze audit event construction."""

    def test_builds_expected_write_entry(self) -> None:
        """Audit helper should preserve Bronze write reporting fields."""
        entry = build_bronze_audit_entry(
            BronzeAuditWriteRequest(
                run_id=RunID("run-1"),
                ingestion_ts=datetime(2025, 1, 1, tzinfo=UTC),
                relative_path="chembl/activity/2025-01-01/batch.jsonl.zst",
                batch_id=BatchID("batch-1"),
                run_type=RunType.INCREMENTAL,
                record_count=10,
                compressed_size=100,
                uncompressed_size=200,
                provider="chembl",
                entity="activity",
            )
        )

        assert entry.table_name.endswith("batch.jsonl.zst")
        assert entry.records_count == 10
        assert entry.metadata["provider"] == "chembl"
        assert entry.metadata["compressed_bytes"] == 100


@pytest.mark.unit
class TestBuildBronzeMetadataInput:
    """Tests for Bronze metadata coordinator input construction."""

    def test_copies_query_string_from_source_metadata(self) -> None:
        """Metadata input should preserve query_string when source metadata exists."""
        from bioetl.domain.models.metadata import SourceMetadata

        result = build_bronze_metadata_input(
            BronzeMetadataInputRequest(
                batch_id=BatchID("batch-2"),
                record_count=3,
                compressed_size=256,
                output_path="chembl/activity/file.jsonl.zst",
                started_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
                completed_at=datetime(2025, 1, 1, 12, 1, tzinfo=UTC),
                source_metadata=SourceMetadata(type="api", query_string="foo=bar"),
            )
        )

        assert result.record_count == 3
        assert result.query_string == "foo=bar"

    def test_preserves_input_snapshots(self) -> None:
        """Metadata input should carry replay-safe input snapshot refs."""
        result = build_bronze_metadata_input(
            BronzeMetadataInputRequest(
                batch_id=BatchID("batch-3"),
                record_count=1,
                compressed_size=32,
                output_path="chembl/activity/file.jsonl.zst",
                started_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
                completed_at=datetime(2025, 1, 1, 12, 1, tzinfo=UTC),
                source_metadata=None,
                input_snapshots=(
                    InputSnapshotRef(
                        snapshot_id="snap-1",
                        content_hash="a" * 64,
                        immutable_uri="test-output/batch.jsonl.zst",
                    ),
                ),
            )
        )

        assert len(result.input_snapshots) == 1
        assert result.input_snapshots[0].snapshot_id == "snap-1"
