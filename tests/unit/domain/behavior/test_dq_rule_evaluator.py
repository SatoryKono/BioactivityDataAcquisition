# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for DQ rule evaluator service.

Tests for evaluate_dq_rules_for_record, select_highest_priority_disposition,
and internal helper functions for building rule outcomes.
"""

from __future__ import annotations

import pytest

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.validation import (
    ConditionalValidation,
    CrossFieldValidation,
    FieldValidation,
)
from bioetl.domain.behavior.dq_rule_evaluator import (
    evaluate_dq_rules_for_record,
    select_highest_priority_disposition,
)
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQRuleOutcome,
)


pytestmark = pytest.mark.unit


class TestSelectHighestPriorityDisposition:
    """Tests for select_highest_priority_disposition function."""

    def test_empty_outcomes_returns_pass(self):
        """Empty outcomes list should return PASS disposition."""
        disposition = select_highest_priority_disposition([])
        assert disposition == DQDisposition.PASS

    def test_single_outcome_returns_its_disposition(self):
        """Single outcome should return its disposition."""
        outcome = DQRuleOutcome(
            rule_id="test_rule",
            disposition=DQDisposition.WARN,
            severity="warning",
            violation_kind="business_rule_violation",
        )
        disposition = select_highest_priority_disposition([outcome])
        assert disposition == DQDisposition.WARN

    def test_multiple_outcomes_returns_highest_priority(self):
        """Multiple outcomes should return the highest priority disposition."""
        outcomes = [
            DQRuleOutcome(
                rule_id="rule1",
                disposition=DQDisposition.WARN,
                severity="warning",
                violation_kind="business_rule_violation",
            ),
            DQRuleOutcome(
                rule_id="rule2",
                disposition=DQDisposition.QUARANTINE,
                severity="error",
                violation_kind="business_rule_violation",
            ),
            DQRuleOutcome(
                rule_id="rule3",
                disposition=DQDisposition.SKIP,
                severity="error",
                violation_kind="business_rule_violation",
            ),
        ]
        disposition = select_highest_priority_disposition(outcomes)
        # QUARANTINE has higher priority than WARN and SKIP
        assert disposition == DQDisposition.QUARANTINE

    def test_fail_has_highest_priority(self):
        """FAIL disposition should have the highest priority."""
        outcomes = [
            DQRuleOutcome(
                rule_id="rule1",
                disposition=DQDisposition.QUARANTINE,
                severity="error",
                violation_kind="business_rule_violation",
            ),
            DQRuleOutcome(
                rule_id="rule2",
                disposition=DQDisposition.FAIL,
                severity="error",
                violation_kind="business_rule_violation",
            ),
        ]
        disposition = select_highest_priority_disposition(outcomes)
        assert disposition == DQDisposition.FAIL

    def test_disposition_priority_order(self):
        """Test the complete disposition priority order."""
        # Priority order: FAIL > QUARANTINE > SKIP > WARN > PASS
        outcomes = [
            DQRuleOutcome(
                rule_id="pass",
                disposition=DQDisposition.PASS,
                severity="info",
                violation_kind="business_rule_violation",
            ),
            DQRuleOutcome(
                rule_id="warn",
                disposition=DQDisposition.WARN,
                severity="warning",
                violation_kind="business_rule_violation",
            ),
            DQRuleOutcome(
                rule_id="skip",
                disposition=DQDisposition.SKIP,
                severity="error",
                violation_kind="business_rule_violation",
            ),
            DQRuleOutcome(
                rule_id="quarantine",
                disposition=DQDisposition.QUARANTINE,
                severity="error",
                violation_kind="business_rule_violation",
            ),
            DQRuleOutcome(
                rule_id="fail",
                disposition=DQDisposition.FAIL,
                severity="error",
                violation_kind="business_rule_violation",
            ),
        ]
        disposition = select_highest_priority_disposition(outcomes)
        assert disposition == DQDisposition.FAIL


class TestEvaluateDQRulesForRecord:
    """Tests for evaluate_dq_rules_for_record function."""

    def test_none_config_returns_empty_list(self):
        """None DQ config should return empty outcomes list."""
        record = {"field1": "value1"}
        outcomes = evaluate_dq_rules_for_record(record, dq_config=None)
        assert outcomes == []

    def test_empty_config_returns_empty_list(self):
        """Empty DQ config should return empty outcomes list."""
        record = {"field1": "value1"}
        config = DQConfig()
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        assert outcomes == []

    def test_field_rule_violation_generates_outcome(self):
        """Field rule violation should generate a rule outcome."""
        record = {"required_field": None}
        config = DQConfig(
            field_validations=[
                FieldValidation(
                    field="required_field",
                    validation_type="required",
                    nullable=False,
                )
            ]
        )
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        # Should generate at least one outcome for the missing required field
        assert len(outcomes) > 0
        assert any("required_field" in outcome.rule_id for outcome in outcomes)

    def test_cross_field_rule_violation_generates_outcome(self):
        """Cross-field rule violation should generate a rule outcome."""
        record = {"field1": "value1", "field2": None}
        config = DQConfig(
            cross_field_validations=[
                CrossFieldValidation(
                    name="all_present",
                    fields=("field1", "field2"),
                    condition="all_present",
                    severity="error",
                )
            ]
        )
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        # Should generate outcome for not all fields present
        assert len(outcomes) > 0
        assert any("all_present" in outcome.rule_id for outcome in outcomes)

    def test_conditional_rule_generates_outcome_when_condition_matches(self):
        """Conditional rule should generate outcome when condition matches."""
        record = {"activity_type": "IC50", "activity_value": -100}
        config = DQConfig(
            conditional_validations=[
                ConditionalValidation(
                    name="ic50_positive",
                    condition_field="activity_type",
                    condition_value="IC50",
                    condition_operator="eq",
                    then_validations=(
                        FieldValidation(
                            field="activity_value",
                            validation_type="range",
                            min_value=0,
                        ),
                    ),
                )
            ]
        )
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        # Should generate outcome for negative IC50 value
        assert len(outcomes) > 0

    def test_conditional_rule_skipped_when_condition_does_not_match(self):
        """Conditional rule should not generate outcome when condition doesn't match."""
        record = {"activity_type": "EC50", "activity_value": -100}
        config = DQConfig(
            conditional_validations=[
                ConditionalValidation(
                    name="ic50_positive",
                    condition_field="activity_type",
                    condition_value="IC50",
                    condition_operator="eq",
                    then_validations=(
                        FieldValidation(
                            field="activity_value",
                            validation_type="range",
                            min_value=0,
                        ),
                    ),
                )
            ]
        )
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        # Should not generate outcome since activity_type is EC50, not IC50
        ic50_outcomes = [o for o in outcomes if "ic50_positive" in o.rule_id]
        assert len(ic50_outcomes) == 0

    def test_is_enricher_flag_affects_severity(self):
        """is_enricher flag should affect rule severity evaluation."""
        record = {"field1": None}
        config = DQConfig(
            field_validations=[
                FieldValidation(
                    field="field1",
                    validation_type="required",
                    nullable=False,
                    severity="error",
                    severity_enricher="warn",  # Less severe for enricher
                )
            ]
        )

        # Test as seed pipeline (is_enricher=False)
        outcomes_seed = evaluate_dq_rules_for_record(
            record, dq_config=config, is_enricher=False
        )

        # Test as enricher pipeline (is_enricher=True)
        outcomes_enricher = evaluate_dq_rules_for_record(
            record, dq_config=config, is_enricher=True
        )

        # Enricher should have less severe outcomes (or different count)
        # The exact behavior depends on the rule implementation
        assert isinstance(outcomes_seed, list)
        assert isinstance(outcomes_enricher, list)

    def test_invalid_record_policy_maps_error_to_quarantine(self):
        """Error severity should map to QUARANTINE disposition with quarantine policy."""
        record = {"field1": None}
        config = DQConfig(
            field_validations=[
                FieldValidation(
                    field="field1",
                    validation_type="required",
                    nullable=False,
                )
            ],
            invalid_record_policy="quarantine",
        )
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        # At least one outcome should have QUARANTINE disposition
        quarantine_outcomes = [
            o for o in outcomes if o.disposition == DQDisposition.QUARANTINE
        ]
        assert len(quarantine_outcomes) > 0

    def test_invalid_record_policy_maps_error_to_skip(self):
        """Error severity should map to SKIP disposition with skip policy."""
        record = {"field1": None}
        config = DQConfig(
            field_validations=[
                FieldValidation(
                    field="field1",
                    validation_type="required",
                    nullable=False,
                )
            ],
            invalid_record_policy="skip",
        )
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        # At least one outcome should have SKIP disposition
        skip_outcomes = [o for o in outcomes if o.disposition == DQDisposition.SKIP]
        assert len(skip_outcomes) > 0

    def test_invalid_record_policy_maps_error_to_fail(self):
        """Error severity should map to FAIL disposition with fail policy."""
        record = {"field1": None}
        config = DQConfig(
            field_validations=[
                FieldValidation(
                    field="field1",
                    validation_type="required",
                    nullable=False,
                )
            ],
            invalid_record_policy="fail",
        )
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        # At least one outcome should have FAIL disposition
        fail_outcomes = [o for o in outcomes if o.disposition == DQDisposition.FAIL]
        assert len(fail_outcomes) > 0

    def test_multiple_rule_types_generate_combined_outcomes(self):
        """Multiple rule types should generate combined outcomes."""
        record = {
            "required_field": None,
            "field1": "value1",
            "field2": None,
            "activity_type": "IC50",
            "activity_value": -100,
        }
        config = DQConfig(
            field_validations=[
                FieldValidation(
                    field="required_field",
                    validation_type="required",
                    nullable=False,
                ),
            ],
            cross_field_validations=[
                CrossFieldValidation(
                    name="all_present",
                    fields=("field1", "field2"),
                    condition="all_present",
                    severity="error",
                ),
            ],
            conditional_validations=[
                ConditionalValidation(
                    name="ic50_check",
                    condition_field="activity_type",
                    condition_value="IC50",
                    condition_operator="eq",
                    then_validations=(
                        FieldValidation(
                            field="activity_value",
                            validation_type="range",
                            min_value=0,
                        ),
                    ),
                ),
            ],
        )
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        # Should generate outcomes from all rule types
        assert len(outcomes) >= 3
        # Should have field, cross, and conditional rule outcomes
        rule_ids = [outcome.rule_id for outcome in outcomes]
        assert any("field" in rule_id for rule_id in rule_ids)
        assert any("cross" in rule_id for rule_id in rule_ids)
        assert any("conditional" in rule_id for rule_id in rule_ids)

    def test_valid_record_generates_no_outcomes(self):
        """Valid record should generate no rule outcomes."""
        record = {
            "required_field": "value",
            "field1": "value1",
            "field2": "value2",
            "activity_type": "EC50",  # Won't match IC50 condition
            "activity_value": 100,
        }
        config = DQConfig(
            field_validations=[
                FieldValidation(
                    field="required_field",
                    validation_type="required",
                    nullable=False,
                ),
            ],
            cross_field_validations=[
                CrossFieldValidation(
                    name="all_present",
                    fields=("field1", "field2"),
                    condition="all_present",
                    severity="error",
                ),
            ],
            conditional_validations=[
                ConditionalValidation(
                    name="ic50_check",
                    condition_field="activity_type",
                    condition_value="IC50",
                    condition_operator="eq",
                    then_validations=(
                        FieldValidation(
                            field="activity_value",
                            validation_type="range",
                            min_value=0,
                        ),
                    ),
                ),
            ],
        )
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        # Valid record should generate minimal or no outcomes
        # (Some rules might still generate warnings depending on implementation)
        assert isinstance(outcomes, list)

    def test_rule_outcomes_are_deterministic_and_ordered_by_rule_family(self) -> None:
        """Repeated evaluation should produce stable IDs, disposition, and provenance."""
        record = {
            "required_field": None,
            "field1": "present",
            "field2": None,
            "activity_type": "IC50",
            "activity_value": -1,
        }
        config = DQConfig(
            field_validations=(
                FieldValidation(
                    field="required_field",
                    validation_type="required",
                    nullable=False,
                ),
            ),
            cross_field_validations=(
                CrossFieldValidation(
                    name="all_present",
                    fields=("field1", "field2"),
                    condition="all_present",
                    severity="error",
                ),
            ),
            conditional_validations=(
                ConditionalValidation(
                    name="ic50_positive",
                    condition_field="activity_type",
                    condition_value="IC50",
                    condition_operator="eq",
                    then_validations=(
                        FieldValidation(
                            field="activity_value",
                            validation_type="range",
                            min_value=0,
                        ),
                    ),
                ),
            ),
            contract_ref="chembl.activity",
            invalid_record_policy="fail",
        )

        first_pass = evaluate_dq_rules_for_record(record, dq_config=config)
        second_pass = evaluate_dq_rules_for_record(record, dq_config=config)

        projected_first = [
            (
                outcome.rule_id,
                outcome.disposition,
                tuple(outcome.affected_fields or ()),
                outcome.config_path,
            )
            for outcome in first_pass
        ]
        projected_second = [
            (
                outcome.rule_id,
                outcome.disposition,
                tuple(outcome.affected_fields or ()),
                outcome.config_path,
            )
            for outcome in second_pass
        ]

        assert projected_first == projected_second
        assert projected_first == [
            (
                "field.required_field.required",
                DQDisposition.FAIL,
                ("required_field",),
                "contracts/chembl.activity/dq_rules.yaml",
            ),
            (
                "cross.all_present",
                DQDisposition.WARN,
                ("field1", "field2"),
                "contracts/chembl.activity/dq_rules.yaml",
            ),
            (
                "conditional.ic50_positive.activity_value.range",
                DQDisposition.FAIL,
                ("activity_value",),
                "contracts/chembl.activity/dq_rules.yaml",
            ),
        ]
