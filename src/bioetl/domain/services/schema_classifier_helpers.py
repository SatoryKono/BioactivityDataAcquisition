"""Helper utilities for schema classifier diffing and explanation rendering."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.domain.types.schema_policy import (
    ChangeClassification,
    SchemaChange,
    SchemaChangeType,
    SchemaDiff,
)


def build_field_removed_change(field_name: str, old_value: object) -> SchemaChange:
    """Build schema change for removed field."""
    return SchemaChange(
        change_type=SchemaChangeType.FIELD_REMOVED,
        field_path=f"properties.{field_name}",
        old_value=old_value,
        new_value=None,
    )


def build_field_added_change(field_name: str, new_value: object) -> SchemaChange:
    """Build schema change for added field."""
    return SchemaChange(
        change_type=SchemaChangeType.FIELD_ADDED,
        field_path=f"properties.{field_name}",
        old_value=None,
        new_value=new_value,
    )


def build_field_type_change(
    field_name: str,
    old_field: JsonDict,
    new_field: JsonDict,
) -> SchemaChange | None:
    """Build type-change schema change when field type changed."""
    old_type = old_field.get("type")
    new_type = new_field.get("type")
    if old_type == new_type:
        return None
    return SchemaChange(
        change_type=SchemaChangeType.FIELD_TYPE_CHANGED,
        field_path=f"properties.{field_name}.type",
        old_value=old_type,
        new_value=new_type,
    )


def build_required_field_change(
    field_name: str,
    old_required: set[str],
    new_required: set[str],
) -> SchemaChange | None:
    """Build required-field-added change when status flipped to required."""
    if field_name not in new_required or field_name in old_required:
        return None
    return SchemaChange(
        change_type=SchemaChangeType.REQUIRED_FIELD_ADDED,
        field_path=f"properties.{field_name}",
        old_value=False,
        new_value=True,
    )


def removed_field_changes(
    old_properties: JsonDict,
    new_properties: JsonDict,
) -> list[SchemaChange]:
    """Return field removal changes."""
    return [
        build_field_removed_change(field_name, old_properties[field_name])
        for field_name in old_properties
        if field_name not in new_properties
    ]


def added_field_changes(
    old_properties: JsonDict,
    new_properties: JsonDict,
) -> list[SchemaChange]:
    """Return field addition changes."""
    return [
        build_field_added_change(field_name, new_properties[field_name])
        for field_name in new_properties
        if field_name not in old_properties
    ]


def changed_field_changes(
    old_schema: JsonDict,
    new_schema: JsonDict,
    old_properties: JsonDict,
    new_properties: JsonDict,
    required_field_additions_as_breaking: bool,
) -> tuple[list[SchemaChange], list[SchemaChange]]:
    """Return (breaking, non-breaking) changes for common fields."""
    breaking_changes: list[SchemaChange] = []
    non_breaking_changes: list[SchemaChange] = []
    old_required = set(old_schema.get("required", []))
    new_required = set(new_schema.get("required", []))

    for field_name in set(old_properties).intersection(new_properties):
        old_field = old_properties[field_name]
        new_field = new_properties[field_name]

        type_change = build_field_type_change(field_name, old_field, new_field)
        if type_change is not None:
            breaking_changes.append(type_change)

        required_change = build_required_field_change(
            field_name=field_name,
            old_required=old_required,
            new_required=new_required,
        )
        if required_change is None:
            continue
        target_changes = (
            breaking_changes
            if required_field_additions_as_breaking
            else non_breaking_changes
        )
        target_changes.append(required_change)

    return breaking_changes, non_breaking_changes


def build_detailed_changes(diff: SchemaDiff) -> list[str]:
    """Build human-readable line items for all detected changes."""
    descriptions = [
        f"❌ BREAKING: {change.change_type.name} at {change.field_path}"
        for change in diff.breaking_changes
    ]
    descriptions.extend(
        f"✅ NON-BREAKING: {change.change_type.name} at {change.field_path}"
        for change in diff.non_breaking_changes
    )
    descriptions.extend(
        f"⚠️  UNKNOWN: {change.change_type.name} at {change.field_path}"
        for change in diff.unknown_changes
    )
    return descriptions


def migration_guidance_for_classification(
    classification: ChangeClassification,
) -> str | None:
    """Return migration guidance text for classification."""
    guidance_map: dict[ChangeClassification, str] = {
        ChangeClassification.MAJOR: (
            "Major version bump required. Consider providing migration tools or "
            "backward compatibility layers."
        ),
        ChangeClassification.MINOR: (
            "Minor version bump recommended. Changes are backward-compatible."
        ),
        ChangeClassification.PATCH: (
            "Patch version bump sufficient. No migration required."
        ),
    }
    return guidance_map.get(classification)
