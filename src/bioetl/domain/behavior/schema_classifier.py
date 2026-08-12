"""Policy-aware schema change classifier."""

from __future__ import annotations

import json

from bioetl.domain.behavior.schema_classifier_helpers import (
    added_field_changes,
    build_detailed_changes,
    changed_field_changes,
    migration_guidance_for_classification,
    removed_field_changes,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.schema_policy import (
    ChangeClassification,
    SchemaChangeClassification,
    SchemaChangeExplanation,
    SchemaCompatibilityPolicy,
    SchemaDiff,
)


class SchemaClassifier:
    """Policy-aware schema change classifier."""

    def __init__(self, policy: SchemaCompatibilityPolicy | None = None):
        """Initialize classifier with optional policy."""
        self.policy = policy or SchemaCompatibilityPolicy.default_policy()

    def classify_changes(
        self, old_schema: JsonDict, new_schema: JsonDict
    ) -> SchemaChangeClassification:
        """Classify schema changes between two versions."""
        diff = self._calculate_diff(old_schema, new_schema)
        classification = self._apply_policy_rules(diff)
        explanation = self._generate_explanation(diff, classification)
        return SchemaChangeClassification(
            classification=classification.classification,
            explanation=explanation,
            requires_manual_review=classification.requires_manual_review,
            breaking_changes=classification.breaking_changes,
            non_breaking_changes=classification.non_breaking_changes,
            unknown_changes=classification.unknown_changes,
        )

    def _calculate_diff(self, old_schema: JsonDict, new_schema: JsonDict) -> SchemaDiff:
        """Calculate detailed diff between two schemas."""
        old_properties = old_schema.get("properties", {})
        new_properties = new_schema.get("properties", {})
        breaking_changes = removed_field_changes(old_properties, new_properties)
        non_breaking_changes = added_field_changes(old_properties, new_properties)
        changed_breaking, changed_non_breaking = changed_field_changes(
            old_schema=old_schema,
            new_schema=new_schema,
            old_properties=old_properties,
            new_properties=new_properties,
            required_field_additions_as_breaking=(
                self.policy.required_field_additions_as_breaking
            ),
        )
        breaking_changes.extend(changed_breaking)
        non_breaking_changes.extend(changed_non_breaking)
        return SchemaDiff(
            breaking_changes=breaking_changes,
            non_breaking_changes=non_breaking_changes,
            unknown_changes=[],
        )

    def _apply_policy_rules(self, diff: SchemaDiff) -> SchemaChangeClassification:
        """Apply policy rules to diff results."""
        if diff.has_breaking_changes():
            return SchemaChangeClassification(
                classification=ChangeClassification.MAJOR,
                explanation="Breaking changes detected",
                requires_manual_review=False,
                breaking_changes=diff.breaking_changes,
                non_breaking_changes=diff.non_breaking_changes,
                unknown_changes=diff.unknown_changes,
            )

        if diff.non_breaking_changes:
            return SchemaChangeClassification(
                classification=ChangeClassification.MINOR,
                explanation="Backward-compatible field changes",
                requires_manual_review=False,
                breaking_changes=diff.breaking_changes,
                non_breaking_changes=diff.non_breaking_changes,
                unknown_changes=diff.unknown_changes,
            )

        if not diff.has_changes():
            return SchemaChangeClassification.patch(
                explanation="No significant changes detected"
            )

        if diff.unknown_changes:
            return SchemaChangeClassification.manual_review(
                explanation="Unknown changes require manual review"
            )

        return SchemaChangeClassification(
            classification=self.policy.default_classification_for_unknown,
            explanation="Changes classified according to policy defaults",
            requires_manual_review=True,
            breaking_changes=diff.breaking_changes,
            non_breaking_changes=diff.non_breaking_changes,
            unknown_changes=diff.unknown_changes,
        )

    def _generate_explanation(
        self, diff: SchemaDiff, classification: SchemaChangeClassification
    ) -> SchemaChangeExplanation:
        """Generate human-readable explanation of changes."""
        base_explanation = classification.explanation
        if isinstance(base_explanation, SchemaChangeExplanation):
            summary_prefix = base_explanation.summary
        else:
            summary_prefix = base_explanation
        return SchemaChangeExplanation(
            summary=(
                f"{summary_prefix}. "
                f"Schema changes classified as {classification.classification.value}"
            ),
            detailed_changes=build_detailed_changes(diff),
            migration_guidance=migration_guidance_for_classification(
                classification.classification
            ),
            breaking_changes_count=len(diff.breaking_changes),
            non_breaking_changes_count=len(diff.non_breaking_changes),
        )

    def classify_from_registry_diff(
        self, old_schema_str: str, new_schema_str: str
    ) -> SchemaChangeClassification:
        """Classify changes from string representations."""
        try:
            old_schema = json.loads(old_schema_str)
            new_schema = json.loads(new_schema_str)
        except json.JSONDecodeError as e:
            return SchemaChangeClassification.manual_review(
                explanation=f"Invalid JSON: {e!s}"
            )
        if not isinstance(old_schema, dict) or not isinstance(new_schema, dict):
            return SchemaChangeClassification.manual_review(
                explanation=(
                    "Registry schema payloads must be JSON objects; "
                    f"got {type(old_schema).__name__} and {type(new_schema).__name__}"
                )
            )
        return self.classify_changes(old_schema, new_schema)


def create_schema_classifier(
    policy: SchemaCompatibilityPolicy | None = None,
) -> SchemaClassifier:
    """Factory function for SchemaClassifier."""
    return SchemaClassifier(policy)
