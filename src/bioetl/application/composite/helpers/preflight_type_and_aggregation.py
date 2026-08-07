"""Type-compatibility and aggregation helpers for preflight checks."""

from __future__ import annotations

from bioetl.application.composite._preflight_types import ValidationIssue
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.aggregation import AggregationFunction

__all__ = [
    "COMPATIBLE_TYPES",
    "ORDER_SENSITIVE_AGGREGATIONS",
    "check_type_compatibility",
    "dtype_in_group",
    "validate_aggregation_ordering",
]

COMPATIBLE_TYPES: tuple[frozenset[str], ...] = (
    frozenset({"str", "object", "String"}),
    frozenset({"int", "Int64", "int64", "Int64Dtype", "float", "Float64", "float64"}),
    frozenset({"bool", "boolean"}),
    frozenset({"date", "datetime", "datetime64"}),
)

ORDER_SENSITIVE_AGGREGATIONS = frozenset(
    {
        AggregationFunction.COLLECT_LIST,
        AggregationFunction.COLLECT_SET,
        AggregationFunction.FIRST,
        AggregationFunction.CONCAT_STR,
    }
)


def dtype_in_group(dtype: str, group: frozenset[str]) -> bool:
    """Check if a dtype belongs to a compatibility group."""
    dtype_lower = dtype.lower()
    return dtype_lower in {entry.lower() for entry in group}


def check_type_compatibility(
    field_name: str, field_dtypes: dict[str, str]
) -> ValidationIssue | None:
    """Check if field types are compatible across sources."""
    dtypes = list(field_dtypes.values())
    sources = list(field_dtypes.keys())

    for compat_group in COMPATIBLE_TYPES:
        if all(dtype_in_group(dtype, compat_group) for dtype in dtypes):
            return None

    return ValidationIssue(
        field=field_name,
        source=",".join(sources),
        issue_type="type_mismatch",
        message=f"Incompatible types for '{field_name}': "
        f"{dict(zip(sources, dtypes, strict=False))}",
        severity="error",
    )


def validate_aggregation_ordering(
    config: CompositeConfig,
) -> list[ValidationIssue]:
    """Return preflight issues for many-to-one aggregation without order_by."""
    issues: list[ValidationIssue] = []
    for enricher in config.enrichers:
        aggregation = enricher.aggregation
        if not enricher.is_many_to_one or aggregation is None:
            continue
        order_sensitive_fields = [
            field.effective_output_field
            for field in aggregation.fields
            if field.agg_function in ORDER_SENSITIVE_AGGREGATIONS
        ]
        if not order_sensitive_fields or aggregation.order_by:
            continue
        issues.append(
            ValidationIssue(
                field="aggregation.order_by",
                source=enricher.pipeline,
                issue_type="missing_deterministic_order",
                message=(
                    f"Enricher '{enricher.pipeline}' many-to-one aggregation "
                    "must declare aggregation.order_by for deterministic "
                    f"fields: {sorted(order_sensitive_fields)}"
                ),
                severity="error",
            )
        )
    return issues
