"""Freeze normalized ChEMBL Silver inputs and a traceable canonical CSV conversion."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pyarrow as pa

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from iuphar_target_class.csv_io import read_csv_records
from iuphar_target_class.pipeline_io import BIOETL_TARGET_KERNEL_CSV_V1
from iuphar_target_class.stage0.io import (
    canonical_csv_bytes,
    canonical_json_bytes,
    sha256_bytes,
)

from ._input_projection import project_target_fields

NORMALIZED_TARGET_SCHEMA = "chembl.target.normalized_silver.v1"
CSV_SOURCE_FORMAT = "chembl_target_silver_csv_v1"
ARROW_SOURCE_FORMAT = "chembl_target_silver_arrow_ipc_v1"
_RESERVED = frozenset(
    {
        "input_row_id",
        "target_kind",
        "import_profile",
        "source_path",
        "source_sha256",
        "source_record",
        "source_business_data",
    }
)
_REQUIRED = frozenset(
    {
        "target_id",
        "target_type",
        "taxonomy_id",
        "pref_name",
        "organism",
        "component_accessions",
    }
)
_COLUMNS = (
    "input_row_id",
    "target_kind",
    "target_chembl_id",
    "target_id",
    "uniprot",
    "organism",
    "name",
    "source_organism",
    "synonyms",
    "ec",
    "gene_symbol",
    "gene_id",
    "source_business_data",
)


class CohortConversionError(ValueError):
    """A rejected record with an explicit diagnostic for the immutable ledger."""

    def __init__(self, message: str, source_record: int, row_id: str) -> None:
        super().__init__(message)
        self.source_record = source_record
        self.row_id = row_id


@dataclass(frozen=True, slots=True)
class CohortExportRequest:
    """Technical source contract; no field grants biological/reference approval."""

    source_path: Path
    source_sha256: str
    source_format: Literal[
        "chembl_target_silver_csv_v1", "chembl_target_silver_arrow_ipc_v1"
    ]
    source_schema_version: str
    approval_reference: str
    environment: str
    target_kind: Literal["protein"] = "protein"
    direct_iuphar_id_column: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalCohortExport:
    canonical_path: Path
    raw_copy_path: Path
    conversion_ledger_path: Path
    canonical_sha256: str
    raw_sha256: str
    conversion_ledger_sha256: str
    row_ids: tuple[str, ...]


def _validate_request(request: CohortExportRequest) -> None:
    if (
        request.source_schema_version != NORMALIZED_TARGET_SCHEMA
        or request.target_kind != "protein"
    ):
        raise ValueError("explicit normalized ChEMBL target v1 protein schema required")
    if request.source_format not in {CSV_SOURCE_FORMAT, ARROW_SOURCE_FORMAT}:
        raise ValueError("unsupported normalized target source format")
    if not request.approval_reference.strip() or not request.environment.strip():
        raise ValueError(
            "technical mapping reference and execution environment required"
        )
    if re.fullmatch(r"[0-9a-f]{64}", request.source_sha256) is None:
        raise ValueError("expected pinned normalized source SHA-256")
    if request.direct_iuphar_id_column in {
        "target_id",
        "target_chembl_id",
        "entity_id",
    }:
        raise ValueError("ChEMBL identity cannot be selected as direct IUPHAR identity")


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


from .canonical_target_rows import _source_rows, render_canonical_target_rows


__all__ = [
    "ARROW_SOURCE_FORMAT",
    "CSV_SOURCE_FORMAT",
    "NORMALIZED_TARGET_SCHEMA",
    "CanonicalCohortExport",
    "CohortExportRequest",
    "export_canonical_cohort",
    "render_canonical_target_rows",
]
