"""Unit tests for debug export audit-pack collection."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID

import pytest

from bioetl.application.services.debug_export_service import (
    DebugExportConfig,
    DebugExportResult,
    DebugExportService,
)
from bioetl.domain.types import ErrorType

pytestmark = pytest.mark.unit

_RUN_ID = UUID("00000000-0000-0000-0000-000000000101")
_BATCH_ID = UUID("00000000-0000-0000-0000-000000000102")


def test_debug_export_service_collects_success_and_failure_rows() -> None:
    service = DebugExportService(
        config=DebugExportConfig(enabled=True, formats=("csv",)),
        run_id=_RUN_ID,
        pipeline_id="chembl_activity",
        provider_id="chembl",
    )

    raw_record = {"activity_id": "ACT-1", "value": "bad", "content_hash": "bronze-h1"}
    silver_record = {"activity_id": "ACT-1", "value": 1.0, "content_hash": "silver-h1"}
    gold_record = {"activity_id": "ACT-1", "value": 1.0, "content_hash": "gold-h1"}

    service.record_bronze_batch(
        records=[raw_record],
        batch_id=_BATCH_ID,
        start_index=17,
    )
    service.record_transform_success(
        raw_record=raw_record,
        record_index=17,
        silver_record=silver_record,
        gold_record=gold_record,
        gold_excluded_by_contract=False,
    )
    service.record_filtered_out(
        raw_record={"activity_id": "ACT-2", "content_hash": "bronze-h2"},
        record_index=18,
        reason="soft filter rejected record",
        details={"activity_id": "ACT-2"},
        policy="skip",
    )
    service.record_data_quality_failure(
        raw_record={
            "activity_id": "ACT-3",
            "target_chembl_id": None,
            "content_hash": "bronze-h3",
        },
        record_index=19,
        error_type=ErrorType.SCHEMA_VIOLATION,
        error_details="Schema validation failed: missing target_chembl_id",
        policy="quarantine",
    )

    pack = service.build_pack(status="failed")

    assert len(pack.tables["bronze_index"]) == 1
    assert pack.tables["bronze_index"][0]["record_index"] == 17
    assert len(pack.tables["silver_full"]) == 1
    assert pack.tables["silver_full"][0]["payload_hash"] == "silver-h1"
    assert len(pack.tables["gold_full"]) == 1
    assert pack.tables["gold_full"][0]["payload_hash"] == "gold-h1"
    assert len(pack.tables["silver_rejected"]) == 1
    assert pack.tables["silver_rejected"][0]["reason_code"] == "DQ_SOFT_RULE_FAILED"
    assert len(pack.tables["silver_quarantine"]) == 1
    assert (
        pack.tables["silver_quarantine"][0]["reason_code"]
        == "SCHEMA_REQUIRED_FIELD_MISSING"
    )
    assert len(pack.tables["dq_summary"]) == 2


def test_debug_export_service_hashes_records_without_content_hash() -> None:
    service = DebugExportService(
        config=DebugExportConfig(enabled=True, formats=("csv",)),
        run_id=_RUN_ID,
        pipeline_id="chembl_target",
        provider_id="chembl",
    )

    service.record_bronze_batch(
        records=[{"target_chembl_id": "CHEMBL1", "pref_name": "EGFR"}],
        batch_id=_BATCH_ID,
        start_index=0,
    )

    pack = service.build_pack()

    payload_hash = pack.tables["bronze_index"][0]["payload_hash"]
    assert isinstance(payload_hash, str)
    assert payload_hash


def test_debug_export_service_finalize_persists_pack_with_manifest_id() -> None:
    writer = Mock()
    writer.write_pack.return_value = DebugExportResult(
        root_path="artifacts/debug_exports/standalone/chembl_activity/run-1",
        manifest_path="artifacts/debug_exports/standalone/chembl_activity/run-1/manifest.json",
        debug_export_hash="hash-1",
    )
    service = DebugExportService(
        config=DebugExportConfig(enabled=True, formats=("csv",)),
        run_id=_RUN_ID,
        pipeline_id="chembl_activity",
        provider_id="chembl",
        writer=writer,
    )

    result = service.finalize(status="failed", manifest_id="manifest-123")

    assert result is not None
    written_pack = writer.write_pack.call_args.kwargs["pack"]
    assert written_pack.status == "failed"
    assert written_pack.manifest_id == "manifest-123"
    assert written_pack.tables["bronze_index"] == ()


def test_debug_export_service_serializes_datetime_source_metadata() -> None:
    service = DebugExportService(
        config=DebugExportConfig(enabled=True, formats=("csv",)),
        run_id=_RUN_ID,
        pipeline_id="chembl_target",
        provider_id="chembl",
    )

    source_metadata = {
        "fetched_at": datetime(2026, 6, 2, 10, 13, 6, tzinfo=UTC),
        "page": 1,
    }
    service.record_bronze_batch(
        records=[{"target_chembl_id": "CHEMBL1", "pref_name": "EGFR"}],
        batch_id=_BATCH_ID,
        start_index=0,
        source_metadata=source_metadata,
    )

    pack = service.build_pack()

    assert "2026-06-02T10:13:06+00:00" in pack.tables["bronze_index"][0]["source_metadata"]


def test_debug_export_service_preserves_semantic_gold_filter_diagnostics() -> None:
    service = DebugExportService(
        config=DebugExportConfig(enabled=True, formats=("csv",)),
        run_id=_RUN_ID,
        pipeline_id="chembl_assay",
        provider_id="chembl",
    )

    service.record_transform_success(
        raw_record={"assay_chembl_id": "CHEMBL1", "content_hash": "bronze-h1"},
        record_index=316,
        silver_record={
            "entity_id": "chembl:CHEMBL1",
            "bao_format": "BAO_0000218",
            "content_hash": "silver-h1",
        },
        gold_record=None,
        gold_excluded_by_contract=True,
        gold_filter_details={
            "include": False,
            "reason_code": "column_filter_mismatch",
            "rule_type": "column_filters",
            "field": "bao_format",
            "operator": "not_in",
            "expected": ["BAO_0000218"],
            "actual": "BAO_0000218",
            "message": "Field 'bao_format' failed column filter not_in",
        },
    )

    pack = service.build_pack(status="success")
    row = pack.tables["gold_rejected"][0]

    assert row["reason_code"] == "SEMANTIC_FILTER_EXCLUDED"
    assert row["rule_id"] == "column_filters"
    assert row["failed_field"] == "bao_format"
    assert row["failed_value"] == "BAO_0000218"
    assert row["expected_constraint"] == 'not_in ["BAO_0000218"]'


def test_debug_export_service_preserves_structured_silver_rejected_diagnostics() -> None:
    service = DebugExportService(
        config=DebugExportConfig(enabled=True, formats=("csv",)),
        run_id=_RUN_ID,
        pipeline_id="chembl_assay",
        provider_id="chembl",
    )

    service.record_filtered_out(
        raw_record={
            "assay_chembl_id": "CHEMBL42",
            "assay_test_type": "In vivo",
            "content_hash": "bronze-h42",
        },
        record_index=42,
        reason="Gold-style semantic filter rejected the Silver record",
        details={
            "field": "assay_test_type",
            "operator": "not_in",
            "expected": ["In vivo", "Ex vivo"],
            "actual": "In vivo",
        },
        policy="skip",
    )

    pack = service.build_pack(status="failed")
    row = pack.tables["silver_rejected"][0]

    assert row["failed_field"] == "assay_test_type"
    assert row["failed_value"] == "In vivo"
    assert row["expected_constraint"] == 'not_in ["In vivo", "Ex vivo"]'


def test_debug_export_service_preserves_structured_silver_quarantine_diagnostics() -> None:
    service = DebugExportService(
        config=DebugExportConfig(enabled=True, formats=("csv",)),
        run_id=_RUN_ID,
        pipeline_id="chembl_activity",
        provider_id="chembl",
    )

    service.record_data_quality_failure(
        raw_record={
            "activity_id": "ACT-77",
            "target_chembl_id": None,
            "content_hash": "bronze-h77",
        },
        record_index=77,
        error_type=ErrorType.SCHEMA_VIOLATION,
        error_details="Schema validation failed: target_chembl_id is required",
        details_payload={
            "field": "target_chembl_id",
            "constraint": "non-empty",
            "actual": None,
        },
        policy="quarantine",
    )

    pack = service.build_pack(status="failed")
    row = pack.tables["silver_quarantine"][0]

    assert row["failed_field"] == "target_chembl_id"
    assert row["failed_value"] == "None"
    assert row["expected_constraint"] == "non-empty"
