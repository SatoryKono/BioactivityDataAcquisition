"""Manifest schema and contract compatibility evidence builders."""

from __future__ import annotations

from bioetl.application.observability.control_plane_evidence.checks import (
    EvidenceCheckResult,
)
from bioetl.application.observability.control_plane_evidence.persistence_profile import (
    STRICT_PERSISTENCE_PROFILES,
    resolve_persistence_profile,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.ports import RawManifestInspection

SUPPORTED_RUN_MANIFEST_SCHEMA_MAJOR = "1"


def build_manifest_checks(
    manifest: RunManifest,
    inspection: RawManifestInspection | None = None,
) -> tuple[EvidenceCheckResult, ...]:
    """Validate typed manifest shape, schema compatibility, and contract anchors."""
    return (
        *_raw_manifest_checks(inspection),
        _schema_version_check(manifest.schema_version),
        _persistence_profile_check(manifest),
        _contract_check(_missing_contract_anchors(manifest), inspection),
        _optional_anchor_check(
            check="resume_contract",
            value=None if inspection is None else inspection.resume_contract,
            reason_value=None if inspection is None else inspection.resume_contract_reason,
            missing_reason="resume_contract_not_recorded",
            missing_detail="Resume contract is absent without an explicit N/A reason.",
            ok_reason="resume_contract_recorded",
            ok_detail="Resume contract has a recorded value or explicit N/A reason.",
        ),
        _optional_anchor_check(
            check="lock_owner_id",
            value=None if inspection is None else inspection.lock_owner_id,
            reason_value=None if inspection is None else inspection.lock_owner_reason,
            missing_reason="lock_owner_id_not_recorded",
            missing_detail="Lock owner is absent without an explicit N/A reason.",
            ok_reason="lock_owner_id_recorded",
            ok_detail="Lock owner has a recorded value or explicit N/A reason.",
        ),
    )


def _raw_manifest_checks(
    inspection: RawManifestInspection | None,
) -> tuple[EvidenceCheckResult, ...]:
    if inspection is None:
        return (
            EvidenceCheckResult(
                "parse",
                "UNKNOWN",
                "manifest_raw_inspection_unavailable",
                "The persisted raw manifest payload was not inspected.",
            ),
            EvidenceCheckResult(
                "schema",
                "UNKNOWN",
                "manifest_raw_schema_not_verified",
                "Raw manifest schema compatibility was not verified.",
            ),
        )
    if not inspection.parse_ok:
        reason = (
            inspection.schema_errors[0]
            if inspection.schema_errors
            else "manifest_parse_error"
        )
        return (
            EvidenceCheckResult(
                "parse",
                "ERROR",
                reason,
                "The persisted manifest payload could not be parsed.",
            ),
            EvidenceCheckResult(
                "schema",
                "UNKNOWN",
                "manifest_raw_schema_not_observable",
                "Raw schema validation requires a parsed manifest object.",
            ),
        )
    if not inspection.schema_errors:
        return (
            EvidenceCheckResult(
                "parse",
                "OK",
                "manifest_parse_ok",
                "The persisted manifest contains a JSON object.",
            ),
            EvidenceCheckResult(
                "schema",
                "OK",
                "manifest_schema_valid",
                "The raw manifest satisfies the supported persisted schema.",
            ),
        )
    schema_checks = tuple(
        EvidenceCheckResult(
            "schema",
            "ERROR",
            reason,
            "A persisted manifest field violates its bounded raw-schema contract.",
        )
        for reason in inspection.schema_errors[:12]
    )
    return (
        EvidenceCheckResult(
            "parse",
            "OK",
            "manifest_parse_ok",
            "The persisted manifest contains a JSON object.",
        ),
        *schema_checks,
        *(
            (
                EvidenceCheckResult(
                    "schema",
                    "ERROR",
                    "manifest_raw_schema_additional_errors",
                    "Additional bounded raw-schema violations were omitted.",
                ),
            )
            if len(inspection.schema_errors) > 12
            else ()
        ),
    )


def _schema_version_check(schema_version: str) -> EvidenceCheckResult:
    compatible = (
        schema_version.split(".", maxsplit=1)[0] == SUPPORTED_RUN_MANIFEST_SCHEMA_MAJOR
    )
    if compatible:
        return EvidenceCheckResult(
            "schema_version",
            "OK",
            "manifest_schema_version_compatible",
            "Manifest schema major version is supported.",
        )
    return EvidenceCheckResult(
        "schema_version",
        "ERROR",
        "manifest_schema_version_incompatible",
        "Manifest schema major version is not supported by this runtime.",
    )


def _missing_contract_anchors(manifest: RunManifest) -> list[str]:
    fields = ["contract_ref", "contract_version"]
    required_profile, profile_valid = resolve_persistence_profile(manifest)
    if not profile_valid or required_profile in STRICT_PERSISTENCE_PROFILES:
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


def _persistence_profile_check(manifest: RunManifest) -> EvidenceCheckResult:
    _, profile_valid = resolve_persistence_profile(manifest)
    if profile_valid:
        return EvidenceCheckResult(
            "persistence_profile",
            "OK",
            "manifest_persistence_profile_supported",
            "The required persistence profile belongs to the supported vocabulary.",
        )
    return EvidenceCheckResult(
        "persistence_profile",
        "ERROR",
        "manifest_persistence_profile_unsupported",
        "The required persistence profile is outside the supported vocabulary.",
    )


def _contract_check(
    missing: list[str],
    inspection: RawManifestInspection | None,
) -> EvidenceCheckResult:
    if missing:
        return EvidenceCheckResult(
            "contract_compatibility",
            "ERROR",
            "manifest_contract_anchors_incomplete",
            "Required contract anchors are absent: " + ", ".join(sorted(set(missing))),
        )
    comparison = (
        None if inspection is None else inspection.contract_comparison_status
    )
    comparison_reason = (
        None if inspection is None else inspection.contract_comparison_reason
    )
    if comparison == "compatible":
        return EvidenceCheckResult(
            "contract_compatibility",
            "OK",
            comparison_reason or "manifest_contract_comparison_compatible",
            "An immutable registry comparison recorded a compatible result.",
        )
    if comparison == "incompatible":
        return EvidenceCheckResult(
            "contract_compatibility",
            "ERROR",
            comparison_reason or "manifest_contract_comparison_incompatible",
            "An immutable registry comparison recorded an incompatible result.",
        )
    return EvidenceCheckResult(
        "contract_compatibility",
        "UNKNOWN",
        "manifest_contract_compatibility_not_verified",
        "Contract anchors are present, but no registry comparison was recorded.",
    )


def _optional_anchor_check(
    *,
    check: str,
    value: str | None,
    reason_value: str | None,
    missing_reason: str,
    missing_detail: str,
    ok_reason: str,
    ok_detail: str,
) -> EvidenceCheckResult:
    if value and value.strip():
        return EvidenceCheckResult(check, "OK", ok_reason, ok_detail)
    if reason_value and reason_value.strip():
        return EvidenceCheckResult(check, "OK", reason_value.strip(), ok_detail)
    return EvidenceCheckResult(check, "UNKNOWN", missing_reason, missing_detail)


__all__ = ["SUPPORTED_RUN_MANIFEST_SCHEMA_MAJOR", "build_manifest_checks"]
