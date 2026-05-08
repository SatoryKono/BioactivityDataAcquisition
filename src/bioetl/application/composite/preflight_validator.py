"""Preflight validator for composite pipeline configurations.

Validates field_priorities configuration against source schemas BEFORE pipeline
execution starts. This ensures schema drift and configuration errors are caught
early, not during merge phase.

See ADR-026 for composite pipeline architectural decisions.
"""

from __future__ import annotations

from bioetl.application.composite._preflight_orchestration import (
    PreflightSchemaOrchestrationMixin,
)
from bioetl.application.composite._preflight_reporting import (
    PreflightValidationReportingMixin,
)
from bioetl.application.composite._preflight_types import (
    FieldInfo,
    PreflightValidationError,
    PreflightValidationResult,
    SchemaFields,
    ValidationIssue,
)
from bioetl.domain.composite.aggregation import AggregationFunction
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.ports import LoggerPort

__all__ = [
    "CompositePreflightValidationService",
    "FieldInfo",
    "PreflightValidationError",
    "PreflightValidationResult",
    "SchemaFields",
    "ValidationIssue",
]


class CompositePreflightValidationService(
    PreflightValidationReportingMixin,
    PreflightSchemaOrchestrationMixin,
):
    """Validates composite pipeline configuration before execution."""

    _COMPATIBLE_TYPES: tuple[frozenset[str], ...] = (
        frozenset({"str", "object", "String"}),
        frozenset(
            {"int", "Int64", "int64", "Int64Dtype", "float", "Float64", "float64"}
        ),
        frozenset({"bool", "boolean"}),
        frozenset({"date", "datetime", "datetime64"}),
    )
    _ORDER_SENSITIVE_AGGREGATIONS = frozenset(
        {
            AggregationFunction.COLLECT_LIST,
            AggregationFunction.COLLECT_SET,
            AggregationFunction.FIRST,
            AggregationFunction.CONCAT_STR,
        }
    )

    def __init__(self, logger: LoggerPort) -> None:
        self._logger = logger

    def _add_pipeline_source_tokens(
        self,
        sources: set[str],
        pipeline_name: str,
        *,
        include_seed_alias: bool = False,
    ) -> None:
        """Register accepted source token variants for one pipeline."""
        identity = self._parse_pipeline_identity(pipeline_name)
        if identity is None:
            return
        provider, entity = identity
        sources.add(provider)
        sources.add(f"{provider}.{entity}")
        sources.add(f"{provider}_{entity}")
        if include_seed_alias:
            sources.add("seed")

    def _get_valid_sources(self, config: CompositeConfig) -> frozenset[str]:
        """Extract valid source names from composite config."""
        sources: set[str] = set()
        self._add_pipeline_source_tokens(
            sources,
            config.seed.pipeline,
            include_seed_alias=True,
        )
        for dependency in config.dependencies:
            self._add_pipeline_source_tokens(sources, dependency.pipeline)
        for enricher in config.enrichers:
            self._add_pipeline_source_tokens(sources, enricher.pipeline)
        return frozenset(sources)

    def _validate_field_priority(
        self,
        field_name: str,
        priorities: tuple[str, ...],
        valid_sources: frozenset[str],
        source_fields: dict[str, SchemaFields],
    ) -> tuple[list[ValidationIssue], str | None]:
        """Validate a single field_priority entry."""
        issues: list[ValidationIssue] = []
        resolved_source: str | None = None
        field_dtypes: dict[str, str] = {}

        for source in priorities:
            source_lower = source.lower()

            if source_lower not in valid_sources:
                issues.append(
                    ValidationIssue(
                        field=field_name,
                        source=source,
                        issue_type="unknown_source",
                        message=f"Source '{source}' not found in composite config "
                        f"(valid: {sorted(valid_sources)})",
                    )
                )
                continue

            schema_fields = source_fields.get(source_lower, {})
            if field_name not in schema_fields:
                issues.append(
                    ValidationIssue(
                        field=field_name,
                        source=source,
                        issue_type="missing_field",
                        message=f"Field '{field_name}' not found in {source} schema",
                        severity="warning",
                    )
                )
                continue

            field_info = schema_fields[field_name]
            field_dtypes[source] = field_info.dtype
            if resolved_source is None:
                resolved_source = source

        if not field_dtypes:
            issues.append(
                ValidationIssue(
                    field=field_name,
                    source=",".join(priorities),
                    issue_type="missing_field",
                    message=f"Field '{field_name}' not found in ANY source schema "
                    f"(checked: {list(priorities)})",
                    severity="error",
                )
            )

        if len(field_dtypes) > 1:
            type_issue = self._check_type_compatibility(field_name, field_dtypes)
            if type_issue:
                issues.append(type_issue)

        return issues, resolved_source

    def _check_type_compatibility(
        self, field_name: str, field_dtypes: dict[str, str]
    ) -> ValidationIssue | None:
        """Check if field types are compatible across sources."""
        dtypes = list(field_dtypes.values())
        sources = list(field_dtypes.keys())

        for compat_group in self._COMPATIBLE_TYPES:
            if all(self._dtype_in_group(dtype, compat_group) for dtype in dtypes):
                return None

        return ValidationIssue(
            field=field_name,
            source=",".join(sources),
            issue_type="type_mismatch",
            message=f"Incompatible types for '{field_name}': "
            f"{dict(zip(sources, dtypes, strict=False))}",
            severity="error",
        )

    def _dtype_in_group(self, dtype: str, group: frozenset[str]) -> bool:
        """Check if a dtype belongs to a compatibility group."""
        dtype_lower = dtype.lower()
        return dtype_lower in {entry.lower() for entry in group}

    def _validate_aggregation_ordering(
        self,
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
                if field.agg_function in self._ORDER_SENSITIVE_AGGREGATIONS
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

    def validate(
        self,
        config: CompositeConfig,
        *,
        fail_on_error: bool = True,
    ) -> PreflightValidationResult:
        """Validate composite configuration field_priorities.

        Args:
            config: Composite pipeline configuration containing field_priorities
                and enricher definitions to validate.
            fail_on_error: If True, raise PreflightValidationError when any
                error-severity issue is found; defaults to True.

        Returns:
            PreflightValidationResult with validation status, issues, and
            resolved field source mappings.
        """
        issues: list[ValidationIssue] = []
        resolved_fields: dict[str, str] = {}

        valid_sources = self._get_valid_sources(config)
        source_fields = self._load_source_fields(config)
        self._log_schema_loading_summary(source_fields)

        field_priorities = config.merge.field_priorities
        for field_name, priorities in field_priorities.items():
            field_issues, resolved_source = self._validate_field_priority(
                field_name=field_name,
                priorities=priorities,
                valid_sources=valid_sources,
                source_fields=source_fields,
            )
            issues.extend(field_issues)
            if resolved_source:
                resolved_fields[field_name] = resolved_source

        issues.extend(self._validate_aggregation_ordering(config))

        is_valid = all(issue.severity != "error" for issue in issues)
        result = PreflightValidationResult(
            is_valid=is_valid,
            issues=issues,
            resolved_fields=resolved_fields,
        )
        self._log_validation_result(
            is_valid=is_valid,
            config=config,
            result=result,
            field_priorities_count=len(field_priorities),
        )

        if fail_on_error and not is_valid:
            raise PreflightValidationError(result)
        return result
