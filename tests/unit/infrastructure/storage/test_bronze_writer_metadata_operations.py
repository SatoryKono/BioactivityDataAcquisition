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


class _BundleCoordinator:
    def __init__(self, metadata: object, fragment: object) -> None:
        self.metadata = metadata
        self.fragment = fragment
        self.last_input: object | None = None

    def create_bronze_metadata_bundle(self, input_data: object) -> object:
        self.last_input = input_data
        return MagicMock(metadata=self.metadata, lineage_fragment=self.fragment)


@pytest.mark.unit
class TestPrepareBronzeMetadataWrite:
    def test_raises_when_coordinator_missing(self, tmp_path: Path) -> None:
        host = _Host(tmp_path)
        output_path = "chembl/activity/file.jsonl.zst"
        full_path = tmp_path / output_path
        full_path.parent.mkdir(parents=True)
        full_path.write_bytes(b"bronze-bytes")

        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinator with create_bronze_metadata_bundle is required",
        ):
            prepare_bronze_metadata_write(
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

    def test_uses_coordinator_bundle_when_configured(self, tmp_path: Path) -> None:
        host = _Host(tmp_path)
        metadata = MagicMock()
        fragment = MagicMock()
        coordinator = _BundleCoordinator(metadata=metadata, fragment=fragment)
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

        bronze_input = coordinator.last_input
        assert bronze_input.record_count == 5
        assert bronze_input.output_path == output_path
        assert len(bronze_input.input_snapshots) == 1
        assert bronze_input.input_snapshots[0].immutable_uri == str(full_path)
        assert bronze_input.input_snapshots[0].query_fingerprint is not None
        assert prepared.metadata is metadata
        assert prepared.lineage_fragment is fragment

    def test_raises_when_bundle_factory_missing(self, tmp_path: Path) -> None:
        host = _Host(tmp_path)

        class _CoordinatorWithoutBundle:
            def create_bronze_metadata(self, input_data: object) -> object:
                return input_data

        host._metadata_coordinator = _CoordinatorWithoutBundle()
        output_path = "pubmed/publication/file.jsonl.zst"
        full_path = tmp_path / output_path
        full_path.parent.mkdir(parents=True)
        full_path.write_bytes(b"replayable-input")

        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinator with create_bronze_metadata_bundle is required",
        ):
            prepare_bronze_metadata_write(
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

    def test_respects_flat_structure_for_metadata_base_path(
        self, tmp_path: Path
    ) -> None:
        host = _Host(tmp_path)
        host._flat_structure = True
        host._metadata_coordinator = _BundleCoordinator(
            metadata=MagicMock(),
            fragment=MagicMock(),
        )

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
