"""Composite validation layer service with clear separation of checks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from bioetl.domain.services.aggregation_validator import (
    AggregationConfig,
    AggregationValidator,
)
from bioetl.domain.services.cross_validation_validator import (
    CrossValidationConfig,
    CrossValidationValidator,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import (
    CompositeValidationReport,
    ValidationIssue,
    ValidationResult,
)
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


@dataclass(frozen=True)
class CompositeValidationConfig:
    pipeline_name: str
    composite_config: JsonDict
    execution_context: JsonDict | None = None
    strict_mode: bool = True


class CompositeValidationService:
    """Service for structural and deep-preflight composite validation."""

    def __init__(self) -> None:
        self._aggregation_validator = AggregationValidator()
        self._cross_validation_validator = CrossValidationValidator()

    def validate_composite(
        self,
        config: CompositeValidationConfig,
    ) -> CompositeValidationReport:
        structural_result = self._run_structural_validation(config)
        deep_preflight_result = self._run_deep_preflight_validation(config)
        return CompositeValidationReport(
            structural_result=structural_result,
            deep_preflight_result=deep_preflight_result,
            runtime_guard_result=None,
        )

    def _run_structural_validation(
        self,
        config: CompositeValidationConfig,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        if not isinstance(config.composite_config, dict):
            issues.append(
                self._create_issue(
                    IssueCode.CMP_STR_SCHEMA_001,
                    ValidationSeverity.BLOCKER,
                    "Composite config must be a dictionary",
                    {"actual_type": type(config.composite_config).__name__},
                )
            )
        for required_field in ("sources", "merge_strategy", "output_schema"):
            if required_field in config.composite_config:
                continue
            issues.append(
                self._create_issue(
                    IssueCode.CMP_STR_CONFIG_002,
                    ValidationSeverity.BLOCKER,
                    f"Missing required field: {required_field}",
                    {"missing_field": required_field},
                )
            )
        return ValidationResult(
            issues=issues,
            validation_layer=ValidationLayer.STRUCTURAL,
            execution_context={"pipeline_name": config.pipeline_name},
        )

    def _run_deep_preflight_validation(
        self,
        config: CompositeValidationConfig,
    ) -> ValidationResult:
        issues = self._deep_preflight_issues(config.composite_config)
        return ValidationResult(
            issues=issues,
            validation_layer=ValidationLayer.DEEP_PREFLIGHT,
            execution_context={"pipeline_name": config.pipeline_name},
        )

    def _deep_preflight_issues(self, composite_config: JsonDict) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        aggregation = composite_config.get("aggregation")
        if aggregation is not None:
            issues.extend(
                self._validate_aggregation_config(
                    aggregation,
                    composite_config.get("output_schema", {}),
                )
            )
        if "cross_validation" in composite_config:
            cross_validation_config = composite_config["cross_validation"]
            source_names = composite_config.get("sources", [])
            cross_validation_issues = self._validate_cross_validation_config(
                cross_validation_config, source_names
            )
            issues.extend(cross_validation_issues.issues)
        self._append_config_issue_if_invalid(
            issues=issues,
            composite_config=composite_config,
            config_key="field_priorities",
            validator=self._is_valid_field_priorities,
            code=IssueCode.CMP_PF_FIELD_001,
            severity=ValidationSeverity.WARNING,
            message="Conflicting or invalid field priorities detected",
            details_key="priorities",
        )
        self._append_config_issue_if_invalid(
            issues=issues,
            composite_config=composite_config,
            config_key="lineage",
            validator=self._is_valid_lineage_config,
            code=IssueCode.CMP_PF_LIN_001,
            severity=ValidationSeverity.BLOCKER,
            message="Insufficient lineage tracking configuration",
            details_key="config",
        )
        return issues

    def _append_config_issue_if_invalid(
        self,
        *,
        issues: list[ValidationIssue],
        composite_config: JsonDict,
        config_key: str,
        validator: Callable[[JsonDict], bool],
        code: IssueCode,
        severity: ValidationSeverity,
        message: str,
        details_key: str,
    ) -> None:
        section_value = composite_config.get(config_key)
        if section_value is None:
            return
        if isinstance(section_value, dict) and validator(section_value):
            return
        issues.append(
            self._create_issue(
                code=code,
                severity=severity,
                message=message,
                details={details_key: section_value},
            )
        )

    def _create_issue(
        self,
        code: IssueCode,
        severity: ValidationSeverity,
        message: str,
        details: JsonDict | None = None,
        location: str | None = None,
    ) -> ValidationIssue:
        return ValidationIssue(
            code=code,
            severity=severity,
            layer=self._get_layer_for_code(code),
            message=message,
            details=details or {},
            location=location,
        )

    @staticmethod
    def _get_layer_for_code(code: IssueCode) -> ValidationLayer:
        if code.value.startswith("CMP-STR-"):
            return ValidationLayer.STRUCTURAL
        if code.value.startswith("CMP-PF-"):
            return ValidationLayer.DEEP_PREFLIGHT
        return ValidationLayer.RUNTIME_GUARD

    def _validate_aggregation_config(
        self,
        config: JsonDict | object,
        source_schema: JsonDict,
    ) -> ValidationResult:
        """Validate cross-validation configuration using CrossValidationValidator."""
        if not isinstance(config, dict):
            return [
                self._create_issue(
                    IssueCode.CMP_PF_AGG_001,
                    ValidationSeverity.BLOCKER,
                    "Aggregation configuration must be a dictionary",
                    {"actual_type": type(config).__name__},
                )
            ]
        try:
            aggregation_config = self._convert_to_aggregation_config(config)
        except (KeyError, ValueError) as exc:
            return [
                self._create_issue(
                    IssueCode.CMP_PF_AGG_001,
                    ValidationSeverity.BLOCKER,
                    f"Invalid aggregation config format: {exc!s}",
                    {"config": config},
                )
            ]
        validation_result = self._aggregation_validator.validate_aggregation_config(
            aggregation_config,
            source_schema,
        )
        return validation_result.issues

    @staticmethod
    def _convert_to_aggregation_config(config: JsonDict) -> AggregationConfig:
        return AggregationConfig(
            group_by=config.get("group_by", []),
            aggregations=config.get("aggregations", {}),
            source_field=config.get("source_field"),
            provenance_tracking=config.get("provenance_tracking", True),
        )

    def _validate_cross_validation_config(
        self, config: JsonDict, source_names: list[str]
    ) -> list[ValidationIssue]:
        if not isinstance(config, dict):
            return ValidationResult(
                issues=[
                    self._create_issue(
                        IssueCode.CMP_PF_CV_002,
                        ValidationSeverity.BLOCKER,
                        "Cross-validation configuration must be a dictionary",
                        {"actual_type": type(config).__name__},
                    )
                ],
                validation_layer=ValidationLayer.DEEP_PREFLIGHT,
                execution_context={},
            )
        rules = config.get("rules")
        if not isinstance(rules, dict) or not rules:
            return ValidationResult(
                issues=[
                    self._create_issue(
                        IssueCode.CMP_PF_CV_008,
                        ValidationSeverity.BLOCKER,
                        "Cross-validation rules cannot be empty",
                        {"rules": rules if isinstance(rules, dict) else {}},
                    )
                ],
                validation_layer=ValidationLayer.DEEP_PREFLIGHT,
                execution_context={},
            )
        try:
            cross_val_config = self._convert_to_cross_validation_config(config)
        except (KeyError, ValueError) as exc:
            return ValidationResult(
                issues=[
                    self._create_issue(
                        IssueCode.CMP_PF_CV_003,
                        ValidationSeverity.BLOCKER,
                        f"Invalid cross-validation config format: {exc!s}",
                        {"config": config},
                    )
                ],
                validation_layer=ValidationLayer.DEEP_PREFLIGHT,
                execution_context={},
            )
        validation_result = self._cross_validation_validator.validate_cross_validation_config(
            cross_val_config, source_names
        )
        return validation_result

    @staticmethod
    def _convert_to_cross_validation_config(config: JsonDict) -> CrossValidationConfig:
        return CrossValidationConfig(
            pairs=config.get("pairs", []),
            rules=config.get("rules", {}),
            strict_mode=config.get("strict_mode", True),
            coverage_threshold=config.get("coverage_threshold"),
            consistency_threshold=config.get("consistency_threshold"),
        )

    def _is_valid_field_priorities(self, priorities: JsonDict) -> bool:
        seen_priorities: dict[str, object] = {}
        for field, priority_config in priorities.items():
            priority = self._extract_priority(priority_config)
            if priority is None:
                return False
            previous = seen_priorities.get(field)
            if previous is not None and previous != priority:
                return False
            seen_priorities[field] = priority
        return True

    @staticmethod
    def _extract_priority(priority_config: object) -> object | None:
        if isinstance(priority_config, dict):
            return priority_config.get("priority")
        return None

    @staticmethod
    def _is_valid_lineage_config(config: JsonDict) -> bool:
        return all(field in config for field in ("tracking_level", "source_fields"))


def create_composite_validation_service() -> CompositeValidationService:
    return CompositeValidationService()
