"""Manifest schema and contract compatibility evidence builders."""

from __future__ import annotations

from bioetl.application.services.control_plane.evidence.models import EvidenceCheck
from bioetl.domain.control_plane import RunManifest

SUPPORTED_RUN_MANIFEST_SCHEMA_MAJOR = "1"


def build_manifest_checks(manifest: RunManifest) -> tuple[EvidenceCheck, ...]:
    """Validate typed manifest shape, schema compatibility, and contract anchors."""
    schema_major = manifest.schema_version.split(".", maxsplit=1)[0]
    schema_compatible = schema_major == SUPPORTED_RUN_MANIFEST_SCHEMA_MAJOR
    provenance = manifest.code_provenance
    contract_missing = [
        name
        for name in ("contract_ref", "contract_version")
        if not str(getattr(provenance, name) or "").strip()
    ]
    strict_profile = str(
        manifest.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    ).strip()
    if strict_profile in {"replay_ready", "forensic_grade"}:
        contract_missing.extend(
            name
            for name in (
                "contract_schema_hash",
                "dq_policy_ref",
                "rule_bundle_version",
                "effective_config_artifact_id",
            )
            if not str(getattr(provenance, name) or "").strip()
        )
    contract_check = (
        EvidenceCheck(
            "contract_compatibility",
            "ERROR",
            "manifest_contract_anchors_incomplete",
            "Required contract anchors are absent: "
            + ", ".join(sorted(set(contract_missing))),
        )
        if contract_missing
        else EvidenceCheck(
            "contract_compatibility",
            "UNKNOWN",
            "manifest_contract_compatibility_not_verified",
            "Contract anchors are present, but no registry comparison was recorded.",
        )
    )
    return (
        EvidenceCheck(
            "parse",
            "OK",
            "manifest_parse_ok",
            "The manifest store parsed the persisted JSON payload.",
        ),
        EvidenceCheck(
            "schema",
            "OK",
            "manifest_schema_valid",
            "Typed manifest invariants and required identity fields are valid.",
        ),
        EvidenceCheck(
            "schema_version",
            "OK" if schema_compatible else "ERROR",
            (
                "manifest_schema_version_compatible"
                if schema_compatible
                else "manifest_schema_version_incompatible"
            ),
            (
                "Manifest schema major version is supported."
                if schema_compatible
                else "Manifest schema major version is not supported by this runtime."
            ),
        ),
        contract_check,
    )


__all__ = ["SUPPORTED_RUN_MANIFEST_SCHEMA_MAJOR", "build_manifest_checks"]
