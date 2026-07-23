"""Shared control-plane identity ref helpers for manifest builders."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

CONTRACT_IDENTITY_FIELD_NAMES: tuple[str, ...] = (
    "contract_ref",
    "contract_version",
    "contract_schema_hash",
    "dq_policy_ref",
    "rule_bundle_version",
    "normalization_profile_ref",
    "normalization_profile_version",
    "normalization_profile_hash",
)

__all__ = [
    "CONTRACT_IDENTITY_FIELD_NAMES",
    "build_contract_identity_field_values",
    "build_contract_identity_field_values_from_mapping",
    "build_control_plane_identity_ref_values",
]


def build_contract_identity_field_values(
    *,
    contract_ref: str,
    contract_version: str | None,
    contract_schema_hash: str | None,
    dq_policy_ref: str | None,
    rule_bundle_version: str | None,
    normalization_profile_ref: str | None,
    normalization_profile_version: str | None,
    normalization_profile_hash: str | None,
) -> dict[str, str | None]:
    """Return the shared mapping shape for manifest contract identity fields."""
    return {
        "contract_ref": contract_ref,
        "contract_version": contract_version,
        "contract_schema_hash": contract_schema_hash,
        "dq_policy_ref": dq_policy_ref,
        "rule_bundle_version": rule_bundle_version,
        "normalization_profile_ref": normalization_profile_ref,
        "normalization_profile_version": normalization_profile_version,
        "normalization_profile_hash": normalization_profile_hash,
    }


def build_contract_identity_field_values_from_mapping(
    values: Mapping[str, object],
) -> dict[str, str | None]:
    """Build contract-identity field values from a same-named locals() mapping."""
    optional_str = "str | None"
    return build_contract_identity_field_values(
        contract_ref=cast("str", values["contract_ref"]),
        contract_version=cast(optional_str, values.get("contract_version")),
        contract_schema_hash=cast(optional_str, values.get("contract_schema_hash")),
        dq_policy_ref=cast(optional_str, values.get("dq_policy_ref")),
        rule_bundle_version=cast(optional_str, values.get("rule_bundle_version")),
        normalization_profile_ref=cast(
            optional_str, values.get("normalization_profile_ref")
        ),
        normalization_profile_version=cast(
            optional_str, values.get("normalization_profile_version")
        ),
        normalization_profile_hash=cast(
            optional_str, values.get("normalization_profile_hash")
        ),
    )


def build_control_plane_identity_ref_values(
    *,
    contract_identity_values: dict[str, str | None],
    required_persistence_profile: str | None,
) -> dict[str, str | None]:
    """Return reusable control-plane identity kwargs shared by ref builders."""
    return {
        **contract_identity_values,
        "required_persistence_profile": required_persistence_profile,
    }
