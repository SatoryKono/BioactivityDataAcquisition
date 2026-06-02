"""Tests for schema compatibility classifier."""

import pytest

import json


from bioetl.domain.behavior.schema_classifier import (
    SchemaClassifier,
    create_schema_classifier,
)
from bioetl.domain.types.schema_policy import (
    ChangeClassification,
    SchemaCompatibilityPolicy,
    SchemaChangeType,
)


pytestmark = pytest.mark.unit


class TestSchemaClassifier:
    """Test schema change classification."""

    def test_classifier_creation(self):
        """Test classifier creation."""
        classifier = create_schema_classifier()
        assert isinstance(classifier, SchemaClassifier)
        assert classifier.policy is not None

    def test_classifier_with_custom_policy(self):
        """Test classifier with custom policy."""
        policy = SchemaCompatibilityPolicy(
            strict_field_renames=False, required_field_additions_as_breaking=False
        )
        classifier = create_schema_classifier(policy)
        assert classifier.policy == policy

    def test_no_changes_classification(self):
        """Test classification when schemas are identical."""
        classifier = create_schema_classifier()

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }

        result = classifier.classify_changes(schema, schema)

        assert result.classification == ChangeClassification.PATCH
        assert "No significant changes" in result.explanation
        assert result.requires_manual_review is False

    def test_field_addition_classification(self):
        """Test classification of field additions."""
        classifier = create_schema_classifier()

        old_schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        new_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},  # Added field
            },
        }

        result = classifier.classify_changes(old_schema, new_schema)

        assert result.classification == ChangeClassification.MINOR
        assert "Backward-compatible field changes" in result.explanation
        assert result.requires_manual_review is False

    def test_field_removal_classification(self):
        """Test classification of field removals."""
        classifier = create_schema_classifier()

        old_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }

        new_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}  # Removed 'age' field
            },
        }

        result = classifier.classify_changes(old_schema, new_schema)

        assert result.classification == ChangeClassification.MAJOR
        assert "Breaking changes detected" in result.explanation
        assert result.requires_manual_review is False

    def test_field_type_change_classification(self):
        """Test classification of field type changes."""
        classifier = create_schema_classifier()

        old_schema = {"type": "object", "properties": {"age": {"type": "integer"}}}

        new_schema = {
            "type": "object",
            "properties": {
                "age": {"type": "string"}  # Changed from integer to string
            },
        }

        result = classifier.classify_changes(old_schema, new_schema)

        assert result.classification == ChangeClassification.MAJOR
        assert "Breaking changes detected" in result.explanation

    def test_required_field_addition_classification(self):
        """Test classification of required field additions."""
        classifier = create_schema_classifier()

        old_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }

        new_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],  # Added 'age' to required
        }

        result = classifier.classify_changes(old_schema, new_schema)

        # With default policy, this should be MAJOR
        assert result.classification == ChangeClassification.MAJOR
        assert "Breaking changes detected" in result.explanation

    def test_required_field_addition_lenient_policy(self):
        """Test classification with lenient policy."""
        policy = SchemaCompatibilityPolicy(required_field_additions_as_breaking=False)
        classifier = create_schema_classifier(policy)

        old_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }

        new_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],  # Added 'age' to required
        }

        result = classifier.classify_changes(old_schema, new_schema)

        # With lenient policy, this should be MINOR
        assert result.classification == ChangeClassification.MINOR
        assert "Backward-compatible field changes" in result.explanation

    def test_explanation_generation(self):
        """Test human-readable explanation generation."""
        classifier = create_schema_classifier()

        old_schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        new_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},  # Added field
            },
        }

        result = classifier.classify_changes(old_schema, new_schema)
        explanation = result.explanation

        assert explanation is not None
        assert "Schema changes classified as minor" in explanation.summary
        assert len(explanation.detailed_changes) == 1
        assert "FIELD_ADDED" in explanation.detailed_changes[0]
        assert explanation.migration_guidance is not None

    def test_from_string_classification(self):
        """Test classification from JSON strings."""
        classifier = create_schema_classifier()

        old_schema_str = json.dumps(
            {"type": "object", "properties": {"name": {"type": "string"}}}
        )

        new_schema_str = json.dumps(
            {
                "type": "object",
                "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            }
        )

        result = classifier.classify_from_registry_diff(old_schema_str, new_schema_str)

        assert result.classification == ChangeClassification.MINOR
        assert result.explanation is not None

    def test_invalid_json_handling(self):
        """Test handling of invalid JSON."""
        classifier = create_schema_classifier()

        result = classifier.classify_from_registry_diff("{invalid", "json")

        assert result.classification == ChangeClassification.MANUAL_REVIEW
        assert "Invalid JSON" in result.explanation
        assert result.requires_manual_review is True

    def test_complex_schema_changes(self):
        """Test classification of multiple changes."""
        classifier = create_schema_classifier()

        old_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string"},
            },
            "required": ["name"],
        }

        new_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "string"},  # Type changed
                "email": {"type": "string"},
                "phone": {"type": "string"},  # Added field
            },
            "required": ["name", "email"],  # Added to required
        }

        result = classifier.classify_changes(old_schema, new_schema)

        # Should be MAJOR due to breaking changes
        assert result.classification == ChangeClassification.MAJOR
        assert len(result.breaking_changes) >= 2  # Type change + required field
        assert len(result.non_breaking_changes) == 1  # Field addition

    def test_policy_configuration(self):
        """Test different policy configurations."""
        # Test default policy
        default_classifier = create_schema_classifier()
        assert default_classifier.policy.strict_field_renames is True

        # Test lenient policy
        lenient_classifier = create_schema_classifier(
            SchemaCompatibilityPolicy.lenient_policy()
        )
        assert lenient_classifier.policy.strict_field_renames is False
        assert lenient_classifier.policy.required_field_additions_as_breaking is False


class TestSchemaChangeTypes:
    """Test schema change type definitions."""

    def test_change_type_values(self):
        """Test change type enum values."""
        assert SchemaChangeType.FIELD_ADDED.value == "field_added"
        assert SchemaChangeType.FIELD_REMOVED.value == "field_removed"
        assert SchemaChangeType.FIELD_TYPE_CHANGED.value == "field_type_changed"
        assert SchemaChangeType.REQUIRED_FIELD_ADDED.value == "required_field_added"


class TestChangeClassification:
    """Test change classification enum."""

    def test_classification_values(self):
        """Test classification enum values."""
        assert ChangeClassification.PATCH.value == "patch"
        assert ChangeClassification.MINOR.value == "minor"
        assert ChangeClassification.MAJOR.value == "major"
        assert ChangeClassification.MANUAL_REVIEW.value == "manual_review"
        assert ChangeClassification.UNKNOWN.value == "unknown"
