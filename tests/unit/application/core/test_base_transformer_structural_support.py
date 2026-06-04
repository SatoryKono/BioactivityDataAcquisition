"""Unit tests for _base_transformer_structural_support module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Import the module to ensure it's covered
from bioetl.application.core import _base_transformer_structural_support  # noqa: F401

pytestmark = pytest.mark.unit

from bioetl.application.core._base_transformer_structural_support import (
    apply_silver_filter,
    apply_structural_policy,
    classify_structural_action,
    classify_structural_shadow_comparison,
    evaluate_semantic_shadow_decision,
    record_structural_policy_metrics,
)
from bioetl.domain.filtering import FilterDecision


class TestClassifyStructuralAction:
    """Tests for classify_structural_action function."""

    def test_classify_structural_action__required_field_missing(self):
        """Test mapping for required_field_missing reason code."""
        details = {"reason_code": "required_field_missing"}
        event_names = set()
        result = classify_structural_action(details, event_names)
        assert result == "presence_quarantine"

    def test_classify_structural_action__required_field_type_mismatch(self):
        """Test mapping for required_field_type_mismatch reason code."""
        details = {"reason_code": "required_field_type_mismatch"}
        event_names = set()
        result = classify_structural_action(details, event_names)
        assert result == "required_type_quarantine"

    def test_classify_structural_action__optional_nonnullable_field_type_mismatch(self):
        """Test mapping for optional_nonnullable_field_type_mismatch reason code."""
        details = {"reason_code": "optional_nonnullable_field_type_mismatch"}
        event_names = set()
        result = classify_structural_action(details, event_names)
        assert result == "optional_nonnullable_quarantine"

    def test_classify_structural_action__silver_structural_type_coerced_to_null(self):
        """Test mapping for silver_structural_type_coerced_to_null event."""
        details = None
        event_names = {"silver_structural_type_coerced_to_null"}
        result = classify_structural_action(details, event_names)
        assert result == "nullable_type_to_null"

    def test_classify_structural_action__unknown_reason_code(self):
        """Test that unknown reason codes return None."""
        details = {"reason_code": "unknown_code"}
        event_names = set()
        result = classify_structural_action(details, event_names)
        assert result is None

    def test_classify_structural_action__no_details_no_events(self):
        """Test that None details and empty events return None."""
        details = None
        event_names = set()
        result = classify_structural_action(details, event_names)
        assert result is None

    def test_classify_structural_action__non_string_reason_code(self):
        """Test that non-string reason codes are ignored."""
        details = {"reason_code": 123}
        event_names = set()
        result = classify_structural_action(details, event_names)
        assert result is None


class TestClassifyStructuralShadowComparison:
    """Tests for classify_structural_shadow_comparison function."""

    def test_classify_structural_shadow_comparison__both_reject(self):
        """Test comparison when both structural and silver filter reject."""
        result = classify_structural_shadow_comparison(
            structural_rejected=True,
            silver_filter_decision=FilterDecision(
                include=False,
                reason_code="test_reason",
                rule_type="test_rule",
                field="test_field",
                message="Test message",
            ),
        )
        assert result == "structural_reject_silver_filter_reject"

    def test_classify_structural_shadow_comparison__both_pass(self):
        """Test comparison when both structural and silver filter pass."""
        result = classify_structural_shadow_comparison(
            structural_rejected=False,
            silver_filter_decision=FilterDecision(
                include=True,
                reason_code="test_reason",
                rule_type="test_rule",
                field="test_field",
                message="Test message",
            ),
        )
        assert result == "structural_pass_silver_filter_pass"

    def test_classify_structural_shadow_comparison__structural_reject_silver_pass(self):
        """Test comparison when structural rejects but silver passes."""
        result = classify_structural_shadow_comparison(
            structural_rejected=True,
            silver_filter_decision=FilterDecision(
                include=True,
                reason_code="test_reason",
                rule_type="test_rule",
                field="test_field",
                message="Test message",
            ),
        )
        assert result == "structural_reject_silver_filter_pass"

    def test_classify_structural_shadow_comparison__structural_pass_silver_reject(self):
        """Test comparison when structural passes but silver rejects."""
        result = classify_structural_shadow_comparison(
            structural_rejected=False,
            silver_filter_decision=FilterDecision(
                include=False,
                reason_code="test_reason",
                rule_type="test_rule",
                field="test_field",
                message="Test message",
            ),
        )
        assert result == "structural_pass_silver_filter_reject"

    def test_classify_structural_shadow_comparison__no_silver_filter(self):
        """Test that None silver filter decision returns None."""
        result = classify_structural_shadow_comparison(
            structural_rejected=True,
            silver_filter_decision=None,
        )
        assert result is None


class TestEvaluateSemanticShadowDecision:
    """Tests for evaluate_semantic_shadow_decision function."""

    def test_evaluate_semantic_shadow_decision__no_result(self):
        """Test that None result returns None."""
        mock_owner = MagicMock()
        mock_owner._silver_filters = MagicMock()
        mock_owner._silver_filters.is_empty.return_value = False

        result = evaluate_semantic_shadow_decision(mock_owner, None)
        assert result is None

    def test_evaluate_semantic_shadow_decision__no_silver_filters(self):
        """Test that None silver_filters returns None."""
        mock_owner = MagicMock()
        mock_owner._silver_filters = None

        result = evaluate_semantic_shadow_decision(mock_owner, {"test": "record"})
        assert result is None

    def test_evaluate_semantic_shadow_decision__empty_filters(self):
        """Test that empty silver_filters returns None."""
        mock_owner = MagicMock()
        mock_owner._silver_filters = MagicMock()
        mock_owner._silver_filters.is_empty.return_value = True

        result = evaluate_semantic_shadow_decision(mock_owner, {"test": "record"})
        assert result is None

    def test_evaluate_semantic_shadow_decision__with_filters(self):
        """Test that filters are evaluated when present."""
        mock_owner = MagicMock()
        mock_owner._silver_filters = MagicMock()
        mock_owner._silver_filters.is_empty.return_value = False
        expected_decision = FilterDecision(
            include=True,
            reason_code="test_reason",
            rule_type="test_rule",
            field="test_field",
            message="Test message",
        )
        mock_owner._silver_filters.evaluate.return_value = expected_decision

        result = evaluate_semantic_shadow_decision(mock_owner, {"test": "record"})
        assert result == expected_decision
        mock_owner._silver_filters.evaluate.assert_called_once_with({"test": "record"})


class TestRecordStructuralPolicyMetrics:
    """Tests for record_structural_policy_metrics function."""

    def test_record_structural_policy_metrics__action_only(self):
        """Test metrics recording with action only."""
        mock_owner = MagicMock()
        mock_owner._metrics = MagicMock()
        mock_owner.provider = "test_provider"
        mock_owner.entity_type = "test_entity"

        record_structural_policy_metrics(
            mock_owner,
            action="presence_quarantine",
            shadow_comparison=None,
        )

        mock_owner._metrics.increment_counter.assert_called_once_with(
            "bioetl_structural_policy_events_total",
            1,
            labels={
                "provider": "test_provider",
                "entity_type": "test_entity",
                "action": "presence_quarantine",
            },
        )

    def test_record_structural_policy_metrics__shadow_comparison_only(self):
        """Test metrics recording with shadow comparison only."""
        mock_owner = MagicMock()
        mock_owner._metrics = MagicMock()
        mock_owner.provider = "test_provider"
        mock_owner.entity_type = "test_entity"

        record_structural_policy_metrics(
            mock_owner,
            action=None,
            shadow_comparison="structural_pass_silver_filter_pass",
        )

        mock_owner._metrics.increment_counter.assert_called_once_with(
            "bioetl_structural_policy_shadow_comparisons_total",
            1,
            labels={
                "provider": "test_provider",
                "entity_type": "test_entity",
                "comparison": "structural_pass_silver_filter_pass",
            },
        )

    def test_record_structural_policy_metrics__both_action_and_comparison(self):
        """Test metrics recording with both action and comparison."""
        mock_owner = MagicMock()
        mock_owner._metrics = MagicMock()
        mock_owner.provider = "test_provider"
        mock_owner.entity_type = "test_entity"

        record_structural_policy_metrics(
            mock_owner,
            action="presence_quarantine",
            shadow_comparison="structural_reject_silver_filter_reject",
        )

        assert mock_owner._metrics.increment_counter.call_count == 2

    def test_record_structural_policy_metrics__none_values(self):
        """Test that None values don't record metrics."""
        mock_owner = MagicMock()
        mock_owner._metrics = MagicMock()

        record_structural_policy_metrics(
            mock_owner,
            action=None,
            shadow_comparison=None,
        )

        mock_owner._metrics.increment_counter.assert_not_called()
