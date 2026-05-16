"""Unit tests for BronzeWriterMetadataMixin."""

from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze.metadata_mixin import (
    BronzeWriterMetadataMixin,
)


class _Host(BronzeWriterMetadataMixin):
    """Minimal host that wires the mixin for isolated testing."""

    def __init__(self) -> None:
        self.logger = MagicMock()
        self._metadata_coordinator = None


@pytest.mark.unit
class TestBronzeWriterMetadataMixin:
    """Tests for Bronze metadata construction helpers."""

    def test_build_bronze_metadata_returns_expected_keys(self) -> None:
        """_build_bronze_metadata should fall back to the legacy sidecar contract."""
        host = _Host()
        ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        metadata = host._build_bronze_metadata(
            run_id=RunID("run-123"),
            run_type=RunType.INCREMENTAL,
            effective_ts=ts,
            provider="chembl",
            entity="activity",
            batch_id=BatchID("batch-001"),
        )

        assert metadata == {
            "run_id": "run-123",
            "run_type": "incremental",
            "ingestion_ts": ts.isoformat(),
            "provider": "chembl",
            "entity": "activity",
            "batch_id": "batch-001",
        }

    def test_build_bronze_metadata_backfill_run_type(self) -> None:
        """Legacy fallback should preserve run_type semantics without a coordinator."""
        host = _Host()
        ts = datetime(2025, 3, 1, 0, 0, 0, tzinfo=UTC)
        metadata = host._build_bronze_metadata(
            run_id=RunID("run-456"),
            run_type=RunType.BACKFILL,
            effective_ts=ts,
            provider="pubmed",
            entity="publication",
            batch_id=BatchID("batch-002"),
        )

        assert metadata["run_type"] == "backfill"

    def test_build_bronze_metadata_prefers_coordinator_projection(self) -> None:
        """Coordinator-backed Bronze writers should project the legacy sidecar centrally."""
        host = _Host()
        ts = datetime(2025, 3, 1, 0, 0, 0, tzinfo=UTC)
        host._metadata_coordinator = MagicMock()
        host._metadata_coordinator.create_bronze_lineage_sidecar.return_value = {
            "run_id": "run-coordinator",
            "manifest_id": "manifest-coordinator",
            "run_type": "incremental",
            "ingestion_ts": ts.isoformat(),
            "provider": "chembl",
            "entity": "activity",
            "batch_id": "batch-003",
            "execution_fingerprint": "fingerprint-coordinator",
            "effective_config_hash": "a" * 64,
        }

        result = host._build_bronze_metadata(
            run_id=RunID("run-ignored"),
            run_type=RunType.INCREMENTAL,
            effective_ts=ts,
            provider="chembl",
            entity="activity",
            batch_id=BatchID("batch-003"),
        )

        assert result["run_id"] == "run-coordinator"
        assert result["manifest_id"] == "manifest-coordinator"
        assert result["execution_fingerprint"] == "fingerprint-coordinator"
        assert result["effective_config_hash"] == "a" * 64
        host._metadata_coordinator.create_bronze_lineage_sidecar.assert_called_once()

    def test_build_bronze_metadata_payload_returns_dict_with_runtime_key(self) -> None:
        """Legacy Bronze sidecar payload builder should fail closed."""
        host = _Host()
        started = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        completed = datetime(2025, 1, 15, 12, 0, 5, tzinfo=UTC)
        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinator with create_bronze_metadata_bundle is required",
        ):
            host._build_bronze_metadata_payload(
                run_id=RunID("run-789"),
                run_type=RunType.REBUILD,
                provider="chembl",
                entity="compound",
                record_count=100,
                compressed_size=2048,
                output_path="chembl/compound/2025-01-15/data.jsonl.zst",
                started_at=started,
                completed_at=completed,
                duration_seconds=5.0,
                source_metadata=None,
            )

    def test_build_full_bronze_metadata_returns_bronze_metadata_instance(self) -> None:
        """Legacy Bronze sidecar model builder should fail closed."""
        host = _Host()
        started = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        completed = datetime(2025, 1, 15, 12, 0, 5, tzinfo=UTC)
        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinator with create_bronze_metadata_bundle is required",
        ):
            host._build_full_bronze_metadata(
                run_id=RunID("run-full"),
                run_type=RunType.INCREMENTAL,
                provider="chembl",
                entity="mechanism",
                batch_id=BatchID("batch-full"),
                record_count=50,
                compressed_size=1024,
                output_path="chembl/mechanism/2025-01-15/data.jsonl.zst",
                started_at=started,
                completed_at=completed,
                duration_seconds=5.0,
                source_metadata=None,
            )
