import pytest

from bioetl.domain.behavior.dq_rule_evaluator import evaluate_dq_rules_for_record
from bioetl.domain.config import DQConfig
from bioetl.domain.config.validation import FieldValidation
from bioetl.domain.types.dq_contracts import DQDisposition, DQViolationKind

pytestmark = pytest.mark.unit

# Simulate composite Gold schemas
# This verifies that the mandatory rules block correctly.


def test_composite_activity_mandatory_rule_missing_activity_id():
    # Provide missing field validation just as in configs/quality/entities/composite/activity.yaml
    dq_config = DQConfig(
        field_validations=(
            FieldValidation(
                field="activity_id",
                validation_type="required",
                nullable=False,
                error_message="composite_activity requires the seed activity identifier",
                severity="error",
            ),
        ),
        invalid_record_policy="quarantine",
    )
    record = {"molecule_id": "CHEMBL123", "publication_id": "12345"}

    outcomes = evaluate_dq_rules_for_record(record, dq_config, is_enricher=False)
    assert len(outcomes) > 0
    assert any(
        o.disposition in (DQDisposition.QUARANTINE, DQDisposition.FAIL)
        and o.violation_kind == DQViolationKind.BUSINESS_RULE_VIOLATION
        for o in outcomes
    )


def test_composite_assay_mandatory_rule_missing_assay_id():
    dq_config = DQConfig(
        field_validations=(
            FieldValidation(
                field="assay_id",
                validation_type="required",
                nullable=False,
                error_message="composite_assay requires the seed assay identifier",
                severity="error",
            ),
        ),
        invalid_record_policy="quarantine",
    )
    record = {"assay_description": "Test assay"}
    outcomes = evaluate_dq_rules_for_record(record, dq_config, is_enricher=False)
    assert len(outcomes) > 0
    assert any(
        o.disposition in (DQDisposition.QUARANTINE, DQDisposition.FAIL)
        and o.violation_kind == DQViolationKind.BUSINESS_RULE_VIOLATION
        for o in outcomes
    )


def test_composite_molecule_mandatory_rule_missing_molecule_id():
    dq_config = DQConfig(
        field_validations=(
            FieldValidation(
                field="molecule_id",
                validation_type="required",
                nullable=False,
                error_message="composite_molecule requires the seed molecule identifier",
                severity="error",
            ),
        ),
        invalid_record_policy="quarantine",
    )
    record = {"canonical_smiles": "C"}
    outcomes = evaluate_dq_rules_for_record(record, dq_config, is_enricher=False)
    assert len(outcomes) > 0
    assert any(
        o.disposition in (DQDisposition.QUARANTINE, DQDisposition.FAIL)
        and o.violation_kind == DQViolationKind.BUSINESS_RULE_VIOLATION
        for o in outcomes
    )


def test_composite_publication_mandatory_rule_missing_publication_id():
    dq_config = DQConfig(
        field_validations=(
            FieldValidation(
                field="publication_id",
                validation_type="required",
                nullable=False,
                error_message="composite_publication requires the seed publication identifier",
                severity="error",
            ),
        ),
        invalid_record_policy="quarantine",
    )
    record = {"title": "Test paper"}
    outcomes = evaluate_dq_rules_for_record(record, dq_config, is_enricher=False)
    assert len(outcomes) > 0
    assert any(
        o.disposition in (DQDisposition.QUARANTINE, DQDisposition.FAIL)
        and o.violation_kind == DQViolationKind.BUSINESS_RULE_VIOLATION
        for o in outcomes
    )


def test_composite_target_mandatory_rule_missing_target_id():
    dq_config = DQConfig(
        field_validations=(
            FieldValidation(
                field="target_id",
                validation_type="required",
                nullable=False,
                error_message="composite_target requires the seed target identifier",
                severity="error",
            ),
        ),
        invalid_record_policy="quarantine",
    )
    record = {"pref_name": "Test target"}
    outcomes = evaluate_dq_rules_for_record(record, dq_config, is_enricher=False)
    assert len(outcomes) > 0
    assert any(
        o.disposition in (DQDisposition.QUARANTINE, DQDisposition.FAIL)
        and o.violation_kind == DQViolationKind.BUSINESS_RULE_VIOLATION
        for o in outcomes
    )
