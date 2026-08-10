# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for _base_transformer_structural_support module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Import the module to ensure it's covered
from bioetl.application.core import _base_transformer_structural_support  # noqa: F401

pytestmark = pytest.mark.unit

from bioetl.application.core._base_transformer_structural_support import (
    _log_structural_policy_events,
    apply_silver_filter,
    apply_structural_policy,
    classify_structural_action,
    classify_structural_shadow_comparison,
    evaluate_semantic_shadow_decision,
    record_structural_policy_metrics,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralPolicyOutcome,
    StructuralPolicySignal,
)
from bioetl.application.core.base_transformer.errors import FilteredOutError
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


class TestApplyStructuralPolicySingleFilterEval:
    """#7795: Silver filter evaluated once for non-quarantined records."""

    def test_kept_record_evaluates_silver_filter_once_and_passes(self) -> None:
        mock_owner = MagicMock()
        mock_owner.provider = "chembl"
        mock_owner.entity_type = "activity"
        mock_owner._metrics = MagicMock()
        mock_owner._structural_policy = MagicMock()
        kept = {"entity_id": "chembl:1", "value": 1.0}
        outcome = MagicMock()
        outcome.record = kept
        outcome.should_quarantine = False
        outcome.details = None
        outcome.events = ()
        mock_owner._structural_policy.apply.return_value = outcome

        decision = FilterDecision(
            include=True,
            reason_code="ok",
            rule_type="always",
            field=None,
            message="pass",
        )
        mock_owner._silver_filters = MagicMock()
        mock_owner._silver_filters.is_empty.return_value = False
        mock_owner._silver_filters.evaluate.return_value = decision

        context = MagicMock()
        result = apply_structural_policy(mock_owner, context, kept, index=0)

        assert result == kept
        mock_owner._silver_filters.evaluate.assert_called_once_with(kept)


class TestApplySilverFilter:
    """Directly exercise guard, precomputed, and rejection paths."""

    @pytest.mark.parametrize(
        ("result", "filters_configured"),
        [(None, True), ({"entity_id": "e1"}, False)],
    )
    def test_noop_when_record_or_filters_are_absent(
        self,
        result: object,
        filters_configured: bool,
    ) -> None:
        """No record or no configured filters means there is nothing to enforce."""
        owner = MagicMock()
        filters = MagicMock()
        filters.is_empty.return_value = False
        owner._silver_filters = filters if filters_configured else None
        context = MagicMock()

        apply_silver_filter(owner, context, result, index=0)

        filters.evaluate.assert_not_called()
        context.logger.debug.assert_not_called()

    def test_noop_when_filter_collection_is_empty(self) -> None:
        """An empty filter collection must not evaluate the record."""
        owner = MagicMock()
        owner._silver_filters.is_empty.return_value = True

        apply_silver_filter(owner, MagicMock(), {"entity_id": "e1"}, index=0)

        owner._silver_filters.evaluate.assert_not_called()

    def test_reuses_precomputed_passing_decision(self) -> None:
        """Shadow evaluation may be reused without evaluating filters twice."""
        owner = MagicMock(provider="chembl", entity_type="activity")
        owner._silver_filters.is_empty.return_value = False
        decision = FilterDecision(
            include=True,
            reason_code="accepted",
            rule_type="allow",
            field=None,
            message=None,
        )

        apply_silver_filter(
            owner,
            MagicMock(),
            {"entity_id": "e1"},
            index=2,
            precomputed_decision=decision,
        )

        owner._silver_filters.evaluate.assert_not_called()

    def test_evaluates_and_raises_bounded_filter_details(self) -> None:
        """A rejecting decision is logged and raised with structural-stage details."""
        owner = MagicMock(provider="chembl", entity_type="activity")
        owner._silver_filters.is_empty.return_value = False
        decision = FilterDecision(
            include=False,
            reason_code="missing_id",
            rule_type="required",
            field="entity_id",
            message=None,
        )
        owner._silver_filters.evaluate.return_value = decision
        context = MagicMock()

        with pytest.raises(FilteredOutError, match="Record excluded by silver filters"):
            apply_silver_filter(
                owner,
                context,
                {"value": 1},
                index=4,
            )

        context.logger.debug.assert_called_once_with(
            "silver_filter_quarantined",
            provider="chembl",
            entity_type="activity",
            record_index=4,
            filter_reason_code="missing_id",
            filter_rule_type="required",
            filter_field="entity_id",
        )


class TestStructuralPolicyQuarantine:
    """Exercise event logging, null-record, and quarantine evidence paths."""

    def test_log_structural_policy_events_uses_declared_log_level(self) -> None:
        """Each structural signal is emitted through its bounded severity method."""
        owner = MagicMock(provider="chembl", entity_type="activity")
        context = MagicMock()
        events = (
            StructuralPolicySignal(
                level="warning",
                event="silver_structural_type_coerced_to_null",
                details={"field": "value"},
            ),
            StructuralPolicySignal(
                level="error",
                event="silver_structural_required_field_missing",
                details={"field": "entity_id"},
            ),
        )

        _log_structural_policy_events(owner, context, 6, events)

        context.logger.warning.assert_called_once_with(
            "silver_structural_type_coerced_to_null",
            provider="chembl",
            entity_type="activity",
            record_index=6,
            field="value",
        )
        context.logger.error.assert_called_once_with(
            "silver_structural_required_field_missing",
            provider="chembl",
            entity_type="activity",
            record_index=6,
            field="entity_id",
        )

    def test_apply_structural_policy_returns_none_without_policy_call(self) -> None:
        """A transformer result of None bypasses structural policy entirely."""
        owner = MagicMock()

        assert apply_structural_policy(owner, MagicMock(), None, index=0) is None
        owner._structural_policy.apply.assert_not_called()

    def test_apply_structural_policy_raises_with_shadow_evidence(self) -> None:
        """Quarantine errors preserve structural and shadow-filter classifications."""
        original = {"value": "not-an-integer"}
        outcome = StructuralPolicyOutcome(
            record=original,
            quarantine_reason="Required field entity_id is missing",
            details={
                "reason_code": "required_field_missing",
                "field": "entity_id",
                "action_taken": "quarantine",
            },
            events=(
                StructuralPolicySignal(
                    level="error",
                    event="silver_structural_required_field_missing",
                    details={"field": "entity_id"},
                ),
            ),
        )
        owner = MagicMock(provider="chembl", entity_type="activity")
        owner._structural_policy.apply.return_value = outcome
        owner._silver_filters.is_empty.return_value = False
        owner._silver_filters.evaluate.return_value = FilterDecision(
            include=False,
            reason_code="semantic_reject",
            rule_type="required",
            field="entity_id",
            message="missing",
        )
        context = MagicMock()

        with pytest.raises(FilteredOutError) as exc_info:
            apply_structural_policy(owner, context, original, index=8)

        assert exc_info.value.details["policy_stage"] == "structural"
        assert exc_info.value.details["shadow_comparison"] == (
            "structural_reject_silver_filter_reject"
        )
        assert (
            exc_info.value.details["silver_filter_shadow_reason_code"]
            == "semantic_reject"
        )
        context.logger.error.assert_called_once()
        context.logger.debug.assert_called_once()

    def test_kept_record_raises_filtered_out_without_second_evaluate(self) -> None:
        mock_owner = MagicMock()
        mock_owner.provider = "chembl"
        mock_owner.entity_type = "activity"
        mock_owner._metrics = MagicMock()
        mock_owner._structural_policy = MagicMock()
        kept = {"entity_id": "chembl:1", "value": 1.0}
        outcome = MagicMock()
        outcome.record = kept
        outcome.should_quarantine = False
        outcome.details = None
        outcome.events = ()
        mock_owner._structural_policy.apply.return_value = outcome

        decision = FilterDecision(
            include=False,
            reason_code="reject",
            rule_type="value_range",
            field="value",
            message="too small",
        )
        mock_owner._silver_filters = MagicMock()
        mock_owner._silver_filters.is_empty.return_value = False
        mock_owner._silver_filters.evaluate.return_value = decision

        context = MagicMock()
        with pytest.raises(FilteredOutError, match="too small"):
            apply_structural_policy(mock_owner, context, kept, index=3)

        mock_owner._silver_filters.evaluate.assert_called_once_with(kept)
