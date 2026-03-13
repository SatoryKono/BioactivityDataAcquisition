"""Rule checks for composite preflight validation."""

from __future__ import annotations

from bioetl.application.composite._preflight_types import (
    SchemaFields,
    ValidationIssue,
)
from bioetl.domain.composite.config import CompositeConfig


class PreflightValidationRulesMixin:
    """Rule checks for field priorities and type compatibility."""

    _COMPATIBLE_TYPES: tuple[frozenset[str], ...] = (
        frozenset({"str", "object", "String"}),
        frozenset(
            {"int", "Int64", "int64", "Int64Dtype", "float", "Float64", "float64"}
        ),
        frozenset({"bool", "boolean"}),
        frozenset({"date", "datetime", "datetime64"}),
    )

    def _get_valid_sources(self, config: CompositeConfig) -> frozenset[str]:
        """Extract valid source names from composite config."""
        sources: set[str] = {"seed"}

        seed_pipeline = config.seed.pipeline
        if "_" in seed_pipeline:
            seed_provider = seed_pipeline.split("_", 1)[0]
            sources.add(seed_provider)
            sources.add(seed_provider.lower())

        for enricher in config.enrichers:
            if "_" in enricher.pipeline:
                provider = enricher.pipeline.split("_", 1)[0]
                sources.add(provider)
                sources.add(provider.lower())

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
