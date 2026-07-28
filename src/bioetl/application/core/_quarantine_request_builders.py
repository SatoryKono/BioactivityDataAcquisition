"""Canonical request-shaping helpers for quarantine writes."""

from __future__ import annotations

from datetime import datetime

from bioetl.application.core._quarantine_metrics_support import FILTERED_OUT_SILVER
from bioetl.domain.ports import QuarantineWriteRequest
from bioetl.domain.types import BatchID, BronzeRecord, ErrorType, JsonDict, RunID


def build_filtered_quarantine_metadata(
    *,
    reason: str,
    details: JsonDict | None,
) -> JsonDict:
    """Build canonical quarantine metadata for Silver filter rejections."""
    error_details: JsonDict = {"message": reason}
    if details:
        error_details.update(
            {key: value for key, value in details.items() if key != "message"}
        )
    return {
        "error_details": error_details,
        "classification": "filter_rejection",
        "quarantine_category": "silver_filter",
    }

def build_dq_quarantine_request(
    *,
    pipeline_name: str,
    record: BronzeRecord,
    error_type: ErrorType,
    error_details: str,
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> QuarantineWriteRequest:
    """Build one DQ quarantine write request."""
    return {
        "pipeline": pipeline_name,
        "error_code": error_type.value,
        "payload": record,
        "bronze_batch_id": batch_id,
        "run_id": run_id,
        "metadata": {"error_details": {"message": error_details}},
        "ingestion_ts": ingestion_ts,
    }

def build_filtered_quarantine_request(
    *,
    pipeline_name: str,
    record: BronzeRecord,
    reason: str,
    details: JsonDict | None,
    batch_id: BatchID,
    run_id: RunID | None,
    ingestion_ts: datetime,
) -> QuarantineWriteRequest:
    """Build one filter-rejection quarantine write request."""
    return {
        "pipeline": pipeline_name,
        "error_code": FILTERED_OUT_SILVER,
        "payload": record,
        "bronze_batch_id": batch_id,
        "run_id": run_id,
        "metadata": build_filtered_quarantine_metadata(
            reason=reason,
            details=details,
        ),
        "ingestion_ts": ingestion_ts,
    }
