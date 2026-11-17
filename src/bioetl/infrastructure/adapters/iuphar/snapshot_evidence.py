"""Verify acquisition bytes and independently reviewed snapshot scope."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import cast
from urllib.parse import urlsplit

from iuphar_target_class.iuphar_mapping import require_mapping_release
from iuphar_target_class.stage0.io import canonical_json_bytes

from ._manifest import (
    checked_bytes,
    header,
    object_document,
    referenced_path,
    require_sha256,
    sha256,
    text,
)
from ._snapshot_payloads import identifier


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """Only verified source bytes and a reviewer-bound coverage declaration."""

    acquisition_bytes: bytes
    acquisition_sha256: str
    coverage_bytes: bytes
    coverage_sha256: str
    source_format: str
    provider_release: str
    retrieved_at: str
    scope: Mapping[str, object]
    raw_artifacts: Mapping[str, bytes]
    acquisition_files: Mapping[str, bytes]
    coverage_files: Mapping[str, bytes]


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("snapshot evidence object required")
    return cast("dict[str, object]", value)


def _positive(value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError("snapshot evidence needs a positive count")
    return value


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("snapshot scope needs a nonempty string list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("snapshot scope contains an invalid string")
    items = cast("list[str]", value)
    if len(items) != len(set(items)):
        raise ValueError("duplicate snapshot scope value")
    return tuple(items)


def _canonical_identifiers(value: object) -> list[str]:
    identifiers: list[str] = []
    for item in _strings(value):
        if not item.isascii() or not item.isdecimal() or item.startswith("0"):
            raise ValueError("invalid provider target or taxonomy identifier")
        identifiers.append(item)
    return identifiers


def _scope(value: object) -> dict[str, object]:
    scope = _mapping(value)
    if set(scope) != {
        "species_taxon_ids",
        "required_family_types",
        "included_target_ids",
        "excluded_targets",
        "selection_basis",
        "expected_raw_row_count",
        "expected_provider_target_count",
        "expected_variant_count",
    }:
        raise ValueError("unsupported snapshot coverage scope")
    species = _canonical_identifiers(scope["species_taxon_ids"])
    types = _strings(scope["required_family_types"])
    if any(value != value.strip().lower() for value in types):
        raise ValueError("snapshot scope types must use canonical provider tokens")
    for key in (
        "expected_raw_row_count",
        "expected_provider_target_count",
        "expected_variant_count",
    ):
        _positive(scope[key])
    if scope["selection_basis"] != "reviewed_single_protein_targets":
        raise ValueError(
            "snapshot requires independently reviewed single-protein selection"
        )
    identifiers = _canonical_identifiers(scope["included_target_ids"])
    _excluded_targets(scope["excluded_targets"])
    return {
        **scope,
        "species_taxon_ids": species,
        "required_family_types": list(types),
        "included_target_ids": identifiers,
    }


def _excluded_targets(value: object) -> None:
    if not isinstance(value, list):
        raise ValueError("snapshot exclusions must be an explicit list")
    seen: set[str] = set()
    for item in value:
        entry = _mapping(item)
        target = identifier(entry.get("target_id"))
        text(entry, "rationale")
        records = entry.get("source_records")
        if not isinstance(records, list) or not records:
            raise ValueError("snapshot exclusion needs every source record")
        counts = [_positive(record) for record in records]
        if target in seen or len(counts) != len(set(counts)):
            raise ValueError("duplicate snapshot exclusion identity")
        seen.add(target)


def _retrieved_at(document: Mapping[str, object]) -> str:
    value = text(document, "retrieved_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("invalid acquisition retrieval timestamp") from error
    if parsed.utcoffset() is None:
        raise ValueError("acquisition retrieval timestamp needs a timezone")
    return value


def _raw_parts(
    document: Mapping[str, object], root: Path
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    parts = _mapping(document.get("raw_artifacts"))
    if not parts:
        raise ValueError("acquisition has no raw provider artifacts")
    raw: dict[str, bytes] = {}
    files: dict[str, bytes] = {}
    for role, value in parts.items():
        reference = _mapping(value)
        path, digest = referenced_path(root, reference)
        payload = checked_bytes(path, digest)
        if _positive(reference.get("byte_count")) != len(payload):
            raise ValueError("acquisition raw byte count differs")
        url = urlsplit(text(reference, "source_url"))
        if url.scheme != "https" or not url.netloc or url.username or url.password:
            raise ValueError("acquisition needs a credential-free HTTPS source URL")
        relative = Path(text(reference, "path")).as_posix()
        if relative in files and files[relative] != payload:
            raise ValueError("conflicting acquisition source path")
        raw[role] = payload
        files[relative] = payload
    return raw, files


def _review(
    coverage: Mapping[str, object],
    root: Path,
    acquisition_hash: str,
    scope: Mapping[str, object],
) -> dict[str, bytes]:
    reference = _mapping(coverage.get("review"))
    path, digest = referenced_path(root, reference)
    raw = checked_bytes(path, digest)
    review = object_document(raw)
    header(review, "bioetl_iuphar_scope_review")
    text(review, "reviewer_reference")
    text(review, "approval_reference")
    if require_sha256(review.get("acquisition_sha256")) != acquisition_hash:
        raise ValueError("coverage review belongs to another acquisition")
    if require_sha256(review.get("scope_sha256")) != sha256(
        canonical_json_bytes(scope)
    ):
        raise ValueError("coverage review belongs to another scope")
    files = {Path(text(reference, "path")).as_posix(): raw}
    references = review.get("evidence_references", [])
    if not isinstance(references, list):
        raise ValueError("scope review evidence must use typed artifact references")
    for item in references:
        evidence_path, evidence_hash = referenced_path(root, item)
        content = checked_bytes(evidence_path, evidence_hash)
        relative = evidence_path.relative_to(root.resolve()).as_posix()
        if relative in files and files[relative] != content:
            raise ValueError("conflicting scope review evidence path")
        files[relative] = content
    return files


def load_source_evidence(
    acquisition: Path, acquisition_sha256: str, coverage: Path, coverage_sha256: str
) -> SourceEvidence:
    """Require hash-checked raw artifacts and a separately pinned scope review."""
    acquisition_raw = checked_bytes(acquisition, acquisition_sha256)
    coverage_raw = checked_bytes(coverage, coverage_sha256)
    acquired = object_document(acquisition_raw)
    covered = object_document(coverage_raw)
    header(acquired, "bioetl_iuphar_acquisition")
    header(covered, "bioetl_iuphar_coverage")
    if require_sha256(covered.get("acquisition_sha256")) != acquisition_sha256:
        raise ValueError("snapshot coverage belongs to another acquisition")
    release = text(acquired, "provider_release")
    require_mapping_release(release)
    scope = _scope(covered.get("scope"))
    raw, files = _raw_parts(acquired, acquisition.parent)
    review_files = _review(covered, coverage.parent, acquisition_sha256, scope)
    return SourceEvidence(
        acquisition_raw,
        require_sha256(acquisition_sha256),
        coverage_raw,
        require_sha256(coverage_sha256),
        text(acquired, "source_format"),
        release,
        _retrieved_at(acquired),
        MappingProxyType(scope),
        MappingProxyType(raw),
        MappingProxyType(files),
        MappingProxyType(review_files),
    )
