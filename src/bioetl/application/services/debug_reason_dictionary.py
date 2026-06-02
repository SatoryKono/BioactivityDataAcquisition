"""Debug reason dictionary for audit pack exports."""

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
        "reason_code": "SEMANTIC_FILTER_EXCLUDED",
        "rule_layer": "gold",
        "action": "filter",
        "reason_message": "Gold semantic filter excluded the record.",
    },
    {
        "reason_code": "CROSS_VALIDATION_NULLIFIED",
        "rule_layer": "cross_validation",
        "action": "nullify",
        "reason_message": "Cross-validation nullified one or more fields.",
    },
    {
        "reason_code": "GOLD_CONTRACT_VIOLATION",
        "rule_layer": "gold",
        "action": "fail",
        "reason_message": "Gold strict contract validation rejected the record.",
    },
    {
        "reason_code": "QUARANTINE_POLICY",
        "rule_layer": "silver",
        "action": "quarantine",
        "reason_message": "Runtime invalid-record policy routed the record to quarantine.",
    },
)
