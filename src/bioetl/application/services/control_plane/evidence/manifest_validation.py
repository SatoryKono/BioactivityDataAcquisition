"""Manifest schema and contract compatibility evidence builders."""

from __future__ import annotations

from bioetl.application.services.control_plane.evidence.models import EvidenceCheck
from bioetl.domain.control_plane import RunManifest

SUPPORTED_RUN_MANIFEST_SCHEMA_MAJOR = "1"


def build_manifest_checks(manifest: RunManifest) -> tuple[EvidenceCheck, ...]:
    """Validate typed manifest shape, schema compatibility, and contract anchors."""
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
        _schema_version_check(manifest.schema_version),
        _contract_check(_missing_contract_anchors(manifest)),
    )


def _schema_version_check(schema_version: str) -> EvidenceCheck:
    compatible = (
        schema_version.split(".", maxsplit=1)[0] == SUPPORTED_RUN_MANIFEST_SCHEMA_MAJOR
    )
    if compatible:
        return EvidenceCheck(
            "schema_version",
            "OK",
            "manifest_schema_version_compatible",
            "Manifest schema major version is supported.",
        )
    return EvidenceCheck(
        "schema_version",
        "ERROR",
        "manifest_schema_version_incompatible",
        "Manifest schema major version is not supported by this runtime.",
    )


def _missing_contract_anchors(manifest: RunManifest) -> list[str]:
    fields = ["contract_ref", "contract_version"]
    required_profile = str(
        manifest.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    ).strip()
    if required_profile in {"replay_ready", "forensic_grade"}:
        fields.extend(
            (
                "contract_schema_hash",
                "dq_policy_ref",
                "rule_bundle_version",
                "effective_config_artifact_id",
            )
        )
    provenance = manifest.code_provenance
    return [name for name in fields if not str(getattr(provenance, name) or "").strip()]


def _contract_check(missing: list[str]) -> EvidenceCheck:
    if missing:
        return EvidenceCheck(
            "contract_compatibility",
            "ERROR",
            "manifest_contract_anchors_incomplete",
            "Required contract anchors are absent: " + ", ".join(sorted(set(missing))),
        )
    return EvidenceCheck(
        "contract_compatibility",
        "UNKNOWN",
        "manifest_contract_compatibility_not_verified",
        "Contract anchors are present, but no registry comparison was recorded.",
    )


__all__ = ["SUPPORTED_RUN_MANIFEST_SCHEMA_MAJOR", "build_manifest_checks"]
