"""Declarative field-mapping helpers for transformer implementations."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.transformations import safe_float, safe_int
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord

# Type aliases for common converters
INT: Callable[[object], int | None] = (
    safe_int  # object: raw field value from Bronze record
)
FLOAT: Callable[[object], float | None] = (
    safe_float  # object: raw field value from Bronze record
)
STR: Callable[[object], str] = str  # object: raw field value from Bronze record

def normalize_pmid(
    value: object,
) -> str | None:  # object: raw PMID value (int, str, or None)
    """Normalize one PubMed identifier via the publication value object."""
    from bioetl.domain.value_objects.publications import PubMedId

    normalized_input: str | int | None = None
    if (isinstance(value, int) and not isinstance(value, bool)) or isinstance(
        value, str
    ):
        normalized_input = value
    vo = PubMedId.from_raw(normalized_input)
    return str(vo) if vo else None

PMID: Callable[[object], str | None] = (
    normalize_pmid  # object: raw PMID value from Bronze record
)

@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Specification for one field mapping."""

    source: str
    target: str | None = None
    converter: Callable[[object], object] | None = (
        None  # object: generic field converter
    )
    required: bool = False
    default: object = (
        None  # object: heterogeneous default values depending on field type
    )

@dataclass(frozen=True, slots=True)
class FieldGroup:
    """Group of related field specifications with an optional target prefix."""

    name: str
    fields: tuple[FieldSpec, ...]
    prefix: str = ""

def map_field(
    record: BronzeRecord,
    spec: FieldSpec,
) -> tuple[str, object]:  # object: field value type varies (str | int | float | None)
    """Map one source field according to a field specification."""
    value = record.get(spec.source)
    target = spec.target or spec.source

    if value is None:
        if spec.required:
            raise ValueError(f"Required field '{spec.source}' is missing or None")
        if spec.default is not None:
            return target, spec.default
        return target, None

    if spec.converter is not None:
        value = spec.converter(value)

    return target, value

def map_fields(
    record: BronzeRecord,
    specs: Sequence[FieldSpec],
) -> JsonDict:  # Any: heterogeneous record values
    """Map multiple fields from one source record."""
    result: JsonDict = {}  # Any: heterogeneous record values

    for spec in specs:
        target, value = map_field(record, spec)
        result[target] = value

    return result

def map_field_group(
    record: BronzeRecord,
    group: FieldGroup,
) -> JsonDict:  # Any: heterogeneous record values
    """Map one field group and apply its optional target prefix."""
    mapped = map_fields(record, group.fields)

    if group.prefix:
        return {f"{group.prefix}{k}": v for k, v in mapped.items()}
    return mapped

def map_field_groups(
    record: BronzeRecord,
    groups: Sequence[FieldGroup],
) -> JsonDict:  # Any: heterogeneous record values
    """Map multiple field groups and merge the results."""
    result: JsonDict = {}  # Any: heterogeneous record values

    for group in groups:
        result.update(map_field_group(record, group))

    return result

# =============================================================================
# Convenience functions for common patterns
# =============================================================================

def simple_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create pass-through field specs from raw field names."""
    return tuple(FieldSpec(name) for name in field_names)

def int_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create field specs that normalize values with `INT`."""
    return tuple(FieldSpec(name, converter=INT) for name in field_names)

def float_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create field specs that normalize values with `FLOAT`."""
    return tuple(FieldSpec(name, converter=FLOAT) for name in field_names)

def standard_value_fields(
    *,
    relation_before_units: bool = False,
    include_standard_upper_value: bool = False,
    include_pchembl_value: bool = False,
    include_standard_flag: bool = False,
) -> tuple[FieldSpec, ...]:
    """Create shared ChEMBL standard value field specs in caller-owned order."""
    relation_unit_fields = (
        ("standard_relation", "standard_units")
        if relation_before_units
        else ("standard_units", "standard_relation")
    )
    float_field_names = ["standard_value"]
    if include_standard_upper_value:
        float_field_names.append("standard_upper_value")
    if include_pchembl_value:
        float_field_names.append("pchembl_value")

    fields = (
        *simple_fields("standard_type", *relation_unit_fields, "standard_text_value"),
        *float_fields(*float_field_names),
    )
    if include_standard_flag:
        return (*fields, *int_fields("standard_flag"))
    return fields

def pmid_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create field specs that normalize values with `PMID`."""
    return tuple(FieldSpec(name, converter=PMID) for name in field_names)

__all__ = [
    "FLOAT",
    "INT",
    "PMID",
    "STR",
    "FieldGroup",
    "FieldSpec",
    "float_fields",
    "int_fields",
    "map_field",
    "map_field_group",
    "map_field_groups",
    "map_fields",
    "normalize_pmid",
    "pmid_fields",
    "simple_fields",
    "standard_value_fields",
]
