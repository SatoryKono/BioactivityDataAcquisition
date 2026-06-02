"""Unit tests for debug export audit-pack collection."""

from __future__ import annotations

from uuid import uuid4

from bioetl.application.services.debug_export_service import (
    DebugExportConfig,
    DebugExportService,
)
from bioetl.domain.types import ErrorType


def test_debug_export_service_collects_success_and_failure_rows() -> None:
    service = DebugExportService(
        config=DebugExportConfig(enabled=True, formats=("csv",)),
        run_id=uuid4(),
        pipeline_id="chembl_activity",
        provider_id="chembl",
    )

    raw_record = {"activity_id": "ACT-1", "value": "bad"}
    silver_record = {"activity_id": "ACT-1", "value": 1.0, "content_hash": "silver-h1"}
    gold_record = {"activity_id": "ACT-1", "value": 1.0, "content_hash": "gold-h1"}

    service.record_bronze_batch(
        records=[raw_record],
        batch_id=uuid4(),
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
        raw_record={"activity_id": "ACT-2"},
        record_index=18,
        reason="soft filter rejected record",
        details={"activity_id": "ACT-2"},
        policy="skip",
    )
    service.record_data_quality_failure(
        raw_record={"activity_id": "ACT-3", "target_chembl_id": None},
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
