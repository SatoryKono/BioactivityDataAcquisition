"""Field-priority validation helpers for composite preflight."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.composite._preflight_types import (
    ProfileInfo,
    SchemaFields,
    ValidationIssue,
)


@dataclass(frozen=True, slots=True)
class FieldPriorityScan:
    """Collected schema facts for one field-priority declaration."""

    issues: list[ValidationIssue]
    resolved_source: str | None
    field_dtypes: dict[str, str]
    field_profile_hashes: dict[str, str]


def scan_field_priority(
    *,
    field_name: str,
    priorities: tuple[str, ...],
    valid_sources: frozenset[str],
    source_fields: dict[str, SchemaFields],
    source_profiles: dict[str, ProfileInfo],
) -> FieldPriorityScan:
    """Collect schema, dtype, and profile facts for one priority list."""
    issues: list[ValidationIssue] = []
    resolved_source: str | None = None
    field_dtypes: dict[str, str] = {}
    field_profile_hashes: dict[str, str] = {}

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
        _record_field_profile_hash(
            field_name=field_name,
            source=source,
            source_lower=source_lower,
            source_profiles=source_profiles,
            field_profile_hashes=field_profile_hashes,
        )
        if resolved_source is None:
            resolved_source = source

    return FieldPriorityScan(
        issues=issues,
        resolved_source=resolved_source,
        field_dtypes=field_dtypes,
        field_profile_hashes=field_profile_hashes,
    )


def missing_from_all_sources_issue(
    field_name: str,
    priorities: tuple[str, ...],
) -> ValidationIssue:
    """Build the error emitted when a field is absent from every source."""
    return ValidationIssue(
        field=field_name,
        source=",".join(priorities),
        issue_type="missing_field",
        message=f"Field '{field_name}' not found in ANY source schema "
        f"(checked: {list(priorities)})",
        severity="error",
    )


def normalization_profile_mismatch_issue(
    *,
    field_name: str,
    priorities: tuple[str, ...],
    field_profile_hashes: dict[str, str],
    compatibility_overrides: dict[str, str],
) -> ValidationIssue | None:
    """Build a profile mismatch issue unless the field has an override."""
    has_mismatch = len(set(field_profile_hashes.values())) > 1
    if not has_mismatch or field_name in compatibility_overrides:
        return None
    return ValidationIssue(
        field=field_name,
        source=",".join(priorities),
        issue_type="normalization_profile_mismatch",
        message=(
            f"Field '{field_name}' resolves to incompatible normalization rules "
            f"across sources: {field_profile_hashes}"
        ),
        severity="error",
    )


def _record_field_profile_hash(
    *,
    field_name: str,
    source: str,
    source_lower: str,
    source_profiles: dict[str, ProfileInfo],
    field_profile_hashes: dict[str, str],
) -> None:
    """Record normalization profile hash for one available source field."""
    profile_info = source_profiles.get(source_lower)
    if profile_info is None:
        return
    field_hash = profile_info.field_hashes.get(field_name)
    if field_hash is not None:
        field_profile_hashes[source] = field_hash
