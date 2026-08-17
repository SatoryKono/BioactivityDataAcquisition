"""Aggregation validation service for MANY_TO_ONE operations."""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass

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

    def _get_source_fields(self, source_schema: JsonDict) -> set[str]:
        properties = source_schema.get("properties")
        if isinstance(properties, dict):
            return set(properties.keys())
        fields_node = source_schema.get("fields")
        if isinstance(fields_node, list):
            return self._field_names_from_list(fields_node)
        return self._collect_fallback_fields(source_schema)

    @staticmethod
    def _field_names_from_list(fields_node: list[object]) -> set[str]:
        """Extract field names from string entries or dict descriptors."""
        names = (_field_name_from_descriptor(entry) for entry in fields_node)
        return {name for name in names if name is not None}

    @staticmethod
    def _collect_fallback_fields(source_schema: JsonDict) -> set[str]:
        """Collect field names from explicit schema shapes only."""
        fields = _column_names(source_schema.get("columns"))
        fields.update(_explicit_field_names(source_schema.get("field_names")))
        return fields

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
        # Type-tagged keys: (presence, type_name, canonical_value)
        seen_groups: set[tuple[tuple[str, str, str], ...]] = set()
        duplicates: list[JsonDict] = []
        for index, record in enumerate(aggregation_results):
            group_key = self._build_group_key(record, group_by_fields)
            if group_key in seen_groups:
                duplicates.append(
                    {
                        "index": index,
                        "group_key": group_key,
                        "record": record,
                    }
                )
            else:
                seen_groups.add(group_key)
        return duplicates

    @staticmethod
    def _build_group_key(
        record: JsonDict, group_by_fields: list[str]
    ) -> tuple[tuple[str, str, str], ...]:
        """Build a type-preserving group key.

        Each component is ``(presence, type_name, canonical)`` so that
        integer ``1`` and string ``\"1\"`` do not collide, and a missing field
        is distinct from the literal string ``\"MISSING\"``.
        """
        components: list[tuple[str, str, str]] = []
        for field in group_by_fields:
            if field not in record:
                components.append(("absent", "", ""))
                continue
            value = record[field]
            type_name = type(value).__name__
            if value is None:
                components.append(("present", "NoneType", "null"))
            else:
                components.append(
                    (
                        "present",
                        type_name,
                        json.dumps(
                            value,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ),
                    )
                )
        return tuple(components)

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


def _field_name_from_descriptor(entry: object) -> str | None:
    """Return a field name from a string or mapping descriptor."""
    if isinstance(entry, str):
        return entry
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    return name if isinstance(name, str) and name else None


def _column_name(entry: object) -> str | None:
    """Return names only from supported string or mapping descriptors."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return _field_name_from_descriptor(entry)
    return None


def _column_names(columns: object) -> set[str]:
    """Return names from the fallback ``columns`` schema shape."""
    if not isinstance(columns, list):
        return set()
    names = (_column_name(entry) for entry in columns)
    return {name for name in names if name is not None}


def _explicit_field_names(names: object) -> set[str]:
    """Return valid strings from the fallback ``field_names`` shape."""
    if not isinstance(names, list):
        return set()
    return {item for item in names if isinstance(item, str)}
