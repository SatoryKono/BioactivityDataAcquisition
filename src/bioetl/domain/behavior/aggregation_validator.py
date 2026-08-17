"""Aggregation validation service for MANY_TO_ONE operations."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from bioetl.domain.behavior.aggregation_validation_helpers import (
    build_group_key,
    collect_duplicate_groups,
)
from bioetl.domain.behavior.aggregation_validation_helpers import (
    column_names as _column_names,
)
from bioetl.domain.behavior.aggregation_validation_helpers import (
    explicit_field_names as _explicit_field_names,
)
from bioetl.domain.behavior.aggregation_validation_helpers import (
    field_name_from_descriptor as _field_name_from_descriptor,
)
from bioetl.domain.behavior.validation_helpers import (
    aggregation_fallback_fields,
    aggregation_field_names_from_list,
    aggregation_group_key,
    aggregation_source_fields,
)
from bioetl.domain.behavior.validation_result_envelopes import (
    build_validation_result,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import ValidationIssue, ValidationResult
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)

__all__ = [
    "AggregationConfig",
    "AggregationProvenance",
    "AggregationValidator",
    "_column_names",
    "_explicit_field_names",
    "_field_name_from_descriptor",
]

_SUPPORTED_AGGREGATIONS = frozenset(
    {"sum", "avg", "min", "max", "count", "first", "last", "concat", "list"}
)


@dataclass(frozen=True)
class AggregationConfig:
    """Canonical aggregation settings used by preflight validation."""

    group_by: list[str]
    aggregations: dict[str, str]
    source_field: str | None = None
    provenance_tracking: bool = True


@dataclass(frozen=True)
class AggregationProvenance:
    """Explainability metadata describing one aggregated output field."""

    field_name: str
    source_field: str
    aggregation_function: str
    source_count: int


class AggregationValidator:
    """Validate aggregation config and runtime uniqueness constraints."""

    _get_source_fields = staticmethod(aggregation_source_fields)
    _field_names_from_list = staticmethod(aggregation_field_names_from_list)
    _collect_fallback_fields = staticmethod(aggregation_fallback_fields)
    _build_group_key = staticmethod(aggregation_group_key)

    def validate_aggregation_config(
        self,
        config: AggregationConfig,
        source_schema: JsonDict,
        execution_context: JsonDict | None = None,
    ) -> ValidationResult:
        """Validate aggregation config against schema and governance rules."""
        issues: list[ValidationIssue] = []
        issues.extend(self._validate_group_by_fields(config, source_schema))
        issues.extend(self._validate_aggregation_functions(config))
        issues.extend(self._validate_source_field(config, source_schema))
        issues.extend(self._check_field_shadowing(config))
        result: ValidationResult = build_validation_result(
            issues=issues,
            validation_layer=ValidationLayer.DEEP_PREFLIGHT,
            execution_context=execution_context or {},
        )
        return result

    def _validate_group_by_fields(
        self,
        config: AggregationConfig,
        source_schema: JsonDict,
    ) -> list[ValidationIssue]:
        if not config.group_by:
            return [
                ValidationIssue(
                    code=IssueCode.CMP_PF_AGG_001,
                    severity=ValidationSeverity.BLOCKER,
                    layer=ValidationLayer.DEEP_PREFLIGHT,
                    message="Aggregation configuration missing group_by fields",
                    details={"config": dataclasses.asdict(config)},
                )
            ]

        source_fields = self._get_source_fields(source_schema)
        missing = [field for field in config.group_by if field not in source_fields]
        return [
            ValidationIssue(
                code=IssueCode.CMP_PF_AGG_002,
                severity=ValidationSeverity.BLOCKER,
                layer=ValidationLayer.DEEP_PREFLIGHT,
                message=f"Group_by field '{field}' not found in source schema",
                details={
                    "missing_field": field,
                    "available_fields": list(source_fields),
                },
            )
            for field in missing
        ]

    def _validate_aggregation_functions(
        self,
        config: AggregationConfig,
    ) -> list[ValidationIssue]:
        if not config.aggregations:
            return [
                ValidationIssue(
                    code=IssueCode.CMP_PF_AGG_003,
                    severity=ValidationSeverity.BLOCKER,
                    layer=ValidationLayer.DEEP_PREFLIGHT,
                    message="Aggregation configuration missing aggregations",
                    details={"config": dataclasses.asdict(config)},
                )
            ]

        unsupported = [
            (field, function)
            for field, function in config.aggregations.items()
            if function not in _SUPPORTED_AGGREGATIONS
        ]
        return [
            ValidationIssue(
                code=IssueCode.CMP_PF_AGG_004,
                severity=ValidationSeverity.BLOCKER,
                layer=ValidationLayer.DEEP_PREFLIGHT,
                message=(
                    f"Unsupported aggregation function '{function}' for field '{field}'"
                ),
                details={
                    "field": field,
                    "function": function,
                    "supported_functions": sorted(_SUPPORTED_AGGREGATIONS),
                },
            )
            for field, function in unsupported
        ]

    def _validate_source_field(
        self,
        config: AggregationConfig,
        source_schema: JsonDict,
    ) -> list[ValidationIssue]:
        if not config.source_field:
            return []
        source_fields = self._get_source_fields(source_schema)
        if config.source_field in source_fields:
            return []
        return [
            ValidationIssue(
                code=IssueCode.CMP_PF_AGG_005,
                severity=ValidationSeverity.BLOCKER,
                layer=ValidationLayer.DEEP_PREFLIGHT,
                message=f"Source field '{config.source_field}' not found in source schema",
                details={
                    "missing_field": config.source_field,
                    "available_fields": list(source_fields),
                },
            )
        ]

    @staticmethod
    def _check_field_shadowing(config: AggregationConfig) -> list[ValidationIssue]:
        shadowing_fields = [
            field for field in config.aggregations if field in config.group_by
        ]
        return [
            ValidationIssue(
                code=IssueCode.CMP_PF_AGG_006,
                severity=ValidationSeverity.WARNING,
                layer=ValidationLayer.DEEP_PREFLIGHT,
                message=f"Aggregation field '{field}' shadows group_by field",
                details={"field": field, "group_by_fields": config.group_by},
            )
            for field in shadowing_fields
        ]

    def validate_post_aggregation_uniqueness(
        self,
        aggregation_results: list[JsonDict],
        group_by_fields: list[str],
    ) -> ValidationResult:
        """Ensure aggregation output preserves the expected grouping grain."""
        duplicate_groups = self._collect_duplicate_groups(
            aggregation_results=aggregation_results,
            group_by_fields=group_by_fields,
        )
        issues = self._build_uniqueness_issues(
            duplicate_groups=duplicate_groups,
            group_by_fields=group_by_fields,
        )
        result: ValidationResult = build_validation_result(
            issues=issues,
            validation_layer=ValidationLayer.RUNTIME_GUARD,
            execution_context={"validation_type": "post_aggregation_uniqueness"},
        )
        return result

    def _collect_duplicate_groups(
        self,
        *,
        aggregation_results: list[JsonDict],
        group_by_fields: list[str],
    ) -> list[JsonDict]:
        return collect_duplicate_groups(
            aggregation_results=aggregation_results,
            group_by_fields=group_by_fields,
        )

    @staticmethod
    def _build_group_key(
        record: JsonDict, group_by_fields: list[str]
    ) -> tuple[tuple[str, str, str], ...]:
        return build_group_key(record, group_by_fields)

    def _build_uniqueness_issues(
        self,
        *,
        duplicate_groups: list[JsonDict],
        group_by_fields: list[str],
    ) -> list[ValidationIssue]:
        if not duplicate_groups:
            return []
        return [
            ValidationIssue(
                code=IssueCode.CMP_RT_GRAIN_001,
                severity=ValidationSeverity.BLOCKER,
                layer=ValidationLayer.RUNTIME_GUARD,
                message=(
                    "Post-aggregation uniqueness violation: "
                    f"{len(duplicate_groups)} duplicate groups found"
                ),
                details={
                    "duplicate_count": len(duplicate_groups),
                    "group_by_fields": group_by_fields,
                    "sample_duplicates": self._build_duplicate_samples(
                        duplicate_groups
                    ),
                },
            )
        ]

    @staticmethod
    def _build_duplicate_samples(duplicate_groups: list[JsonDict]) -> list[JsonDict]:
        return [
            {
                "index": duplicate["index"],
                "group_key": [list(component) for component in duplicate["group_key"]],
            }
            for duplicate in duplicate_groups[:5]
        ]

    def generate_aggregation_provenance(
        self,
        aggregation_config: AggregationConfig,
        source_records: list[JsonDict],
    ) -> list[AggregationProvenance]:
        """Build provenance facts for each configured aggregation field."""
        provenance: list[AggregationProvenance] = []
        for field, function in aggregation_config.aggregations.items():
            source_field = aggregation_config.source_field or field
            source_count = sum(1 for record in source_records if source_field in record)
            provenance.append(
                AggregationProvenance(
                    field_name=field,
                    source_field=source_field,
                    aggregation_function=function,
                    source_count=source_count,
                )
            )
        return provenance
