"""Acceptance receipt checks for a pinned IUPHAR profile."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from iuphar_target_class.policy import LOCAL_RULE_CATALOG_VERSION, PLAN_VERSION

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

_ADMITTED_PROFILE_VERSIONS = frozenset(
    {
        (NORMALIZATION_VERSION, PLAN_VERSION, CLASSIFICATION_SCHEMA_VERSION),
        (NORMALIZATION_VERSION, LOCAL_RULE_CATALOG_VERSION, "3.2.0"),
    }
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
    if versions not in _ADMITTED_PROFILE_VERSIONS:
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


def _load_acceptance(
    document: Mapping[str, object],
    root: Path,
    snapshot: LoadedIupharSnapshot,
    required: bool,
) -> tuple[str, tuple[str, str, str]] | None:
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
    versions = (
        text(receipt, "normalization_version"),
        text(receipt, "rules_version"),
        text(receipt, "classification_schema_version"),
    )
    return digest, versions


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
    loaded_acceptance = _load_acceptance(
        document, path.parent, snapshot, require_acceptance
    )
    versions = (
        text(document, "normalization_version"),
        text(document, "rules_version"),
        text(document, "classification_schema_version"),
    )
    if versions not in _ADMITTED_PROFILE_VERSIONS:
        raise ValueError("IUPHAR profile versions differ from the executing adapter")
    acceptance_hash = None
    if loaded_acceptance is not None:
        acceptance_hash, receipt_versions = loaded_acceptance
        if receipt_versions != versions:
            raise ValueError(
                "acceptance versions differ from the selected IUPHAR profile"
            )
    return LoadedIupharProfile(
        snapshot,
        require_sha256(expected_sha256),
        path.as_uri(),
        acceptance_hash,
        *versions,
    )
