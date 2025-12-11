"""Adapter for converting domain FieldSpec to Pandera fields.

This module bridges the domain layer (technology-agnostic field specifications)
with the infrastructure layer (Pandera validation framework).

The adapter transforms FieldSpec instances into Pandera Field objects,
preserving all constraints and validation rules.
"""

from __future__ import annotations

import re
from typing import Any

import pandera.pandas as pa

from bioetl.domain.schemas.field_specs import FieldSpec

__all__ = [
    "field_spec_to_pandera_field",
    "field_specs_to_schema_fields",
    "get_pandera_dtype",
]


# Mapping from domain data types to Pandera/pandas types
_DTYPE_MAP: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": object,  # Lists stored as object dtype
    "object": object,  # JSON-like structures stored as object
    "datetime": str,  # ISO format string representation
}


def get_pandera_dtype(data_type: str) -> Any:
    """Map domain data type to Pandera-compatible dtype.

    Parameters
    ----------
    data_type
        Domain data type string.

    Returns
    -------
    Any
        Pandera/pandas dtype.

    Raises
    ------
    ValueError
        If data type is not recognized.
    """
    if data_type not in _DTYPE_MAP:
        msg = f"Unknown data type: {data_type}"
        raise ValueError(msg)
    return _DTYPE_MAP[data_type]


def field_spec_to_pandera_field(spec: FieldSpec) -> pa.Field:
    """Convert a FieldSpec to a Pandera Field.

    Parameters
    ----------
    spec
        Domain field specification.

    Returns
    -------
    pa.Field
        Configured Pandera Field instance.

    Examples
    --------
    >>> spec = FieldSpec(
    ...     "activity_id", "integer", nullable=False, constraints={"ge": 1}
    ... )
    >>> field = field_spec_to_pandera_field(spec)
    """
    kwargs: dict[str, Any] = {
        "nullable": spec.nullable,
        "description": spec.description,
    }

    # Add pattern constraint if specified
    if spec.pattern:
        # Compile to validate pattern, then use pattern string
        re.compile(spec.pattern)  # Raises re.error if invalid
        kwargs["str_matches"] = spec.pattern

    # Add numeric range constraints
    for constraint in ("ge", "gt", "le", "lt"):
        if constraint in spec.constraints:
            kwargs[constraint] = spec.constraints[constraint]

    # Add enumeration constraint
    if "isin" in spec.constraints:
        kwargs["isin"] = spec.constraints["isin"]

    return pa.Field(**kwargs)


def field_specs_to_schema_fields(
    specs: tuple[FieldSpec, ...] | list[FieldSpec],
) -> dict[str, tuple[Any, pa.Field]]:
    """Convert multiple FieldSpecs to Pandera schema field definitions.

    This function produces a dictionary suitable for dynamically creating
    a Pandera DataFrameModel or DataFrameSchema.

    Parameters
    ----------
    specs
        Sequence of domain field specifications.

    Returns
    -------
    dict[str, tuple[Any, pa.Field]]
        Dictionary mapping field names to (dtype, Field) tuples.

    Examples
    --------
    >>> specs = [
    ...     FieldSpec("id", "integer", nullable=False),
    ...     FieldSpec("name", "string", nullable=True),
    ... ]
    >>> fields = field_specs_to_schema_fields(specs)
    >>> # fields = {"id": (int, Field(...)), "name": (str, Field(...))}
    """
    result: dict[str, tuple[Any, pa.Field]] = {}

    for spec in specs:
        dtype = get_pandera_dtype(spec.data_type)
        field = field_spec_to_pandera_field(spec)
        result[spec.name] = (dtype, field)

    return result


def create_schema_from_field_specs(
    name: str,
    business_specs: tuple[FieldSpec, ...] | list[FieldSpec],
    *,
    include_generated: bool = True,
) -> type[pa.DataFrameModel]:
    """Dynamically create a Pandera DataFrameModel from field specifications.

    This is an alternative to static class definitions when schemas need
    to be generated at runtime from domain specifications.

    Parameters
    ----------
    name
        Name for the generated schema class.
    business_specs
        Business field specifications.
    include_generated
        Whether to include standard generated columns.

    Returns
    -------
    type[pa.DataFrameModel]
        Dynamically created Pandera schema class.

    Examples
    --------
    >>> from bioetl.domain.schemas.field_specs import ACTIVITY_FIELD_SPECS
    >>> ActivitySchema = create_schema_from_field_specs(
    ...     "ActivitySchema", ACTIVITY_FIELD_SPECS
    ... )
    """
    from bioetl.domain.schemas.field_specs import GENERATED_FIELD_SPECS
    from bioetl.infrastructure.validation.schemas.pandera_base import (
        BaseGeneratedColumnsModel,
    )

    # Build annotations and field defaults
    annotations: dict[str, Any] = {}
    namespace: dict[str, Any] = {}

    # Add business fields
    for spec in business_specs:
        dtype = get_pandera_dtype(spec.data_type)
        field = field_spec_to_pandera_field(spec)
        annotations[spec.name] = f"Series[{dtype.__name__}]"
        namespace[spec.name] = field

    # Determine base class
    if include_generated:
        base_classes: tuple[type, ...] = (BaseGeneratedColumnsModel,)
        # Add generated field annotations (they're inherited but need type hints)
        for spec in GENERATED_FIELD_SPECS:
            dtype = get_pandera_dtype(spec.data_type)
            annotations[spec.name] = f"Series[{dtype.__name__}]"
    else:
        base_classes = (pa.DataFrameModel,)

    namespace["__annotations__"] = annotations

    # Create and return the class
    schema_class = type(name, base_classes, namespace)
    return schema_class  # type: ignore[return-value]
