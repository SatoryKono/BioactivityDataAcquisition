"""Unit tests for schema compatibility policy value types."""

from __future__ import annotations

import pytest

from bioetl.domain.types.schema_policy import (
    ChangeClassification,
    SchemaChange,
    SchemaChangeClassification,
    SchemaChangeExplanation,
    SchemaChangeType,
    SchemaCompatibilityPolicy,
    SchemaDiff,
)

pytestmark = pytest.mark.unit


def test_schema_change_breaking_classification_by_type() -> None:
    assert SchemaChange(SchemaChangeType.FIELD_REMOVED, "pmid").is_breaking()
    assert SchemaChange(SchemaChangeType.REQUIRED_FIELD_ADDED, "doi").is_breaking()
    assert SchemaChange(SchemaChangeType.FIELD_TYPE_CHANGED, "year").is_breaking()
    assert not SchemaChange(SchemaChangeType.FIELD_ADDED, "abstract").is_breaking()
    assert not SchemaChange(SchemaChangeType.REQUIRED_FIELD_REMOVED, "legacy").is_breaking()


def test_schema_diff_detects_changes_field_changes_and_renames() -> None:
    breaking = SchemaChange(SchemaChangeType.FIELD_REMOVED, "old")
    non_breaking = SchemaChange(SchemaChangeType.FIELD_RENAMED, "title")
    diff = SchemaDiff(
        breaking_changes=[breaking],
        non_breaking_changes=[non_breaking],
        unknown_changes=[],
    )

    assert diff.has_breaking_changes()
    assert diff.has_changes()
    assert diff.has_field_changes()
    assert diff.has_field_renames()
    assert not SchemaDiff([], [], []).has_changes()


def test_schema_change_classification_factories_set_review_flags() -> None:
    assert SchemaChangeClassification.patch().classification == ChangeClassification.PATCH
    assert SchemaChangeClassification.minor().classification == ChangeClassification.MINOR
    assert SchemaChangeClassification.major().classification == ChangeClassification.MAJOR

    review = SchemaChangeClassification.manual_review("ambiguous rename")
    assert review.classification == ChangeClassification.MANUAL_REVIEW
    assert review.requires_manual_review is True
    assert review.explanation == "ambiguous rename"


def test_default_and_lenient_policies_capture_semver_defaults() -> None:
    default = SchemaCompatibilityPolicy.default_policy()
    lenient = SchemaCompatibilityPolicy.lenient_policy()

    assert default.strict_field_renames is True
    assert default.enum_changes_as_breaking is True
    assert default.default_classification_for_unknown == ChangeClassification.MANUAL_REVIEW
    assert lenient.strict_field_renames is False
    assert lenient.enum_changes_as_breaking is False
    assert lenient.default_classification_for_unknown == ChangeClassification.MINOR


def test_schema_change_explanation_string_contains_and_payload() -> None:
    explanation = SchemaChangeExplanation(
        summary="Breaking field removal",
        detailed_changes=["Removed field pmid"],
        migration_guidance="Map pmid to publication_id",
        breaking_changes_count=1,
        non_breaking_changes_count=2,
    )

    assert str(explanation) == "Breaking field removal"
    assert "pmid" in explanation
    assert "publication_id" in explanation
    assert 123 not in explanation
    assert explanation.to_dict() == {
        "summary": "Breaking field removal",
        "detailed_changes": ["Removed field pmid"],
        "migration_guidance": "Map pmid to publication_id",
        "breaking_changes_count": 1,
        "non_breaking_changes_count": 2,
    }
