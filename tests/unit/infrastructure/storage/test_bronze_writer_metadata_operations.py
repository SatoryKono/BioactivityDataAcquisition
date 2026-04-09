"""Unit tests for Bronze metadata preparation helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze.metadata_operations import (
    BronzeMetadataWriteRequest,
    prepare_bronze_metadata_write,
)


class _Host:
    def __init__(self, tmp_path: Path) -> None:
        self.base_path = tmp_path
        self._flat_structure = False
        self._metadata_coordinator = None
        self._build_full_bronze_metadata = MagicMock(return_value=MagicMock())


@pytest.mark.unit
class TestPrepareBronzeMetadataWrite:
    def test_uses_fallback_builder_when_coordinator_missing(
        self, tmp_path: Path
    ) -> None:
        host = _Host(tmp_path)
        output_path = "chembl/activity/file.jsonl.zst"
        full_path = tmp_path / output_path
        full_path.parent.mkdir(parents=True)
        full_path.write_bytes(b"bronze-bytes")

        prepared = prepare_bronze_metadata_write(
            host,
            BronzeMetadataWriteRequest(
                run_id=RunID("run-1"),
                run_type=RunType.INCREMENTAL,
                provider="chembl",
                entity="activity",
                batch_id=BatchID("batch-1"),
                record_count=3,
                compressed_size=128,
                relative_path=output_path,
                ingestion_ts=datetime(2025, 1, 1, tzinfo=UTC),
                duration=2.5,
                source_metadata=None,
            ),
        )

        host._build_full_bronze_metadata.assert_called_once()
        source_metadata = host._build_full_bronze_metadata.call_args.kwargs[
            "source_metadata"
        ]
        assert source_metadata is not None
        assert len(source_metadata.input_snapshots) == 1
        assert source_metadata.input_snapshots[0].immutable_uri == str(full_path)
        assert prepared.metadata_base_path == tmp_path / "chembl" / "activity"

    def test_uses_coordinator_payload_when_configured(self, tmp_path: Path) -> None:
        host = _Host(tmp_path)
        coordinator = MagicMock()
        coordinator.create_bronze_metadata.return_value = MagicMock()
        host._metadata_coordinator = coordinator
        output_path = "pubmed/publication/file.jsonl.zst"
        full_path = tmp_path / output_path
        full_path.parent.mkdir(parents=True)
        full_path.write_bytes(b"replayable-input")

        prepared = prepare_bronze_metadata_write(
            host,
            BronzeMetadataWriteRequest(
                run_id=RunID("run-2"),
                run_type=RunType.BACKFILL,
                provider="pubmed",
                entity="publication",
                batch_id=BatchID("batch-2"),
                record_count=5,
                compressed_size=256,
                relative_path=output_path,
                ingestion_ts=datetime(2025, 2, 1, tzinfo=UTC),
                duration=1.0,
                source_metadata=SourceMetadata(type="api", query_string="page=1"),
            ),
        )

        host._build_full_bronze_metadata.assert_not_called()
        coordinator.create_bronze_metadata.assert_called_once()
        bronze_input = coordinator.create_bronze_metadata.call_args.args[0]
        assert bronze_input.record_count == 5
        assert bronze_input.output_path == output_path
        assert len(bronze_input.input_snapshots) == 1
        assert bronze_input.input_snapshots[0].immutable_uri == str(full_path)
        assert bronze_input.input_snapshots[0].query_fingerprint is not None
        assert prepared.metadata is coordinator.create_bronze_metadata.return_value

    def test_respects_flat_structure_for_metadata_base_path(
        self, tmp_path: Path
    ) -> None:
        host = _Host(tmp_path)
        host._flat_structure = True

        prepared = prepare_bronze_metadata_write(
            host,
            BronzeMetadataWriteRequest(
                run_id=RunID("run-3"),
                run_type=RunType.REBUILD,
                provider="uniprot",
                entity="protein",
                batch_id=BatchID("batch-3"),
                record_count=2,
                compressed_size=64,
                relative_path="uniprot/protein/file.jsonl.zst",
                ingestion_ts=datetime(2025, 3, 1, tzinfo=UTC),
                duration=0.5,
                source_metadata=None,
            ),
        )

        assert prepared.metadata_base_path == tmp_path
