"""Schema field extraction collaborators for preflight orchestration."""

from __future__ import annotations

from typing import Protocol

from bioetl.application.composite._preflight_types import FieldInfo, SchemaFields
from bioetl.domain.exceptions import BioETLError, DataQualityError
from bioetl.domain.ports import LoggerPort

__all__ = [
    "PreflightSchemaFieldExtractionHost",
    "extract_dtype_from_annotation",
    "extract_fields_from_annotations",
    "extract_fields_from_schema",
    "simplify_dtype",
]


class PreflightSchemaFieldExtractionHost(Protocol):
    _logger: LoggerPort


def simplify_dtype(dtype_str: str) -> str:
    """Simplify a dtype string for comparison."""
    normalized = dtype_str.strip()
    for prefix in ("pandas.core.arrays.integer.", "pandas.", "pandera."):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]

    simplifications = {
        "Int64Dtype()": "int",
        "Int64Dtype": "int",
        "Int64": "int",
        "int64": "int",
        "Float64": "float",
        "float64": "float",
        "object": "str",
        "string": "str",
        "String": "str",
        "boolean": "bool",
        "datetime64[ns]": "datetime",
    }
    return simplifications.get(normalized, normalized)


def extract_dtype_from_annotation(annotation: object) -> str:
    """Extract dtype string from a type annotation."""
    ann_str = str(annotation)
    if "Series[" in ann_str:
        inner = ann_str.split("Series[", 1)[1].rstrip("]")
        return simplify_dtype(inner)
    return simplify_dtype(ann_str)


def extract_fields_from_annotations(
    schema_class: type,
    source: str,
) -> SchemaFields:
    """Fallback: extract fields from class annotations."""
    fields: SchemaFields = {}

    for klass in schema_class.__mro__:
        if not hasattr(klass, "__annotations__"):
            continue
        for field_name, field_type in klass.__annotations__.items():
            if field_name.startswith("_") and field_name not in (
                "_source",
                "_dq_warn",
                "_dq_error",
            ):
                continue
            if field_name in fields:
                continue

            dtype_str = extract_dtype_from_annotation(field_type)
            fields[field_name] = FieldInfo(
                name=field_name,
                dtype=dtype_str,
                nullable=True,
                source=source,
            )

    return fields


def extract_fields_from_schema(
    host: PreflightSchemaFieldExtractionHost,
    schema_class: type,
    source: str,
) -> SchemaFields:
    """Extract field information from a Pandera schema class."""
    fields: SchemaFields = {}

    try:
        schema_instance = schema_class.to_schema()  # type: ignore[attr-defined]
        for col_name, col_info in schema_instance.columns.items():
            dtype_str = str(col_info.dtype) if col_info.dtype else "object"
            dtype_str = simplify_dtype(dtype_str)
            fields[col_name] = FieldInfo(
                name=col_name,
                dtype=dtype_str,
                nullable=col_info.nullable if col_info.nullable is not None else True,
                source=source,
            )
    except (ValueError, TypeError, RuntimeError, DataQualityError) as error:
        host._logger.warning(
            "Failed to extract fields from schema",
            schema=schema_class.__name__,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="schema_field_extraction_failed",
        )
        fields = extract_fields_from_annotations(schema_class, source)
    except BioETLError as error:
        host._logger.warning(
            "Failed to extract fields from schema",
            schema=schema_class.__name__,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="schema_field_extraction_failed",
        )
        fields = extract_fields_from_annotations(schema_class, source)

    return fields
