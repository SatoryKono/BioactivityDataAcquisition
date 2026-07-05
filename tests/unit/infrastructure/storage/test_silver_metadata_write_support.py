"""Unit tests for Silver metadata write support helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.infrastructure.storage.silver.operations.metadata_write_support import (
    _SilverMetadataAuditSupportRequest,
    _SilverMetadataWriteSupportRequest,
    _emit_silver_metadata_write_success,
    _fallback_table_path,
    _log_silver_audit_event,
    _normalize_metric_label,
    _require_metadata_coordinator,
    _resolve_metadata_logger,
    _silver_metadata_write_success_labels,
    _source_batch_ids,
    _write_silver_metadata,
)


@dataclass
class _Ops:
    _metrics: object | None = None
    _audit: object | None = None
    _metadata_coordinator: object | None = None
    _persist_silver_metadata: object | None = None
    _logger: object | None = None
    logger: object | None = None


@pytest.mark.unit
class TestSilverMetadataWriteSupport:
    """Coverage-oriented tests for support-layer pure helpers."""

    def test_resolve_metadata_logger_prefers_private_then_public_and_errors(
        self,
    ) -> None:
        logger = MagicMock()
        assert _resolve_metadata_logger(_Ops(_logger=logger)) is logger
        assert _resolve_metadata_logger(_Ops(logger=logger, _logger=None)) is logger
        with pytest.raises(
            AttributeError,
            match="must expose either '_logger' or 'logger'",
        ):
            _resolve_metadata_logger(_Ops())

    def test_metadata_path_and_metric_label_helpers(self) -> None:
        assert (
            _fallback_table_path("chembl.activity")
            == "data/output/silver/chembl/activity"
        )
        assert (
            _normalize_metric_label("ChEMBL Activity!", fallback="x")
            == "chembl_activity"
        )
        assert _normalize_metric_label("", fallback="x") == "x"
        assert _silver_metadata_write_success_labels("chembl.activity") == {
            "layer": "silver",
            "provider": "chembl",
            "pipeline": "chembl_activity",
            "status": "success",
            "final_reason": "completed",
        }
        assert (
            _silver_metadata_write_success_labels("tableonly")["provider"] == "storage"
        )

    def test_require_coordinator_and_source_batch_ids(self) -> None:
        coordinator = object()
        assert (
            _require_metadata_coordinator(_Ops(_metadata_coordinator=coordinator))
            is coordinator
        )
        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinatorPort is required for Silver metadata publication",
        ):
            _require_metadata_coordinator(_Ops())

        assert _source_batch_ids(None) is None
        assert _source_batch_ids("batch-1") == ["batch-1"]

    def test_audit_support_request_defaults_optional_identity_fields(self) -> None:
        request = _SilverMetadataAuditSupportRequest(
            table_name="chembl.activity",
            records=[{"entity_id": "CHEMBL1"}],
            mode=SilverWriteMode.MERGE,
        )
        assert request.run_id is None
        assert request.source_batch_id is None

    @pytest.mark.asyncio
    async def test_write_silver_metadata_builds_payload_and_emits_metrics(self) -> None:
        coordinator = MagicMock()
        metadata = MagicMock()
        coordinator.create_silver_metadata.return_value = metadata
        ops = _Ops(
            _metadata_coordinator=coordinator,
            _metrics=MagicMock(),
            _audit=MagicMock(),
        )
        ops._persist_silver_metadata = AsyncMock(return_value="persisted")
        dq_metrics = BatchDQMetrics(total_records=1, valid_records=1)
        request = _SilverMetadataWriteSupportRequest(
            table_name="chembl.activity",
            dq_metrics=dq_metrics,
            records=[{"entity_id": "CHEMBL1"}],
            validated_mode=SilverWriteMode.MERGE,
            transform_version="2.0.0",
            transform_steps=("normalize",),
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )

        result = await _write_silver_metadata(ops, request)

        assert result == "persisted"
        coordinator.create_silver_metadata.assert_called_once()
        persist_call = ops._persist_silver_metadata.await_args.kwargs
        assert persist_call["table_name"] == "chembl.activity"
        assert persist_call["table_path"] == "data/output/silver/chembl/activity"
        ops._metrics.increment_counter.assert_called_once()
        ops._audit.log_event.assert_called_once()

    def test_emit_silver_metadata_write_success_without_audit_is_safe(self) -> None:
        metrics = MagicMock()
        ops = _Ops(_metrics=metrics, _audit=None)

        _emit_silver_metadata_write_success(
            ops,
            "chembl.activity",
            [{"entity_id": "CHEMBL1"}],
            BatchDQMetrics(total_records=1, valid_records=1),
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )

        metrics.increment_counter.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_silver_audit_event_is_noop_without_audit_and_writes_with_audit(
        self,
    ) -> None:
        request = _SilverMetadataAuditSupportRequest(
            table_name="chembl.activity",
            records=[{"entity_id": "CHEMBL1"}],
            mode=SilverWriteMode.MERGE,
        )

        ops = _Ops(_audit=None)
        await _log_silver_audit_event(ops, request)

        audit = MagicMock()
        audit.log_write = AsyncMock()
        ops = _Ops(_audit=audit, _logger=MagicMock())
        audit_entry = MagicMock()
        with patch(
            "bioetl.infrastructure.storage.silver.audit_operations._build_silver_audit_entry",
            return_value=audit_entry,
        ):
            await _log_silver_audit_event(ops, request)

        audit.log_write.assert_awaited_once_with(audit_entry)
