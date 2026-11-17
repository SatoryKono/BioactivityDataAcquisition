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
from .snapshot_payload import SNAPSHOT_FORMAT, verify_snapshot_sources

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


from .acceptance_receipt import load_profile, validate_acceptance_receipt


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
