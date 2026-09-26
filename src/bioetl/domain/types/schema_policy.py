"""Schema compatibility policies and classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from bioetl.domain.types import JsonDict


class ChangeClassification(Enum):
    """Classification levels for schema changes."""

    PATCH = "patch"  # Backward-compatible bug fixes
    MINOR = "minor"  # Backward-compatible features
    MAJOR = "major"  # Breaking changes
    MANUAL_REVIEW = "manual_review"  # Requires human assessment
    UNKNOWN = "unknown"  # Cannot be automatically classified


class SchemaChangeType(Enum):
    """Types of schema changes that can be detected."""

    FIELD_ADDED = "field_added"
    FIELD_REMOVED = "field_removed"
    FIELD_RENAMED = "field_renamed"
    FIELD_TYPE_CHANGED = "field_type_changed"
    REQUIRED_FIELD_ADDED = "required_field_added"
    REQUIRED_FIELD_REMOVED = "required_field_removed"
    ENUM_VALUE_ADDED = "enum_value_added"
    ENUM_VALUE_REMOVED = "enum_value_removed"
    PATTERN_CHANGED = "pattern_changed"
    FORMAT_CHANGED = "format_changed"
    ADDITIONAL_PROPERTIES_CHANGED = "additional_properties_changed"
    OBJECT_STRUCTURE_CHANGED = "object_structure_changed"
    ARRAY_TYPE_CHANGED = "array_type_changed"


@dataclass(frozen=True)
class SchemaChange:
    """Individual schema change with classification."""

    change_type: SchemaChangeType
    field_path: str
    old_value: object | None = None
    new_value: object | None = None
    classification: ChangeClassification | None = None

    def is_breaking(self) -> bool:
        """Check if this change is likely breaking."""
        breaking_types = {
            SchemaChangeType.FIELD_REMOVED,
            SchemaChangeType.REQUIRED_FIELD_ADDED,
            SchemaChangeType.ENUM_VALUE_REMOVED,
            SchemaChangeType.FIELD_TYPE_CHANGED,
            SchemaChangeType.PATTERN_CHANGED,
            SchemaChangeType.FORMAT_CHANGED,
            SchemaChangeType.OBJECT_STRUCTURE_CHANGED,
            SchemaChangeType.ARRAY_TYPE_CHANGED,
        }
        return self.change_type in breaking_types


@dataclass(frozen=True)
class SchemaDiff:
    """Complete diff between two schema versions."""

    breaking_changes: list[SchemaChange]
    non_breaking_changes: list[SchemaChange]
    unknown_changes: list[SchemaChange]

    def has_breaking_changes(self) -> bool:
        """Check if there are any breaking changes."""
        return len(self.breaking_changes) > 0

    def has_changes(self) -> bool:
        """Check if there are any changes at all."""
        return (
            len(self.breaking_changes)
            + len(self.non_breaking_changes)
            + len(self.unknown_changes)
        ) > 0

    def has_field_changes(self) -> bool:
        """Check if there are any field-related changes."""
        field_types = {
            SchemaChangeType.FIELD_ADDED,
            SchemaChangeType.FIELD_REMOVED,
            SchemaChangeType.FIELD_RENAMED,
            SchemaChangeType.FIELD_TYPE_CHANGED,
            SchemaChangeType.REQUIRED_FIELD_ADDED,
            SchemaChangeType.REQUIRED_FIELD_REMOVED,
        }
        return any(
            change.change_type in field_types
            for change in self.breaking_changes + self.non_breaking_changes
        )

    def has_field_renames(self) -> bool:
        """Check if there are any field renames."""
        return any(
            change.change_type == SchemaChangeType.FIELD_RENAMED
            for change in self.breaking_changes + self.non_breaking_changes
        )


@dataclass(frozen=True)
class SchemaChangeClassification:
    """Result of schema change classification."""

    classification: ChangeClassification
    explanation: str | SchemaChangeExplanation
    requires_manual_review: bool
    breaking_changes: list[SchemaChange]
    non_breaking_changes: list[SchemaChange]
    unknown_changes: list[SchemaChange]

    @classmethod
    def patch(
        cls, explanation: str = "Backward-compatible bug fix"
    ) -> SchemaChangeClassification:
        """Create a PATCH classification."""
        return cls(
            classification=ChangeClassification.PATCH,
            explanation=explanation,
            requires_manual_review=False,
            breaking_changes=[],
            non_breaking_changes=[],
            unknown_changes=[],
        )

    @classmethod
    def minor(
        cls, explanation: str = "Backward-compatible feature addition"
    ) -> SchemaChangeClassification:
        """Create a MINOR classification."""
        return cls(
            classification=ChangeClassification.MINOR,
            explanation=explanation,
            requires_manual_review=False,
            breaking_changes=[],
            non_breaking_changes=[],
            unknown_changes=[],
        )

    @classmethod
    def major(
        cls, explanation: str = "Breaking change detected"
    ) -> SchemaChangeClassification:
        """Create a MAJOR classification."""
        return cls(
            classification=ChangeClassification.MAJOR,
            explanation=explanation,
            requires_manual_review=False,
            breaking_changes=[],
            non_breaking_changes=[],
            unknown_changes=[],
        )

    @classmethod
    def manual_review(
        cls, explanation: str = "Requires human assessment"
    ) -> SchemaChangeClassification:
        """Create a MANUAL_REVIEW classification."""
        return cls(
            classification=ChangeClassification.MANUAL_REVIEW,
            explanation=explanation,
            requires_manual_review=True,
            breaking_changes=[],
            non_breaking_changes=[],
            unknown_changes=[],
        )


@dataclass(frozen=True)
class SchemaCompatibilityPolicy:
    """Policy rules for schema compatibility classification."""

    strict_field_renames: bool = True
    treat_additional_properties_as_breaking: bool = False
    enum_changes_as_breaking: bool = True
    format_changes_as_breaking: bool = True
    pattern_changes_as_breaking: bool = True
    required_field_additions_as_breaking: bool = True
    default_classification_for_unknown: ChangeClassification = (
        ChangeClassification.MANUAL_REVIEW
    )

    @classmethod
    def default_policy(cls) -> SchemaCompatibilityPolicy:
        """Default policy matching semantic versioning principles."""
        return SchemaCompatibilityPolicy(
            strict_field_renames=True,
            treat_additional_properties_as_breaking=False,
            enum_changes_as_breaking=True,
            format_changes_as_breaking=True,
            pattern_changes_as_breaking=True,
            required_field_additions_as_breaking=True,
            default_classification_for_unknown=ChangeClassification.MANUAL_REVIEW,
        )

    @classmethod
    def lenient_policy(cls) -> SchemaCompatibilityPolicy:
        """More lenient policy for experimental schemas."""
        return SchemaCompatibilityPolicy(
            strict_field_renames=False,
            treat_additional_properties_as_breaking=False,
            enum_changes_as_breaking=False,
            format_changes_as_breaking=False,
            pattern_changes_as_breaking=False,
            required_field_additions_as_breaking=False,
            default_classification_for_unknown=ChangeClassification.MINOR,
        )


@dataclass(frozen=True)
class SchemaChangeExplanation:
    """Human-readable explanation of schema changes."""

    summary: str
    detailed_changes: list[str]
    migration_guidance: str | None = None
    breaking_changes_count: int = 0
    non_breaking_changes_count: int = 0

    def __str__(self) -> str:
        """Return summary as string representation."""
        return self.summary

    def __contains__(self, item: object) -> bool:
        """Allow string containment checks over explanation content."""
        if not isinstance(item, str):
            return False
        haystacks = [self.summary, *self.detailed_changes]
        if self.migration_guidance is not None:
            haystacks.append(self.migration_guidance)
        return any(item in text for text in haystacks)

    def to_dict(self) -> JsonDict:
        """Convert to dictionary for reporting."""
        return {
            "summary": self.summary,
            "detailed_changes": self.detailed_changes,
            "migration_guidance": self.migration_guidance,
            "breaking_changes_count": self.breaking_changes_count,
            "non_breaking_changes_count": self.non_breaking_changes_count,
        }
