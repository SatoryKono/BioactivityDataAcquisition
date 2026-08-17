"""Composite validation layer service with clear separation of checks."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.composite_validation_config import CompositeValidationConfig
from bioetl.domain.behavior.composite_validation_helpers import (
    _append_named_config_issue_if_invalid,
    _convert_to_aggregation_config,
    _convert_to_cross_validation_config,
    _create_issue,
    _extract_priority,
    _is_valid_field_priorities,
    _is_valid_lineage_config,
    append_invalid_config_section,
    as_output_schema,
    as_source_names,
)
from bioetl.domain.behavior.composite_validation_shapes import (
    as_output_schema,
    as_source_names,
    build_structural_validation_result,
    precheck_cross_validation_config,
)
from bioetl.domain.behavior.cross_validation_validator import CrossValidationValidator
from bioetl.domain.behavior.preflight_governance import (
    PreflightGovernanceConfig,
    PreflightGovernor,
)
from bioetl.domain.behavior.validation_result_envelopes import (
    build_validation_result,
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


class CompositeValidator:
    """Validator for structural and deep-preflight composite checks."""

    _as_output_schema = staticmethod(as_output_schema)
    _as_source_names = staticmethod(as_source_names)
    _extract_priority = staticmethod(_extract_priority)
    _is_valid_lineage_config = staticmethod(_is_valid_lineage_config)

    def __init__(
        self,
        *,
        aggregation_validator: AggregationValidator,
        cross_validation_validator: CrossValidationValidator,
        preflight_governance: PreflightGovernor,
    ) -> None:
        self._aggregation_validator = aggregation_validator
        self._cross_validation_validator = cross_validation_validator
        self._preflight_governance = preflight_governance

    def validate_composite(
        self,
        config: CompositeValidationConfig,
    ) -> CompositeValidationReport:
        """Run structural and deep-preflight validation for one composite config."""
        structural_result = self._run_structural_validation(config)
        if isinstance(config.composite_config, dict):
            deep_preflight_result = self._run_deep_preflight_validation(config)
        else:
            # Fail closed: do not probe a non-mapping payload with .get / membership.
            deep_preflight_result = build_validation_result(
                issues=[],
                validation_layer=ValidationLayer.DEEP_PREFLIGHT,
                execution_context={"pipeline_name": config.pipeline_name},
            )
        validation_report = CompositeValidationReport(
            structural_result=structural_result,
            deep_preflight_result=deep_preflight_result,
            runtime_guard_result=None,
        )
        governance_config = PreflightGovernanceConfig(
            policy=config.governance_policy,
            ci_integration=(
                config.execution_context.get("ci_integration", False)
                if config.execution_context
                else False
            ),
        )
        governance_decision = self._preflight_governance.apply_governance(
            validation_report,
            execution_context=config.execution_context,
            config=governance_config,
        )
        return replace(
            validation_report, execution_decision=governance_decision
        )  # NOSONAR

    def _run_structural_validation(
        self,
        config: CompositeValidationConfig,
    ) -> ValidationResult:
        return build_structural_validation_result(
            pipeline_name=config.pipeline_name,
            composite_config=config.composite_config,
        )

    def _run_deep_preflight_validation(
        self,
        config: CompositeValidationConfig,
    ) -> ValidationResult:
        issues = self._deep_preflight_issues(config.composite_config)
        result: ValidationResult = build_validation_result(
            issues=issues,
            validation_layer=ValidationLayer.DEEP_PREFLIGHT,
            execution_context={"pipeline_name": config.pipeline_name},
        )
        return result

    def _deep_preflight_issues(
        self, composite_config: JsonDict
    ) -> list[ValidationIssue]:
        if not isinstance(composite_config, dict):
            return [
                _create_issue(
                    IssueCode.CMP_STR_SCHEMA_001,
                    ValidationSeverity.BLOCKER,
                    "Composite config must be a dictionary",
                    {"actual_type": type(composite_config).__name__},
                )
            ]
        issues = self._aggregation_preflight_issues(composite_config)
        issues.extend(self._cross_validation_preflight_issues(composite_config))
        append_invalid_config_section(
            issues=issues,
            composite_config=composite_config,
            config_key="field_priorities",
            validator=_is_valid_field_priorities,
            code=IssueCode.CMP_PF_FIELD_001,
            severity=ValidationSeverity.WARNING,
            message="Conflicting or invalid field priorities detected",
            details_key="priorities",
        )
        append_invalid_config_section(
            issues=issues,
            composite_config=composite_config,
            config_key="lineage",
            validator=_is_valid_lineage_config,
            code=IssueCode.CMP_PF_LIN_001,
            severity=ValidationSeverity.BLOCKER,
            message="Insufficient lineage tracking configuration",
            details_key="config",
        )
        return issues

    def _aggregation_preflight_issues(
        self, composite_config: JsonDict
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        aggregation = composite_config.get("aggregation")
        if aggregation is None:
            return issues
        output_schema, schema_issues = self._as_output_schema(
            composite_config.get("output_schema", {})
        )
        issues.extend(schema_issues)
        if output_schema is not None:
            issues.extend(self._validate_aggregation_config(aggregation, output_schema))
        return issues

    def _cross_validation_preflight_issues(
        self, composite_config: JsonDict
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        cross_validation_config = composite_config.get("cross_validation")
        if cross_validation_config is None:
            return issues
        source_names, source_issues = self._as_source_names(
            composite_config.get("sources", [])
        )
        issues.extend(source_issues)
        if source_names is not None:
            issues.extend(
                self._validate_cross_validation_config(
                    cross_validation_config, source_names
                )
            )
        return issues

    def _as_output_schema(
        self, raw: object
    ) -> tuple[JsonDict | None, list[ValidationIssue]]:
        return as_output_schema(raw)

    def _as_source_names(
        self, raw: object
    ) -> tuple[list[str] | None, list[ValidationIssue]]:
        return as_source_names(raw)

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
        _append_named_config_issue_if_invalid(
            issues=issues,
            composite_config=composite_config,
            config_key=config_key,
            validator=validator,
            code=code,
            severity=severity,
            message=message,
            details_key=details_key,
        )

    def _create_issue(
        self,
        code: IssueCode,
        severity: ValidationSeverity,
        message: str,
        details: JsonDict | None = None,
        location: str | None = None,
    ) -> ValidationIssue:
        return _create_issue(code, severity, message, details, location)

    def _validate_aggregation_config(
        self,
        config: JsonDict | object,
        source_schema: JsonDict,
    ) -> list[ValidationIssue]:
        if not isinstance(config, dict):
            return [
                _create_issue(
                    IssueCode.CMP_PF_AGG_001,
                    ValidationSeverity.BLOCKER,
                    "Aggregation configuration must be a dictionary",
                    {"actual_type": type(config).__name__},
                )
            ]
        try:
            aggregation_config = _convert_to_aggregation_config(config)
        except (KeyError, TypeError, ValueError) as exc:
            return [
                _create_issue(
                    IssueCode.CMP_PF_AGG_001,
                    ValidationSeverity.BLOCKER,
                    f"Invalid aggregation config format: {exc!s}",
                    {"config": config},
                )
            ]
        validation_result: ValidationResult = (
            self._aggregation_validator.validate_aggregation_config(
                aggregation_config,
                source_schema,
            )
        )
        issues: list[ValidationIssue] = validation_result.issues
        return issues

    def _validate_cross_validation_config(
        self, config: JsonDict, source_names: list[str]
    ) -> list[ValidationIssue]:
        precheck_errors = self._precheck_cross_validation_config(config)
        if precheck_errors:
            return precheck_errors
        try:
            cross_val_config = _convert_to_cross_validation_config(config)
        except (KeyError, TypeError, ValueError) as exc:
            return [
                _create_issue(
                    IssueCode.CMP_PF_CV_002,
                    ValidationSeverity.BLOCKER,
                    f"Invalid cross-validation config format: {exc!s}",
                    {"config": config},
                )
            ]
        validation_result: ValidationResult = (
            self._cross_validation_validator.validate_cross_validation_config(
                cross_val_config, source_names
            )
        )
        issues: list[ValidationIssue] = validation_result.issues
        return issues

    def _precheck_cross_validation_config(
        self,
        config: JsonDict,
    ) -> list[ValidationIssue]:
        return precheck_cross_validation_config(config)

    def _is_valid_field_priorities(self, priorities: JsonDict) -> bool:
        return _is_valid_field_priorities(priorities)

    @staticmethod
    def _extract_priority(priority_config: object) -> object | None:
        return _extract_priority(priority_config)

    @staticmethod
    def _is_valid_lineage_config(config: JsonDict) -> bool:
        return _is_valid_lineage_config(config)
