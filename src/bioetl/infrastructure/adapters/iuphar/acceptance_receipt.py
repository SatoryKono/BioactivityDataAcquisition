"""Acceptance receipt checks for a pinned IUPHAR profile."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from iuphar_target_class.bioetl_input import (
    UNIPROT_PROJECTION_POLICY_V1,
    UNIPROT_PROJECTION_POLICY_V2,
)
from iuphar_target_class.matching import (
    MATCHING_POLICY_ROLE_SEPARATED_V2,
    MATCHING_POLICY_STRICT_ANCHORS_V1,
    profile_qualifies_matching_policy,
)
from iuphar_target_class.policy import PLAN_VERSION

from ._manifest import checked_document, header, referenced_path, require_sha256, text
from .snapshot_loader import load_snapshot_manifest
from .snapshot_models import (
    CLASSIFICATION_SCHEMA_VERSION,
    NORMALIZATION_VERSION,
    OUTPUT_NAMES,
    REQUIRED_ACCEPTANCE_CHECKS,
    LoadedIupharProfile,
    LoadedIupharSnapshot,
)


def validate_acceptance_receipt(
    document: Mapping[str, object], *, snapshot_manifest_sha256: str
) -> None:
    """Require executed, source-bound acceptance; hashes alone are not a waiver."""
    header(document, "bioetl_iuphar_acceptance", versions=(1, 2))
    if (
        document.get("scope") != "offline_target_integration"
        or document.get("status") != "PASS"
    ):
        raise ValueError("IUPHAR reference acceptance has not passed")
    if document.get("snapshot_manifest_sha256") != snapshot_manifest_sha256:
        raise ValueError("acceptance belongs to a different IUPHAR snapshot")
    if document.get("reference_cases_accepted") is not True:
        raise ValueError("independent IUPHAR reference cases are not accepted")
    versions = tuple(
        document.get(key)
        for key in (
            "normalization_version",
            "rules_version",
            "classification_schema_version",
        )
    )
    if versions != (NORMALIZATION_VERSION, PLAN_VERSION, CLASSIFICATION_SCHEMA_VERSION):
        raise ValueError("acceptance versions differ from the executing adapter")
    _executed_checks(document.get("checks"))
    _bound_acceptance_outputs(document)
    if document["schema_version"] == 2:
        from iuphar_target_class.reference_coverage import (
            validate_reference_coverage_receipt,
        )

        validate_reference_coverage_receipt(document)
    text(document, "run_id")
    text(document, "reviewer_reference")


def _executed_checks(checks: object) -> None:
    if not isinstance(checks, dict) or any(
        checks.get(name) != "PASS" for name in REQUIRED_ACCEPTANCE_CHECKS
    ):
        raise ValueError("missing executed IUPHAR acceptance checks")


def _bound_acceptance_outputs(document: Mapping[str, object]) -> None:
    for key in ("stage0_manifest_sha256", "expected_labels_sha256"):
        require_sha256(document.get(key))
    outputs = document.get("output_sha256")
    if not isinstance(outputs, dict) or set(outputs) != OUTPUT_NAMES:
        raise ValueError("acceptance does not bind all six classification outputs")
    for digest in outputs.values():
        require_sha256(digest)


def _optional_policy(document: Mapping[str, object]) -> str:
    """Missing policy is the historical strict-anchor contract."""
    if "matching_policy" not in document or document.get("matching_policy") is None:
        return MATCHING_POLICY_STRICT_ANCHORS_V1
    value = document.get("matching_policy")
    if value not in (
        MATCHING_POLICY_STRICT_ANCHORS_V1,
        MATCHING_POLICY_ROLE_SEPARATED_V2,
    ):
        raise ValueError("unknown IUPHAR matching policy")
    return str(value)


def _load_acceptance(
    document: Mapping[str, object],
    root: Path,
    snapshot: LoadedIupharSnapshot,
    required: bool,
    matching_policy: str,
) -> str | None:
    reference = document.get("acceptance")
    if reference is None:
        if required:
            raise ValueError("enrich requires executed IUPHAR reference acceptance")
        return None
    path, digest = referenced_path(root, reference)
    receipt = checked_document(path, digest)
    if required and receipt.get("schema_version") != 2:
        raise ValueError("new enrich requires bounded reference acceptance schema 2")
    validate_acceptance_receipt(
        receipt, snapshot_manifest_sha256=snapshot.snapshot_manifest_sha256
    )
    if _optional_policy(receipt) != matching_policy:
        raise ValueError(
            "acceptance matching policy differs from the executing profile"
        )
    return digest


def load_profile(
    path: Path, expected_sha256: str, *, require_acceptance: bool = True
) -> LoadedIupharProfile:
    """Resolve the noncircular profile→snapshot+acceptance dependency graph."""
    path = path.resolve()
    document = checked_document(path, expected_sha256)
    header(document, "bioetl_iuphar_profile", versions=(1, 2))
    snapshot_path, snapshot_hash = referenced_path(
        path.parent, document.get("snapshot")
    )
    snapshot = load_snapshot_manifest(snapshot_path, snapshot_hash)
    if require_acceptance and snapshot.manifest.get("schema_version") != 2:
        raise ValueError("new enrich requires source-verified snapshot schema 2")
    if require_acceptance and not (
        snapshot.completeness.complete and snapshot.completeness.publishable
    ):
        raise ValueError("enrich requires a complete, publishable IUPHAR snapshot")
    versions = (
        text(document, "normalization_version"),
        text(document, "rules_version"),
        text(document, "classification_schema_version"),
    )
    if versions != (NORMALIZATION_VERSION, PLAN_VERSION, CLASSIFICATION_SCHEMA_VERSION):
        raise ValueError("IUPHAR profile versions differ from the executing adapter")
    matching_policy = _optional_policy(document)
    profile_hash = require_sha256(expected_sha256)
    if matching_policy == MATCHING_POLICY_ROLE_SEPARATED_V2 and not (
        profile_qualifies_matching_policy(
            profile_name="iuphar.profile",
            profile_version=versions[0],
            profile_hash=profile_hash,
            matching_policy=matching_policy,
        )
    ):
        raise ValueError("IUPHAR profile does not qualify role-separated matching")
    acceptance_hash = _load_acceptance(
        document, path.parent, snapshot, require_acceptance, matching_policy
    )
    projection_policy = (
        UNIPROT_PROJECTION_POLICY_V2
        if matching_policy == MATCHING_POLICY_ROLE_SEPARATED_V2
        else UNIPROT_PROJECTION_POLICY_V1
    )
    return LoadedIupharProfile(
        snapshot,
        profile_hash,
        path.as_uri(),
        acceptance_hash,
        *versions,
        matching_policy,
        projection_policy,
    )
