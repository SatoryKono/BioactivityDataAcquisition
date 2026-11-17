"""Pure canonical-row projection for a frozen normalized target cohort."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

import pyarrow as pa

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from iuphar_target_class.csv_io import read_csv_records
from iuphar_target_class.stage0.io import (
    canonical_csv_bytes,
    canonical_json_bytes,
    sha256_bytes,
)

from ._input_projection import project_target_fields
from .cohort_contract import (
    _COLUMNS,
    _REQUIRED,
    _RESERVED,
    ARROW_SOURCE_FORMAT,
    CohortConversionError,
    CohortExportRequest,
    _validate_request,
)


def _source_rows(raw: bytes, source_format: str) -> tuple[Mapping[str, object], ...]:
    if source_format == ARROW_SOURCE_FORMAT:
        with pa.ipc.open_stream(pa.BufferReader(raw)) as reader:
            return tuple(reader.read_all().to_pylist())
    headers, rows = read_csv_records(raw)
    if len(headers) != len(set(headers)) or not headers:
        raise ValueError("normalized source needs distinct nonempty CSV headers")
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("invalid normalized source CSV row width")
    return rows


def render_canonical_target_rows(
    rows: Sequence[Mapping[str, object]], *, request: CohortExportRequest
) -> tuple[bytes, tuple[str, ...], list[dict[str, object]]]:
    """Pure Arrow/Delta caller seam using the same runtime field projection.

    Callers must freeze their whole source snapshot before using the published
    file exporter; this projection alone is not a source/admission receipt.
    """
    _validate_request(request)
    converted: list[dict[str, str]] = []
    ledger: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        projected = _canonical_row(row, request)
        identity = projected["input_row_id"]
        if identity in seen:
            raise CohortConversionError(
                f"duplicate target identity at source record {index}: {identity}",
                index,
                identity,
            )
        seen.add(identity)
        converted.append(projected)
        ledger.append(
            {
                "source_record": index,
                "canonical_row_id": identity,
                "canonical_row_sha256": sha256_bytes(canonical_json_bytes(projected)),
            }
        )
    if not converted:
        raise ValueError("empty normalized target cohort cannot be admitted")
    return (
        canonical_csv_bytes(_COLUMNS, converted),
        tuple(row["input_row_id"] for row in converted),
        ledger,
    )


def _canonical_row(
    row: Mapping[str, object], request: CohortExportRequest
) -> dict[str, str]:
    _validate_source_row(row)
    data = {
        key: value
        for key, value in row.items()
        if not key.startswith("_") and key not in {"entity_id", "content_hash"}
    }
    direct_column = request.direct_iuphar_id_column
    if direct_column is not None:
        data["iuphar_target_id"] = _direct_identity(row, direct_column)
    taxon = str(data["taxonomy_id"])
    fields = project_target_fields(data, taxon)
    return {
        "input_row_id": "chembl.target:" + str(row["target_id"]),
        "target_kind": "protein",
        **{name: fields[name] or "" for name in _COLUMNS[2:]},
    }


def _validate_source_row(row: Mapping[str, object]) -> None:
    if not _REQUIRED.issubset(row) or _RESERVED.intersection(row):
        raise ValueError(
            "normalized target schema missing fields or reserved importer fields supplied"
        )
    if any(key in row for key in TARGET_CLASSIFICATION_FIELDS):
        raise ValueError("normalized V30 input cannot reuse classification outputs")
    if row["target_type"] != "SINGLE PROTEIN":
        raise ValueError("normalized cohort requires explicit SINGLE PROTEIN rows")
    if re.fullmatch(r"CHEMBL\d+", str(row["target_id"]), flags=re.ASCII) is None:
        raise ValueError("normalized cohort requires a valid ChEMBL target identity")
    if (
        type(row["taxonomy_id"]) is bool
        or re.fullmatch(r"[1-9]\d*", str(row["taxonomy_id"]), flags=re.ASCII) is None
    ):
        raise ValueError("normalized cohort requires confirmed canonical TaxID values")


def _direct_identity(row: Mapping[str, object], column: str) -> str | None:
    if column not in row:
        raise ValueError("declared direct IUPHAR identity column is absent")
    value = row[column]
    if value in (None, ""):
        return None
    if re.fullmatch(r"[1-9]\d*", str(value), flags=re.ASCII) is None:
        raise ValueError("direct IUPHAR identity must be explicit positive ASCII text")
    return str(value)
