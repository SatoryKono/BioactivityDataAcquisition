"""Cross-validation governance service for composite pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import ValidationIssue, ValidationResult
from bioetl.domain.types.validation_severity import IssueCode, ValidationLayer, ValidationSeverity


@dataclass(frozen=True)
class CrossValidationConfig:
    """Configuration for cross-validation governance."""

    pairs: list[dict]
    rules: dict[str, str]
    strict_mode: bool = True
    coverage_threshold: Optional[float] = None
    consistency_threshold: Optional[float] = None


class CrossValidationValidator:
    """Service for validating cross-validation configurations."""

    def validate_cross_validation_config(
        self,
        config: CrossValidationConfig,
        source_names: list[str],
        execution_context: Optional[JsonDict] = None,
    ) -> ValidationResult:
        """Validate cross-validation configuration semantics."""
        issues = []

        # Validate pairs structure and coverage
        pair_issues = self._validate_cross_validation_pairs(config, source_names)
        issues.extend(pair_issues)

        # Validate rules consistency
        rule_issues = self._validate_cross_validation_rules(config)
        issues.extend(rule_issues)

        # Validate thresholds if specified
        threshold_issues = self._validate_thresholds(config)
        issues.extend(threshold_issues)

        # Validate coverage if strict mode
        if config.strict_mode:
            coverage_issues = self._validate_coverage(config, source_names)
            issues.extend(coverage_issues)

        return ValidationResult(
            issues=issues,
            validation_layer=ValidationLayer.DEEP_PREFLIGHT,
            execution_context=execution_context or {},
        )

    def _validate_cross_validation_pairs(
        self,
        config: CrossValidationConfig,
        source_names: list[str],
    ) -> list[ValidationIssue]:
        """Validate cross-validation pair structure and source references."""
        issues = []

        if not config.pairs:
            issues.append(
                self._create_issue(
                    IssueCode.CMP_PF_CV_002,
                    ValidationSeverity.BLOCKER,
                    "Cross-validation pairs cannot be empty",
                    {"pairs": config.pairs},
                )
            )
            return issues

        valid_source_names = set(source_names)

        for i, pair in enumerate(config.pairs):
            if not isinstance(pair, dict):
                issues.append(
                    self._create_issue(
                        IssueCode.CMP_PF_CV_003,
                        ValidationSeverity.BLOCKER,
                        f"Cross-validation pair {i} must be a dictionary",
                        {"pair": pair, "index": i},
                    )
                )
                continue

            # Validate pair structure
            if len(pair) != 1:
                issues.append(
                    self._create_issue(
                        IssueCode.CMP_PF_CV_004,
                        ValidationSeverity.BLOCKER,
                        f"Cross-validation pair {i} must have exactly one source mapping",
                        {"pair": pair, "index": i},
                    )
                )
                continue

            # Extract source names from pair
            for source_name, comparison_sources in pair.items():
                if source_name not in valid_source_names:
                    issues.append(
                        self._create_issue(
                            IssueCode.CMP_PF_CV_005,
                            ValidationSeverity.BLOCKER,
                            f"Cross-validation source '{source_name}' not found in pipeline sources",
                            {
                                "source_name": source_name,
                                "available_sources": list(valid_source_names),
                                "pair_index": i,
                            },
                        )
                    )

                if not isinstance(comparison_sources, (str, list)):
                    issues.append(
                        self._create_issue(
                            IssueCode.CMP_PF_CV_006,
                            ValidationSeverity.BLOCKER,
                            f"Comparison sources for '{source_name}' must be string or list",
                            {"source_name": source_name, "comparison_sources": comparison_sources},
                        )
                    )
                    continue

                # Normalize to list and validate comparison sources
                if isinstance(comparison_sources, str):
                    comparison_sources = [comparison_sources]

                for comp_source in comparison_sources:
                    if comp_source not in valid_source_names:
                        issues.append(
                            self._create_issue(
                                IssueCode.CMP_PF_CV_007,
                                ValidationSeverity.BLOCKER,
                                f"Comparison source '{comp_source}' not found in pipeline sources",
                                {
                                    "comparison_source": comp_source,
                                    "source_name": source_name,
                                    "available_sources": list(valid_source_names),
                                },
                            )
                        )

        return issues

    def _validate_cross_validation_rules(
        self,
        config: CrossValidationConfig,
    ) -> list[ValidationIssue]:
        """Validate cross-validation rules consistency."""
        issues = []

        if not config.rules:
            issues.append(
                self._create_issue(
                    IssueCode.CMP_PF_CV_008,
                    ValidationSeverity.BLOCKER,
                    "Cross-validation rules cannot be empty",
                    {"rules": config.rules},
                )
            )
            return issues

        supported_rule_types = {"strict", "lenient", "warn", "custom"}

        for rule_name, rule_type in config.rules.items():
            if not isinstance(rule_type, str):
                issues.append(
                    self._create_issue(
                        IssueCode.CMP_PF_CV_009,
                        ValidationSeverity.BLOCKER,
                        f"Rule '{rule_name}' must be a string type",
                        {"rule_name": rule_name, "actual_type": type(rule_type).__name__},
                    )
                )
                continue

            if rule_type not in supported_rule_types:
                issues.append(
                    self._create_issue(
                        IssueCode.CMP_PF_CV_010,
                        ValidationSeverity.BLOCKER,
                        f"Unsupported cross-validation rule type '{rule_type}'",
                        {
                            "rule_name": rule_name,
                            "rule_type": rule_type,
                            "supported_types": list(supported_rule_types),
                        },
                    )
                )

        return issues

    def _validate_thresholds(
        self,
        config: CrossValidationConfig,
    ) -> list[ValidationIssue]:
        """Validate threshold values if specified."""
        issues = []

        if config.coverage_threshold is not None:
            if not (0.0 <= config.coverage_threshold <= 1.0):
                issues.append(
                    self._create_issue(
                        IssueCode.CMP_PF_CV_011,
                        ValidationSeverity.BLOCKER,
                        "Coverage threshold must be between 0.0 and 1.0",
                        {"coverage_threshold": config.coverage_threshold},
                    )
                )

        if config.consistency_threshold is not None:
            if not (0.0 <= config.consistency_threshold <= 1.0):
                issues.append(
                    self._create_issue(
                        IssueCode.CMP_PF_CV_012,
                        ValidationSeverity.BLOCKER,
                        "Consistency threshold must be between 0.0 and 1.0",
                        {"consistency_threshold": config.consistency_threshold},
                    )
                )

        return issues

    def _validate_coverage(
        self,
        config: CrossValidationConfig,
        source_names: list[str],
    ) -> list[ValidationIssue]:
        """Validate that cross-validation covers all sources in strict mode."""
        issues = []

        if not source_names:
            return issues

        # Extract all sources mentioned in pairs
        covered_sources = set()
        for pair in config.pairs:
            if isinstance(pair, dict):
                for source_name in pair.keys():
                    covered_sources.add(source_name)
                for comparison_sources in pair.values():
                    if isinstance(comparison_sources, str):
                        covered_sources.add(comparison_sources)
                    elif isinstance(comparison_sources, list):
                        covered_sources.update(comparison_sources)

        # Check if all sources are covered
        uncovered_sources = set(source_names) - covered_sources
        if uncovered_sources:
            issues.append(
                self._create_issue(
                    IssueCode.CMP_PF_CV_013,
                    ValidationSeverity.WARNING,
                    f"Cross-validation does not cover all sources: {sorted(uncovered_sources)}",
                    {
                        "uncovered_sources": sorted(uncovered_sources),
                        "covered_sources": sorted(covered_sources),
                        "all_sources": sorted(source_names),
                    },
                )
            )

        return issues

    def _create_issue(
        self,
        code: IssueCode,
        severity: ValidationSeverity,
        message: str,
        details: JsonDict | None = None,
    ) -> ValidationIssue:
        """Create a validation issue."""
        return ValidationIssue(
            code=code,
            severity=severity,
            layer=ValidationLayer.DEEP_PREFLIGHT,
            message=message,
            details=details or {},
        )


def create_cross_validation_validator() -> CrossValidationValidator:
    """Factory function for CrossValidationValidator."""
    return CrossValidationValidator()