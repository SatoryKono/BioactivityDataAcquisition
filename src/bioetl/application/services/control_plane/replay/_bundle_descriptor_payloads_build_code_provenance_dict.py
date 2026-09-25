"""Extracted _build_code_provenance_dict for the hotspot coverage floor (#11016)."""

from __future__ import annotations


def _build_code_provenance_dict(code_provenance: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "pipeline_version": getattr(code_provenance, "pipeline_version", None),
        "git_commit": getattr(code_provenance, "git_commit", None),
        "dependency_lock_hash": getattr(code_provenance, "dependency_lock_hash", None),
        "config_hash": getattr(code_provenance, "config_hash", None),
        "resolved_config_hash": getattr(code_provenance, "resolved_config_hash", None),
        "effective_config_hash": getattr(
            code_provenance, "effective_config_hash", None
        ),
        "effective_config_artifact_id": getattr(
            code_provenance,
            "effective_config_artifact_id",
            None,
        ),
        "contract_ref": getattr(code_provenance, "contract_ref", None),
        "contract_version": getattr(code_provenance, "contract_version", None),
        "contract_schema_hash": getattr(code_provenance, "contract_schema_hash", None),
        "dq_policy_ref": getattr(code_provenance, "dq_policy_ref", None),
        "rule_bundle_version": getattr(code_provenance, "rule_bundle_version", None),
        "normalization_profile_ref": getattr(
            code_provenance,
            "normalization_profile_ref",
            None,
        ),
        "normalization_profile_version": getattr(
            code_provenance,
            "normalization_profile_version",
            None,
        ),
        "normalization_profile_hash": getattr(
            code_provenance,
            "normalization_profile_hash",
            None,
        ),
        "dq_contract_compatibility_hash": getattr(
            code_provenance,
            "dq_contract_compatibility_hash",
            None,
        ),
    }
    return {key: value for key, value in payload.items() if value is not None}
