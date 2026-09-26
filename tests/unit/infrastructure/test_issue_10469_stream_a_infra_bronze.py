"""BronzeWriter facade leftovers not already covered by silver.py mixins."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.domain.exceptions import BronzeValidationError
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze.facade_contracts import (
    BronzeWriterRuntimeServices,
)
from bioetl.infrastructure.storage.bronze.metrics_mixin import BronzeWriterMetricsMixin
from bioetl.infrastructure.storage.bronze.pipeline_helpers import (
    BronzeWriteArtifacts,
    BronzeWritePostwriteContext,
    BronzeWritePrepared,
    BronzeWriteRequest,
    build_bronze_write_artifacts,
    prepare_bronze_write,
)
from bioetl.infrastructure.storage.bronze.side_effects_mixin import (
    BronzeWriterSideEffectsMixin,
)
from bioetl.infrastructure.storage.bronze.validation_mixin import (
    BronzeWriterValidationMixin,
)
from bioetl.infrastructure.storage.bronze.write_execution import (
    run_bronze_post_write_actions,
)
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

pytestmark = pytest.mark.unit


def _ids() -> tuple[RunID, BatchID]:
    return (
        RunID(UUID("00000000-0000-4000-8000-000000000001")),
        BatchID(UUID("00000000-0000-4000-8000-000000000002")),
    )


class _ValidationHost(BronzeWriterValidationMixin):
    def __init__(self, *, flat: bool = False) -> None:
        self._flat_structure = flat
        self.logger = NoOpLogger()


class TestBronzeWriterConstruction:
    def test_unexpected_and_conflicting_runtime_kwargs(self, tmp_path: Path) -> None:
        logger = NoOpLogger()
        metrics = NoOpMetrics()
        with pytest.raises(TypeError, match="unexpected keyword"):
            BronzeWriter(tmp_path, logger, metrics, unknown=True)
        services = BronzeWriterRuntimeServices(
            tracing=None,
            audit=None,
            metadata_writer=MagicMock(),
            save_metadata=False,
            metadata_coordinator=None,
        )
        with pytest.raises(TypeError, match="either runtime_services or legacy"):
            BronzeWriter(
                tmp_path,
                logger,
                metrics,
                runtime_services=services,
                audit=MagicMock(),
            )
        writer = BronzeWriter(tmp_path, logger, metrics)
        assert writer.validate_json is True
        assert writer._flat_structure is False
        packed = BronzeWriter(
            tmp_path,
            logger,
            metrics,
            runtime_services=services,
            flat_structure=True,
        )
        assert packed._flat_structure is True
        assert packed._metadata_writer is services.metadata_writer


class TestBronzeValidationAndPrepare:
    def test_validation_mixin_error_and_skip_paths(self) -> None:
        host = _ValidationHost()
        with pytest.raises(ValueError, match="Invalid provider"):
            host._validate_bronze_names("", "activity")
        with pytest.raises(ValueError, match="Invalid entity"):
            host._validate_bronze_names("chembl", "bad name")
        with pytest.raises(TypeError, match="cannot be None"):
            host._validate_records_iterator(None)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="Iterator"):
            host._validate_records_iterator(123)  # type: ignore[arg-type]
        naive = datetime(2024, 1, 1)
        with pytest.raises(ValueError, match="timezone-aware"):
            host._validate_utc_datetime(naive, "date")
        offset = datetime(2024, 1, 1, tzinfo=timezone(timedelta(hours=3)))
        with pytest.raises(ValueError, match="must be UTC"):
            host._validate_utc_datetime(offset, "date")
        host._validate_utc_datetime(datetime(2024, 1, 1, tzinfo=UTC), "date")
        with pytest.raises(BronzeValidationError, match="Invalid JSON"):
            list(host._validate_json_records(iter([b"not-json"])))
        assert list(host._validate_json_records(iter([b'{"id":1}']))) == [b'{"id":1}']
        assert host._resolve_bronze_path(
            "chembl", "activity", "2024-01-01", "f.jsonl"
        ) == ("chembl/activity/2024-01-01/f.jsonl")
        host._flat_structure = True
        assert host._resolve_bronze_path(
            "chembl", "activity", "2024-01-01", "f.jsonl"
        ) == ("2024-01-01/f.jsonl")

    def test_prepare_bronze_write_without_json_copy(self, tmp_path: Path) -> None:
        run_id, batch_id = _ids()
        now = datetime(2024, 1, 1, tzinfo=UTC)
        records = [b'{"id":1}']
        host = SimpleNamespace(
            base_path=tmp_path,
            save_json=False,
            validate_json=False,
            _validate_bronze_request_inputs=lambda _req: None,
            _validate_json_records=lambda recs: recs,
            _resolve_bronze_path=lambda provider, entity, date_str, filename: (
                f"{provider}/{entity}/{date_str}/{filename}"
            ),
            _build_bronze_metadata=lambda *_a, **_k: {"run_id": "x"},
        )
        prepared = prepare_bronze_write(
            host,
            BronzeWriteRequest(
                records=iter(records),
                provider="chembl",
                entity="activity",
                date=now,
                batch_id=batch_id,
                run_id=run_id,
                run_type=RunType.INCREMENTAL,
                ingestion_ts=now,
            ),
        )
        assert prepared.record_list == []
        assert prepared.relative_path.endswith(".jsonl.zst")
        payload = tmp_path / "out.jsonl.zst"
        payload.write_bytes(b"abc")
        artifacts = build_bronze_write_artifacts(
            full_path=payload, record_count=1, uncompressed_size=3
        )
        assert artifacts.compressed_size == 3


class TestBronzeMetricsSideEffectsAndWriter:
    def test_metrics_mixin_emits(self) -> None:
        mixin = BronzeWriterMetricsMixin()
        mixin._metrics = MagicMock()
        mixin.logger = MagicMock()
        run_id, batch_id = _ids()
        mixin._emit_bronze_write_metrics(
            duration=1.25,
            provider="chembl",
            entity="activity",
            record_count=2,
            compressed_size=10,
            uncompressed_size=20,
            relative_path="p.jsonl.zst",
            batch_id=batch_id,
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
        )
        mixin._metrics.observe_histogram.assert_called()
        mixin.logger.info.assert_called()

    async def test_audit_skip_and_postwrite_skips(self, tmp_path: Path) -> None:
        mixin = BronzeWriterSideEffectsMixin()
        mixin._audit = None
        await mixin._log_bronze_audit(
            run_id=_ids()[0],
            ingestion_ts=datetime(2024, 1, 1, tzinfo=UTC),
            relative_path="p.jsonl.zst",
            batch_id=_ids()[1],
            run_type=RunType.INCREMENTAL,
            record_count=1,
            compressed_size=1,
            uncompressed_size=1,
            provider="chembl",
            entity="activity",
        )
        host = SimpleNamespace(
            save_json=False,
            _audit=None,
            _save_metadata=False,
            _emit_bronze_write_metrics=MagicMock(),
            _write_json_copy=AsyncMock(),
            _log_bronze_audit=AsyncMock(),
            _maybe_write_bronze_metadata=AsyncMock(),
        )
        run_id, batch_id = _ids()
        now = datetime(2024, 1, 1, tzinfo=UTC)
        request = BronzeWriteRequest(
            records=iter([b'{"id":1}']),
            provider="chembl",
            entity="activity",
            date=now,
            batch_id=batch_id,
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            ingestion_ts=now,
        )
        prepared = BronzeWritePrepared(
            records_iter=iter([b'{"id":1}']),
            record_list=[],
            date_str="2024-01-01",
            relative_path="chembl/activity/2024-01-01/batch.jsonl.zst",
            metadata={"run_id": "x"},
            full_path=tmp_path / "out.jsonl.zst",
            meta_path=tmp_path / "out.jsonl.zst.meta.json",
        )
        await run_bronze_post_write_actions(
            host,
            BronzeWritePostwriteContext(
                request=request,
                prepared=prepared,
                write_artifacts=BronzeWriteArtifacts(
                    record_count=1, uncompressed_size=1, compressed_size=1
                ),
                duration=0.1,
            ),
        )
        host._write_json_copy.assert_not_awaited()
        host._log_bronze_audit.assert_not_awaited()
        host._maybe_write_bronze_metadata.assert_not_awaited()

    async def test_write_bronze_with_tracing_mocked(self, tmp_path: Path) -> None:
        writer = BronzeWriter(tmp_path, NoOpLogger(), NoOpMetrics())
        run_id, batch_id = _ids()
        now = datetime(2024, 1, 1, tzinfo=UTC)
        prepared = SimpleNamespace(
            relative_path="p.jsonl.zst", full_path=tmp_path / "p"
        )
        artifacts = BronzeWriteArtifacts(
            record_count=1, uncompressed_size=2, compressed_size=1
        )
        writer._prepare_bronze_write = MagicMock(return_value=prepared)  # type: ignore[method-assign]
        writer._write_bronze_data_and_sidecar = AsyncMock(return_value=artifacts)  # type: ignore[method-assign]
        writer._run_bronze_post_write_actions = AsyncMock()  # type: ignore[method-assign]
        writer._build_bronze_write_result = AsyncMock(  # type: ignore[method-assign]
            return_value=SimpleNamespace(record_count=1)
        )
        result = await writer.write_bronze(
            iter([b'{"id":1}']),
            "chembl",
            "activity",
            now,
            batch_id,
            run_id,
            RunType.INCREMENTAL,
            now,
        )
        assert result.record_count == 1
        writer._run_bronze_post_write_actions.assert_awaited()
        writer._validate_bronze_request_inputs(
            BronzeWriteRequest(
                records=iter([b'{"id":1}']),
                provider="chembl",
                entity="activity",
                date=now,
                batch_id=batch_id,
                run_id=run_id,
                run_type=RunType.INCREMENTAL,
                ingestion_ts=now,
            )
        )
        with pytest.raises(ValueError, match="Invalid provider"):
            writer._validate_bronze_request_inputs(
                BronzeWriteRequest(
                    records=iter([b'{"id":1}']),
                    provider="",
                    entity="activity",
                    date=now,
                    batch_id=batch_id,
                    run_id=run_id,
                    run_type=RunType.INCREMENTAL,
                    ingestion_ts=now,
                )
            )
