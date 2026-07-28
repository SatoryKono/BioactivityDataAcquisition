# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods provided by concrete composition.
"""Reporting helpers for preflight validation results."""

from __future__ import annotations

from bioetl.application.composite._preflight_types import (
    PreflightValidationResult,
    ProfileInfo,
    SchemaFields,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.ports import LoggerPort


class PreflightValidationReportingMixin:
    """Centralized logging/report formatting for preflight validation."""

    _logger: LoggerPort

    def _log_schema_loading_summary(
        self, source_fields: dict[str, SchemaFields]
    ) -> None:
        """Log schema loading summary before validation checks."""
        self._logger.debug(
            "Preflight validator loaded source schemas",
            sources=list(source_fields.keys()),
            field_counts={
                source: len(fields) for source, fields in source_fields.items()
            },
        )

    def _log_profile_loading_summary(
        self, source_profiles: dict[str, ProfileInfo]
    ) -> None:
        """Log normalization-profile loading summary before compatibility checks."""
        if not source_profiles:
            return
        self._logger.debug(
            "Preflight validator loaded source normalization profiles",
            sources=list(source_profiles.keys()),
            profile_refs={
                source: {
                    "profile_name": profile.profile_name,
                    "profile_version": profile.profile_version,
                    "profile_hash": profile.profile_hash,
                }
                for source, profile in source_profiles.items()
            },
        )

    def _log_validation_result(
        self,
        *,
        is_valid: bool,
        config: CompositeConfig,
        result: PreflightValidationResult,
        field_priorities_count: int,
    ) -> None:
        """Log success or failure summary after validation."""
        if is_valid:
            self._logger.info(
                "Preflight validation passed",
                composite=config.name,
                fields_validated=field_priorities_count,
                resolved_fields=result.resolved_fields,
                profile_refs={
                    source: {
                        "profile_name": profile.profile_name,
                        "profile_version": profile.profile_version,
                        "profile_hash": profile.profile_hash,
                    }
                    for source, profile in result.profile_refs.items()
                },
            )
            return

        self._logger.error(
            "Preflight validation failed",
            composite=config.name,
            error_count=len(result.errors),
            warning_count=len(result.warnings),
            errors=[
                {"field": error.field, "issue": error.issue_type, "msg": error.message}
                for error in result.errors
            ],
        )

    def log_resolved_field_sources(
        self, result: PreflightValidationResult, composite_name: str
    ) -> None:
        """Log resolved field sources for debugging and auditability.

        Args:
            result: Preflight validation result containing resolved field sources.
            composite_name: Name of the composite pipeline for log context.
        """
        if not result.resolved_fields:
            return

        self._logger.info(
            "Field priority resolution",
            composite=composite_name,
            resolved_fields=result.resolved_fields,
            field_count=len(result.resolved_fields),
        )

        for field_name, source in result.resolved_fields.items():
            self._logger.debug(
                "Resolved field source",
                composite=composite_name,
                field=field_name,
                primary_source=source,
            )
