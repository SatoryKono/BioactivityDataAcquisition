import pytest

from bioetl.infrastructure.schemas.composite_validation import CompositeDQSchema

pytestmark = pytest.mark.unit

_MOLECULE_REQUIRED = {
    "field": "molecule_id",
    "type": "required",
    "nullable": False,
    "error_message": "composite_molecule requires the seed molecule identifier",
    "severity": "error",
}


def _gold_dq_payload(
    *,
    required_fields: list[str],
    field_validations: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "strict_validation": True,
        "invalid_record_policy": "quarantine",
        "soft_fail_threshold": 0.1,
        "hard_fail_threshold": 0.5,
        "required_fields": required_fields,
        "field_validations": field_validations,
        "cross_field_validations": [],
    }


@pytest.mark.parametrize(
    ("required_fields", "field_validations", "check_domain"),
    [
        (["molecule_id"], [_MOLECULE_REQUIRED], False),
        (["molecule_id"], [_MOLECULE_REQUIRED], True),
        (
            ["activity_id"],
            [
                {
                    "field": "target_id",
                    "type": "pattern",
                    "pattern": r"^CHEMBL\d+$",
                    "nullable": True,
                    "error_message": (
                        "target_id must preserve canonical ChEMBL identifier format"
                    ),
                    "severity": "error",
                }
            ],
            False,
        ),
    ],
)
def test_composite_gold_dq_severity_and_policy(
    required_fields: list[str],
    field_validations: list[dict[str, object]],
    check_domain: bool,
) -> None:
    schema = CompositeDQSchema.model_validate(
        _gold_dq_payload(
            required_fields=required_fields,
            field_validations=field_validations,
        )
    )
    assert schema.strict_validation is True
    assert schema.invalid_record_policy == "quarantine"
    assert schema.field_validations[0].severity == "error"
    if check_domain:
        assert schema.to_domain().field_validations[0].severity == "error"
