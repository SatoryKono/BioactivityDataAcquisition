"""Preflight validator for composite pipeline configurations.

Validates field_priorities configuration against source schemas BEFORE pipeline
execution starts. This ensures schema drift and configuration errors are caught
early, not during merge phase.

See ADR-026 for composite pipeline architectural decisions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite._preflight_orchestration import (
    PreflightSchemaOrchestrationMixin,
)
from bioetl.application.composite._preflight_reporting import (
    PreflightValidationReportingMixin,
)
from bioetl.application.composite._preflight_rules import PreflightValidationRulesMixin
from bioetl.application.composite._preflight_types import (
    FieldInfo,
    PreflightValidationError,
    PreflightValidationResult,
    SchemaFields,
    ValidationIssue,
)

if TYPE_CHECKING:
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "CompositePreflightValidationService",
    "CompositePreflightValidator",
    "FieldInfo",
    "PreflightValidationError",
    "PreflightValidationResult",
    "SchemaFields",
    "ValidationIssue",
]


class CompositePreflightValidationService(
    PreflightValidationReportingMixin,
    PreflightValidationRulesMixin,
    PreflightSchemaOrchestrationMixin,
):
    """Validates composite pipeline configuration before execution."""

    def __init__(self, logger: LoggerPort) -> None:
        self._logger = logger

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


# Backward-compatible alias for iterative NAME-001 migration.
CompositePreflightValidator = CompositePreflightValidationService
