import pytest

from bioetl.domain.behavior.dq_rule_evaluator import evaluate_dq_rules_for_record
from bioetl.domain.config import DQConfig
from bioetl.domain.config.validation import FieldValidation
from bioetl.domain.types.dq_contracts import DQDisposition, DQViolationKind

pytestmark = pytest.mark.unit

# Simulate composite Gold schemas: mandatory seed identifiers must quarantine/fail.


@pytest.mark.parametrize(
    ("field", "error_message", "record"),
    [
        (
            "activity_id",
            "composite_activity requires the seed activity identifier",
            {"molecule_id": "CHEMBL123", "publication_id": "12345"},
        ),
        (
            "assay_id",
            "composite_assay requires the seed assay identifier",
            {"assay_description": "Test assay"},
        ),
        (
            "molecule_id",
            "composite_molecule requires the seed molecule identifier",
            {"canonical_smiles": "C"},
        ),
        (
            "publication_id",
            "composite_publication requires the seed publication identifier",
            {"title": "Test paper"},
        ),
        (
            "target_id",
            "composite_target requires the seed target identifier",
            {"pref_name": "Test target"},
        ),
    ],
)
def test_composite_mandatory_rule_missing_seed_id(
    field: str, error_message: str, record: dict[str, str]
) -> None:
    dq_config = DQConfig(
        field_validations=(
            FieldValidation(
                field=field,
                validation_type="required",
                nullable=False,
                error_message=error_message,
                severity="error",
            ),
        ),
        invalid_record_policy="quarantine",
    )

    outcomes = evaluate_dq_rules_for_record(record, dq_config, is_enricher=False)
    assert len(outcomes) > 0
    assert any(
        o.disposition in (DQDisposition.QUARANTINE, DQDisposition.FAIL)
        and o.violation_kind == DQViolationKind.BUSINESS_RULE_VIOLATION
        for o in outcomes
    )
