"""Pure canonical-row projection for a frozen normalized target cohort."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence

import pyarrow as pa

from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_TARGET_SCHEMA
from bioetl.infrastructure.storage.target_classification_guard import (
    TARGET_CLASSIFICATION_FIELDS,
)
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

_TRUE_TOKENS = frozenset({"true", "1", "yes"})
_FALSE_TOKENS = frozenset({"false", "0", "no"})
_SCHEMA_FIELDS = {field.name: field.type for field in CHEMBL_TARGET_SCHEMA}


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


def _restore_normalized_silver_types(
    row: Mapping[str, object],
) -> dict[str, object]:
    """Rebuild Silver scalar types so CSV transport matches Arrow/runtime rows."""
    restored: dict[str, object] = {}
    for key, value in row.items():
        field_type = _SCHEMA_FIELDS.get(key)
        if field_type is None:
            restored[key] = value
            continue
        if value == "" or value is None:
            restored[key] = None
            continue
        if pa.types.is_boolean(field_type):
            restored[key] = _as_bool(value, key)
        elif pa.types.is_integer(field_type):
            restored[key] = _as_int(value, key)
        elif pa.types.is_floating(field_type):
            restored[key] = _as_float(value, key)
        else:
            restored[key] = value
    return restored


def _as_bool(value: object, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        token = value.strip().casefold()
        if token in _TRUE_TOKENS:
            return True
        if token in _FALSE_TOKENS:
            return False
    raise ValueError(f"normalized Silver field {field} must be a boolean")


def _as_int(value: object, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"normalized Silver field {field} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(f"normalized Silver field {field} must be an integer")
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"-?[1-9]\d*|0", text, flags=re.ASCII) is not None:
            return int(text)
    raise ValueError(f"normalized Silver field {field} must be an integer")


def _as_float(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"normalized Silver field {field} must be a float")
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"normalized Silver field {field} must be a float")
        return number
    if isinstance(value, str):
        text = value.strip()
        try:
            number = float(text)
        except ValueError as error:
            raise ValueError(
                f"normalized Silver field {field} must be a float"
            ) from error
        if not math.isfinite(number):
            raise ValueError(f"normalized Silver field {field} must be a float")
        return number
    raise ValueError(f"normalized Silver field {field} must be a float")


def _canonical_row(
    row: Mapping[str, object], request: CohortExportRequest
) -> dict[str, str]:
    typed = _restore_normalized_silver_types(row)
    _validate_source_row(typed)
    data = {
        key: value
        for key, value in typed.items()
        if not key.startswith("_") and key not in {"entity_id", "content_hash"}
    }
    direct_column = request.direct_iuphar_id_column
    if direct_column is not None:
        data["iuphar_target_id"] = _direct_identity(typed, direct_column)
    taxon = str(data["taxonomy_id"])
    fields = project_target_fields(data, taxon)
    return {
        "input_row_id": "chembl.target:" + str(typed["target_id"]),
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
