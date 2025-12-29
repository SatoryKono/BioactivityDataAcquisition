"""Declarative field mapping specifications.

Provides a DSL for declaring field transformations, replacing repetitive
_map_* methods with config-driven approach.

Example usage:
    >>> from bioetl.application.core.field_specs import (
    ...     FieldSpec, FieldGroup, map_fields, INT, FLOAT
    ... )
    >>> specs = (
    ...     FieldSpec("activity_id", converter=str),
    ...     FieldSpec("value", converter=FLOAT),
    ...     FieldSpec("type"),  # No conversion
    ... )
    >>> record = {"activity_id": 123, "value": "5.5", "type": "IC50"}
    >>> map_fields(record, specs)
    {'activity_id': '123', 'value': 5.5, 'type': 'IC50'}
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.domain.transformations import safe_float, safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Type aliases for common converters
INT: Callable[[Any], int | None] = safe_int
FLOAT: Callable[[Any], float | None] = safe_float
STR: Callable[[Any], str] = str


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Specification for a single field mapping.

    Attributes:
        source: Source field name in the record.
        target: Target field name in output. Defaults to source if None.
        converter: Optional type converter function. Applied if value is not None.
        required: If True, raise ValueError when field is missing or None.
        default: Default value when field is missing (only used if not required).

    Example:
        >>> spec = FieldSpec("molecule_id", target="molecule_chembl_id", converter=str)
        >>> spec = FieldSpec("value", converter=FLOAT, required=True)
        >>> spec = FieldSpec("description", default="N/A")
    """

    source: str
    target: str | None = None
    converter: Callable[[Any], Any] | None = None
    required: bool = False
    default: Any = None


@dataclass(frozen=True, slots=True)
class FieldGroup:
    """Group of related field specifications.

    Useful for organizing fields by category (identifiers, values, metadata).

    Attributes:
        name: Descriptive name for the group.
        fields: Tuple of field specifications.
        prefix: Optional prefix added to all target field names.

    Example:
        >>> group = FieldGroup(
        ...     name="activity_values",
        ...     fields=(
        ...         FieldSpec("value", converter=FLOAT),
        ...         FieldSpec("units"),
        ...     ),
        ... )
    """

    name: str
    fields: tuple[FieldSpec, ...]
    prefix: str = ""


def map_field(record: BronzeRecord, spec: FieldSpec) -> tuple[str, Any]:
    """Map a single field from record according to specification.

    Args:
        record: Source record dictionary.
        spec: Field specification.

    Returns:
        Tuple of (target_field_name, value).

    Raises:
        ValueError: If field is required but missing or None.
    """
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
) -> dict[str, Any]:
    """Map multiple fields from record according to specifications.

    Args:
        record: Source record dictionary.
        specs: Sequence of field specifications.

    Returns:
        Dictionary with mapped fields.

    Raises:
        ValueError: If any required field is missing.

    Example:
        >>> specs = (
        ...     FieldSpec("activity_id", converter=str, required=True),
        ...     FieldSpec("value", converter=FLOAT),
        ...     FieldSpec("type"),
        ... )
        >>> map_fields({"activity_id": 123, "value": "5.5", "type": "IC50"}, specs)
        {'activity_id': '123', 'value': 5.5, 'type': 'IC50'}
    """
    result: dict[str, Any] = {}

    for spec in specs:
        target, value = map_field(record, spec)
        result[target] = value

    return result


def map_field_group(
    record: BronzeRecord,
    group: FieldGroup,
) -> dict[str, Any]:
    """Map a group of fields with optional prefix.

    Args:
        record: Source record dictionary.
        group: Field group specification.

    Returns:
        Dictionary with mapped fields, optionally prefixed.

    Example:
        >>> group = FieldGroup(
        ...     name="ligand_efficiency",
        ...     prefix="le_",
        ...     fields=(
        ...         FieldSpec("bei", converter=FLOAT),
        ...         FieldSpec("le", converter=FLOAT),
        ...     ),
        ... )
        >>> map_field_group({"bei": "1.5", "le": "0.3"}, group)
        {'le_bei': 1.5, 'le_le': 0.3}
    """
    mapped = map_fields(record, group.fields)

    if group.prefix:
        return {f"{group.prefix}{k}": v for k, v in mapped.items()}
    return mapped


def map_field_groups(
    record: BronzeRecord,
    groups: Sequence[FieldGroup],
) -> dict[str, Any]:
    """Map multiple field groups, merging results.

    Args:
        record: Source record dictionary.
        groups: Sequence of field groups.

    Returns:
        Merged dictionary with all mapped fields.
    """
    result: dict[str, Any] = {}

    for group in groups:
        result.update(map_field_group(record, group))

    return result


# =============================================================================
# Convenience functions for common patterns
# =============================================================================


def simple_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create simple field specs (no conversion) from field names.

    Args:
        *field_names: Variable number of field names.

    Returns:
        Tuple of FieldSpec objects with no converters.

    Example:
        >>> specs = simple_fields("type", "units", "relation")
        >>> len(specs)
        3
    """
    return tuple(FieldSpec(name) for name in field_names)


def int_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create field specs with safe_int converter.

    Args:
        *field_names: Variable number of field names.

    Returns:
        Tuple of FieldSpec objects with INT converter.

    Example:
        >>> specs = int_fields("record_id", "src_id", "max_phase")
    """
    return tuple(FieldSpec(name, converter=INT) for name in field_names)


def float_fields(*field_names: str) -> tuple[FieldSpec, ...]:
    """Create field specs with safe_float converter.

    Args:
        *field_names: Variable number of field names.

    Returns:
        Tuple of FieldSpec objects with FLOAT converter.

    Example:
        >>> specs = float_fields("value", "standard_value", "pchembl_value")
    """
    return tuple(FieldSpec(name, converter=FLOAT) for name in field_names)


__all__ = [
    "FLOAT",
    "INT",
    "STR",
    "FieldGroup",
    "FieldSpec",
    "float_fields",
    "int_fields",
    "map_field",
    "map_field_group",
    "map_field_groups",
    "map_fields",
    "simple_fields",
]
