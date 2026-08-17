"""Helper utilities for schema classifier diffing and explanation rendering."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

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
    old_field: object,
    new_field: object,
) -> SchemaChange | None:
    """Build type-change schema change when field type changed.

    Non-mapping property values are treated as having no type (no change),
    so malformed definitions do not raise AttributeError.
    """
    old_type = old_field.get("type") if isinstance(old_field, Mapping) else None
    new_type = new_field.get("type") if isinstance(new_field, Mapping) else None
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
    """Return field removal changes in deterministic sorted order."""
    return [
        build_field_removed_change(field_name, old_properties[field_name])
        for field_name in sorted(old_properties)
        if field_name not in new_properties
    ]


def added_field_changes(
    old_properties: JsonDict,
    new_properties: JsonDict,
) -> list[SchemaChange]:
    """Return field addition changes in deterministic sorted order."""
    return [
        build_field_added_change(field_name, new_properties[field_name])
        for field_name in sorted(new_properties)
        if field_name not in old_properties
    ]


def changed_field_changes(
    old_schema: JsonDict,
    new_schema: JsonDict,
    old_properties: JsonDict,
    new_properties: JsonDict,
    required_field_additions_as_breaking: bool,
) -> tuple[list[SchemaChange], list[SchemaChange]]:
    """Return (breaking, non-breaking) changes for common and newly required fields."""
    breaking_changes: list[SchemaChange] = []
    non_breaking_changes: list[SchemaChange] = []
    old_required = _required_names(old_schema.get("required"))
    new_required = _required_names(new_schema.get("required"))
    required_changes = _required_change_target(
        breaking_changes,
        non_breaking_changes,
        required_field_additions_as_breaking,
    )
    _append_common_field_changes(
        old_properties=old_properties,
        new_properties=new_properties,
        old_required=old_required,
        new_required=new_required,
        breaking_changes=breaking_changes,
        required_changes=required_changes,
    )

    # Newly added properties that are also required must apply the same policy
    # (067-S1): otherwise only FIELD_ADDED is emitted and breaking never fires.
    _append_new_required_field_changes(
        old_properties=old_properties,
        new_properties=new_properties,
        old_required=old_required,
        new_required=new_required,
        required_changes=required_changes,
    )

    return breaking_changes, non_breaking_changes


def _required_names(value: object) -> set[str]:
    """Return strings from a valid required-field collection."""
    if isinstance(value, str | bytes | Mapping) or not isinstance(value, Iterable):
        return set()
    return {item for item in value if isinstance(item, str)}


def _required_change_target(
    breaking_changes: list[SchemaChange],
    non_breaking_changes: list[SchemaChange],
    additions_are_breaking: bool,
) -> list[SchemaChange]:
    """Select the policy-controlled destination for newly required fields."""
    return breaking_changes if additions_are_breaking else non_breaking_changes


def _append_common_field_changes(
    *,
    old_properties: JsonDict,
    new_properties: JsonDict,
    old_required: set[str],
    new_required: set[str],
    breaking_changes: list[SchemaChange],
    required_changes: list[SchemaChange],
) -> None:
    """Append type and required-status changes for fields present in both schemas."""
    common_fields = sorted(set(old_properties).intersection(new_properties))
    for field_name in common_fields:
        _append_optional_change(
            breaking_changes,
            build_field_type_change(
                field_name,
                old_properties[field_name],
                new_properties[field_name],
            ),
        )
        _append_optional_change(
            required_changes,
            build_required_field_change(field_name, old_required, new_required),
        )


def _append_new_required_field_changes(
    *,
    old_properties: JsonDict,
    new_properties: JsonDict,
    old_required: set[str],
    new_required: set[str],
    required_changes: list[SchemaChange],
) -> None:
    """Append required-status changes for newly added properties."""
    added_fields = sorted(set(new_properties) - set(old_properties))
    for field_name in added_fields:
        _append_optional_change(
            required_changes,
            build_required_field_change(field_name, old_required, new_required),
        )


def _append_optional_change(
    changes: list[SchemaChange],
    change: SchemaChange | None,
) -> None:
    """Append a detected change when present."""
    if change is not None:
        changes.append(change)


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
