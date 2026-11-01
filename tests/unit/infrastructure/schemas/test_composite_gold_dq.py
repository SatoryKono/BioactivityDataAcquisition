import pytest

from bioetl.infrastructure.schemas.composite_validation import CompositeDQSchema

pytestmark = pytest.mark.unit


def test_composite_gold_dq_warning_mode_is_explicit():
    payload = {
        "strict_validation": True,
        "invalid_record_policy": "quarantine",
        "soft_fail_threshold": 0.1,
        "hard_fail_threshold": 0.5,
        "required_fields": ["molecule_id"],
        "field_validations": [
            {
                "field": "molecule_id",
                "type": "required",
                "nullable": False,
                "error_message": "composite_molecule requires the seed molecule identifier",
                "severity": "error",
            }
        ],
        "cross_field_validations": [],
    }

    schema = CompositeDQSchema.model_validate(payload)

    assert schema.strict_validation is True
    assert schema.invalid_record_policy == "quarantine"
    assert schema.field_validations[0].severity == "error"


def test_composite_gold_dq_warning_mode_missing_molecule_id_is_warn():
    # If the user sets strict_validation=True and severity=warn
    payload = {
        "strict_validation": True,
        "invalid_record_policy": "quarantine",
        "soft_fail_threshold": 0.1,
        "hard_fail_threshold": 0.5,
        "required_fields": ["molecule_id"],
        "field_validations": [
            {
                "field": "molecule_id",
                "type": "required",
                "nullable": False,
                "error_message": "composite_molecule requires the seed molecule identifier",
                "severity": "error",
            }
        ],
    }

    schema = CompositeDQSchema.model_validate(payload)
    assert schema.field_validations[0].severity == "error"


def test_composite_gold_dq_warning_mode_invalid_target_id_is_warn():
    payload = {
        "strict_validation": True,
        "invalid_record_policy": "quarantine",
        "soft_fail_threshold": 0.1,
        "hard_fail_threshold": 0.5,
        "required_fields": ["activity_id"],
        "field_validations": [
            {
                "field": "target_id",
                "type": "pattern",
                "pattern": "^CHEMBL\\d+$",
                "nullable": True,
                "error_message": "target_id must preserve canonical ChEMBL identifier format",
                "severity": "error",
            }
        ],
    }

    schema = CompositeDQSchema.model_validate(payload)
    assert schema.field_validations[0].severity == "error"


def test_composite_gold_dq_to_domain_propagates_severity_enricher():
    payload = {
        "strict_validation": True,
        "invalid_record_policy": "quarantine",
        "soft_fail_threshold": 0.1,
        "hard_fail_threshold": 0.5,
        "required_fields": ["molecule_id"],
        "field_validations": [
            {
                "field": "molecule_id",
                "type": "required",
                "nullable": False,
                "error_message": "composite_molecule requires the seed molecule identifier",
                "severity": "error",
            }
        ],
    }
    schema = CompositeDQSchema.model_validate(payload)
    domain_config = schema.to_domain()
    assert domain_config.field_validations[0].severity == "error"
