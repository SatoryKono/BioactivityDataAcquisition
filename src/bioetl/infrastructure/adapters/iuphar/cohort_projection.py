"""Freeze normalized ChEMBL Silver inputs and their canonical conversion."""

from __future__ import annotations

from pathlib import Path

from iuphar_target_class.pipeline_io import BIOETL_TARGET_KERNEL_CSV_V1
from iuphar_target_class.stage0.io import canonical_json_bytes, sha256_bytes

from .canonical_target_rows import _source_rows, render_canonical_target_rows
from .cohort_contract import (
    ARROW_SOURCE_FORMAT,
    CSV_SOURCE_FORMAT,
    NORMALIZED_TARGET_SCHEMA,
    CanonicalCohortExport,
    CohortConversionError,
    CohortExportRequest,
    _validate_request,
)


def export_canonical_cohort(
    request: CohortExportRequest, *, output_dir: Path
) -> CanonicalCohortExport:
    """Convert an exact source file into a new immutable raw/canonical bundle."""
    _validate_request(request)
    raw = request.source_path.read_bytes()
    if sha256_bytes(raw) != request.source_sha256:
        raise ValueError("normalized target source digest mismatch")
    rows = _source_rows(raw, request.source_format)
    try:
        canonical, row_ids, records = render_canonical_target_rows(
            rows, request=request
        )
    except CohortConversionError as error:
        _publish_rejection(request, output_dir, raw, error)
        raise
    ledger = canonical_json_bytes(
        {
            "artifact": "bioetl_target_cohort_conversion",
            "schema_version": 1,
            "producer_version": "bioetl-target-cohort-export-v1",
            "source_schema_version": request.source_schema_version,
            "source_format": request.source_format,
            "technical_mapping_reference": request.approval_reference,
            "environment": request.environment,
            "target_kind": request.target_kind,
            "direct_iuphar_id_column": request.direct_iuphar_id_column,
            "biological_accuracy_accepted": False,
            "eligibility_approval_granted": False,
            "raw_source": {"sha256": sha256_bytes(raw), "byte_count": len(raw)},
            "canonical": {
                "sha256": sha256_bytes(canonical),
                "byte_count": len(canonical),
                "row_count": len(row_ids),
                "format_version": BIOETL_TARGET_KERNEL_CSV_V1,
            },
            "records": records,
        }
    )
    output = output_dir.resolve()
    if request.source_path.resolve().is_relative_to(output):
        raise ValueError("cohort output cannot contain or replace its source")
    output.mkdir(parents=True, exist_ok=False)
    return _publish_bundle(output, raw, canonical, ledger, row_ids)


def _publish_rejection(
    request: CohortExportRequest,
    output_dir: Path,
    raw: bytes,
    error: CohortConversionError,
) -> None:
    output = output_dir.resolve()
    if request.source_path.resolve().is_relative_to(output):
        raise ValueError("cohort output cannot contain or replace its source")
    output.mkdir(parents=True, exist_ok=False)
    (output / "raw-source.bin").write_bytes(raw)
    (output / "conversion-ledger.json").write_bytes(
        canonical_json_bytes(
            {
                "artifact": "bioetl_target_cohort_conversion",
                "schema_version": 1,
                "status": "REJECTED",
                "raw_source": {"sha256": sha256_bytes(raw), "byte_count": len(raw)},
                "diagnostic": {
                    "code": "duplicate_target_identity",
                    "source_record": error.source_record,
                    "canonical_row_id": error.row_id,
                    "reason": str(error),
                },
                "biological_accuracy_accepted": False,
            }
        )
    )


def _publish_bundle(
    output: Path, raw: bytes, canonical: bytes, ledger: bytes, row_ids: tuple[str, ...]
) -> CanonicalCohortExport:
    paths = (
        output / "raw-source.bin",
        output / "cohort.csv",
        output / "conversion-ledger.json",
    )
    for path, payload in zip(paths, (raw, canonical, ledger), strict=True):
        with path.open("xb") as stream:
            stream.write(payload)
        if path.read_bytes() != payload:
            raise ValueError("cohort bundle bytes changed during publication")
    return CanonicalCohortExport(
        paths[1],
        paths[0],
        paths[2],
        sha256_bytes(canonical),
        sha256_bytes(raw),
        sha256_bytes(ledger),
        row_ids,
    )


__all__ = [
    "ARROW_SOURCE_FORMAT",
    "CSV_SOURCE_FORMAT",
    "NORMALIZED_TARGET_SCHEMA",
    "CanonicalCohortExport",
    "CohortExportRequest",
    "export_canonical_cohort",
    "render_canonical_target_rows",
]
