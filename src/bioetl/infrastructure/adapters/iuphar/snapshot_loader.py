"""Load pinned profiles without treating a caller's completeness flag as proof."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from iuphar_target_class.pipeline import IndexedSnapshot
from iuphar_target_class.policy import PLAN_VERSION
from iuphar_target_class.snapshot import Completeness, assess_completeness

from ._manifest import (
    checked_bytes,
    checked_document,
    header,
    referenced_path,
    require_sha256,
    text,
)
from ._snapshot_payloads import (
    identifier,
    parse_target_payloads,
    parse_target_species_payloads,
)
from .snapshot_builder import SNAPSHOT_FORMAT, verify_snapshot_sources

REQUIRED_ACCEPTANCE_CHECKS = frozenset(
    {
        "stage0_admission",
        "reference_cases",
        "evidence_integrity",
        "semantic_determinism",
        "pipeline_integration",
    }
)
OUTPUT_NAMES = frozenset(
    {
        "classification.json",
        "evidence.json",
        "candidates.json",
        "components.json",
        "diagnostics.json",
        "metrics.json",
    }
)
NORMALIZATION_VERSION = "bioetl-iuphar-input-v1"
CLASSIFICATION_SCHEMA_VERSION = "3.1.0"


@dataclass(frozen=True, slots=True)
class LoadedIupharSnapshot:
    snapshot: IndexedSnapshot
    completeness: Completeness
    snapshot_manifest_sha256: str
    immutable_uri: str
    retrieved_at: str
    species_taxon_ids: frozenset[str]
    manifest: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class LoadedIupharProfile:
    snapshot: LoadedIupharSnapshot
    profile_sha256: str
    profile_uri: str
    acceptance_sha256: str | None
    normalization_version: str
    rules_version: str
    classification_schema_version: str


def _required_strings(document: Mapping[str, object], key: str) -> tuple[str, ...]:
    values = document.get(key)
    if (
        not isinstance(values, list)
        or not values
        or any(not isinstance(item, str) or not item for item in values)
    ):
        raise ValueError(f"expected a nonempty string list: {key}")
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate scope entry: {key}")
    return tuple(values)


def _completeness(
    document: Mapping[str, object],
    snapshot_rows: int,
    actual_types: frozenset[str],
) -> Completeness:
    expected = document.get("expected_target_count")
    if isinstance(expected, bool) or not isinstance(expected, int) or expected <= 0:
        raise ValueError("snapshot needs a positive expected target count")
    required_types = frozenset(_required_strings(document, "required_target_types"))
    return assess_completeness(
        coverage_approved=_has_reference(document, "coverage_approval_reference"),
        required_types_loaded=required_types.issubset(actual_types),
        pagination_complete=document.get("pagination_complete") is True,
        transport_or_schema_errors=False,
        totals_match=expected == snapshot_rows,
        provider_versions=text(document, "provider_versions"),
        version_limitation_recorded=_has_reference(
            document, "version_limitation_reference"
        ),
    )


def _has_reference(document: Mapping[str, object], key: str) -> bool:
    value = document.get(key)
    if value is None:
        return False
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid IUPHAR approval reference: {key}")
    return True


def load_snapshot_manifest(path: Path, expected_sha256: str) -> LoadedIupharSnapshot:
    """Validate bytes, scope and projections before indexing the pinned release."""
    path = path.resolve()
    document = checked_document(path, expected_sha256)
    header(document, "bioetl_iuphar_snapshot", versions=(1, 2))
    if document["schema_version"] == 2:
        return _load_current_snapshot(path, expected_sha256, document)
    if document.get("format") != "gtopdb_target_payload_v1":
        raise ValueError("unsupported frozen target payload format")
    targets_path, targets_hash = referenced_path(path.parent, document.get("targets"))
    catalog, annotations = parse_target_payloads(
        checked_bytes(targets_path, targets_hash)
    )
    species = frozenset(
        identifier(item) for item in _required_strings(document, "species_taxon_ids")
    )
    if any(row.species not in species for row in catalog):
        raise ValueError("provider target lies outside declared snapshot species")
    completeness = _completeness(
        document,
        len(catalog),
        frozenset(
            item.type_raw.strip().lower()
            for item in annotations.values()
            if item.type_raw
        ),
    )
    snapshot = IndexedSnapshot.from_approved_gtopdb(
        snapshot_id=text(document, "snapshot_id"),
        release=text(document, "provider_release"),
        complete=completeness.complete,
        catalog=catalog,
        annotations=annotations,
    )
    return LoadedIupharSnapshot(
        snapshot,
        completeness,
        require_sha256(expected_sha256),
        path.as_uri(),
        text(document, "retrieved_at"),
        species,
        MappingProxyType(document),
    )


def _load_current_snapshot(
    path: Path, expected_sha256: str, document: Mapping[str, object]
) -> LoadedIupharSnapshot:
    if document.get("format") != SNAPSHOT_FORMAT:
        raise ValueError("unsupported source-verified snapshot format")
    targets_path, targets_hash = referenced_path(path.parent, document.get("targets"))
    raw = checked_bytes(targets_path, targets_hash)
    evidence, projection = verify_snapshot_sources(document, path.parent, raw)
    audit_path, audit_hash = referenced_path(
        path.parent, document.get("projection_audit")
    )
    if checked_bytes(audit_path, audit_hash) != projection.audit:
        raise ValueError("snapshot projection audit differs from source accounting")
    catalog, annotations = parse_target_species_payloads(raw)
    completeness = Completeness(
        True,
        True,
        False,
        projection.allows_not_found,
        "verified reviewed family-only scope; global absence "
        + ("covered" if projection.allows_not_found else "not established"),
    )
    snapshot = IndexedSnapshot.from_approved_gtopdb(
        snapshot_id=text(document, "snapshot_id"),
        release=evidence.provider_release,
        complete=completeness.allows_not_found,
        admission_complete=completeness.complete,
        catalog=catalog,
        annotations={},
        species_annotations=annotations,
    )
    return LoadedIupharSnapshot(
        snapshot,
        completeness,
        require_sha256(expected_sha256),
        path.as_uri(),
        evidence.retrieved_at,
        frozenset(
            identifier(value)
            for value in _required_strings(evidence.scope, "species_taxon_ids")
        ),
        MappingProxyType(dict(document)),
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


def _load_acceptance(
    document: Mapping[str, object],
    root: Path,
    snapshot: LoadedIupharSnapshot,
    required: bool,
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
    acceptance_hash = _load_acceptance(
        document, path.parent, snapshot, require_acceptance
    )
    versions = (
        text(document, "normalization_version"),
        text(document, "rules_version"),
        text(document, "classification_schema_version"),
    )
    if versions != (NORMALIZATION_VERSION, PLAN_VERSION, CLASSIFICATION_SCHEMA_VERSION):
        raise ValueError("IUPHAR profile versions differ from the executing adapter")
    return LoadedIupharProfile(
        snapshot,
        require_sha256(expected_sha256),
        path.as_uri(),
        acceptance_hash,
        *versions,
    )


__all__ = [
    "OUTPUT_NAMES",
    "REQUIRED_ACCEPTANCE_CHECKS",
    "LoadedIupharProfile",
    "LoadedIupharSnapshot",
    "load_profile",
    "load_snapshot_manifest",
    "parse_target_payloads",
    "validate_acceptance_receipt",
]
