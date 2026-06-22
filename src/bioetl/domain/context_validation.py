"""Context validation functions for contract identity consistency."""

from __future__ import annotations

from bioetl.domain.types.contract_identity import (
    ContractIdentity,
    DQContractCompatibility,
)


def _validate_dq_contract_alignment(
    contract_identity: ContractIdentity,
    dq_contract_compatibility: DQContractCompatibility | None,
) -> list[str]:
    """Return DQ alignment issues between contract identity and DQ compatibility."""
    if dq_contract_compatibility is None:
        return []
    issues: list[str] = []
    checks = (
        (
            "DQ policy ref mismatch between contract identity and DQ compatibility",
            contract_identity.dq_policy_ref,
            dq_contract_compatibility.policy_ref,
        ),
        (
            "Rule bundle version mismatch between contract identity and DQ compatibility",
            contract_identity.rule_bundle_version,
            dq_contract_compatibility.rule_bundle_version,
        ),
    )
    for message, expected, actual in checks:
        if expected is None or expected == actual:
            continue
        issues.append(message)
    return issues


def _validate_manifest_contract_alignment(
    contract_identity: ContractIdentity,
    manifest_id: str | None,
) -> list[str]:
    """Return manifest-level contract alignment issues."""
    if manifest_id is None or contract_identity.contract_ref:
        return []
    return ["Contract identity missing contract reference"]


def _validate_contract_identity_completeness(
    contract_identity: ContractIdentity,
) -> list[str]:
    """Return missing-field issues for contract identity provenance anchors."""
    required_fields = (
        ("contract_version", contract_identity.contract_version),
        ("contract_schema_hash", contract_identity.schema_hash),
        ("dq_policy_ref", contract_identity.dq_policy_ref),
        ("rule_bundle_version", contract_identity.rule_bundle_version),
    )
    return [
        f"Contract identity missing {field_name}"
        for field_name, value in required_fields
        if not str(value or "").strip()
    ]
