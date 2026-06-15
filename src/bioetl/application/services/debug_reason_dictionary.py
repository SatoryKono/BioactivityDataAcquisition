"""Debug reason dictionary for audit pack exports."""

from __future__ import annotations

DEBUG_REASON_DICTIONARY: tuple[dict[str, str], ...] = (
    {
        "reason_code": "SCHEMA_REQUIRED_FIELD_MISSING",
        "rule_layer": "silver",
        "action": "quarantine",
        "reason_message": "Required field is missing from the record payload.",
    },
    {
        "reason_code": "SCHEMA_TYPE_MISMATCH",
        "rule_layer": "silver",
        "action": "quarantine",
        "reason_message": "Record payload failed schema/type validation.",
    },
    {
        "reason_code": "DQ_SOFT_RULE_FAILED",
        "rule_layer": "silver",
        "action": "skip",
        "reason_message": "A non-fatal runtime DQ rule rejected the record.",
    },
    {
        "reason_code": "DQ_HARD_RULE_FAILED",
        "rule_layer": "silver",
        "action": "quarantine",
        "reason_message": "A blocking runtime DQ rule rejected the record.",
    },
    {
        "reason_code": "DUPLICATE_PRIMARY_KEY",
        "rule_layer": "silver",
        "action": "skip",
        "reason_message": "A duplicate business key was skipped during merge.",
    },
    {
        "reason_code": "gold_semantic_business_exclusion",
        "rule_layer": "gold",
        "action": "filter",
        "reason_message": "Gold business eligibility excluded the record.",
    },
    {
        "reason_code": "gold_semantic_profile_exclusion",
        "rule_layer": "gold",
        "action": "filter",
        "reason_message": "Gold source/profile eligibility excluded the record.",
    },
    {
        "reason_code": "CROSS_VALIDATION_NULLIFIED",
        "rule_layer": "cross_validation",
        "action": "nullify",
        "reason_message": "Cross-validation nullified one or more fields.",
    },
    {
        "reason_code": "gold_contract_schema_failure",
        "rule_layer": "gold",
        "action": "fail",
        "reason_message": "Gold strict contract validation rejected the record.",
    },
    {
        "reason_code": "gold_contract_required_failure",
        "rule_layer": "gold",
        "action": "fail",
        "reason_message": "Gold required-field contract validation rejected the record.",
    },
    {
        "reason_code": "gold_contract_reference_failure",
        "rule_layer": "gold",
        "action": "fail",
        "reason_message": "Gold reference contract validation rejected the record.",
    },
    {
        "reason_code": "QUARANTINE_POLICY",
        "rule_layer": "silver",
        "action": "quarantine",
        "reason_message": "Runtime invalid-record policy routed the record to quarantine.",
    },
)
