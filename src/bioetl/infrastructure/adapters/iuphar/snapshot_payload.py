"""Deterministic offline publication of a source-verified species snapshot."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from iuphar_target_class.identifier_roles import (
    ANCHOR_PRIORITY_POLICIES,
    MATCHING_POLICY_VERSION,
    REVIEWED_CLASS_POLICY_VERSION,
)
from iuphar_target_class.policy import LOCAL_CATALOG_VERSION
from iuphar_target_class.stage0.io import canonical_json_bytes

from ._manifest import checked_bytes, referenced_path, sha256
from ._official_target_projection import project_official_export
from ._official_targets_csv import OfficialProjection
from .snapshot_evidence import SourceEvidence, load_source_evidence
from .snapshot_reviewed_inputs import parse_reviewed_inputs

SNAPSHOT_FORMAT = "gtopdb_target_species_payload_v2"
_SNAPSHOT_JSON = "snapshot.json"


@dataclass(frozen=True, slots=True)
class SnapshotBundle:
    files: Mapping[str, bytes]
    snapshot_sha256: str
    profile_sha256: str


def _reference(path: str, payload: bytes) -> dict[str, str]:
    return {"path": path, "sha256": sha256(payload)}


def _source_files(evidence: SourceEvidence) -> dict[str, bytes]:
    files = {
        "sources/acquisition/acquisition.json": evidence.acquisition_bytes,
        "sources/coverage/coverage.json": evidence.coverage_bytes,
    }
    for directory, sources in (
        ("sources/acquisition", evidence.acquisition_files),
        ("sources/coverage", evidence.coverage_files),
    ):
        for relative, payload in sources.items():
            name = directory + "/" + relative
            if name in files:
                raise ValueError("source receipt path collides with a raw artifact")
            files[name] = payload
    return files


def compile_snapshot_bundle(
    evidence: SourceEvidence,
    *,
    matching_policy_version: str = MATCHING_POLICY_VERSION,
    reviewed_inputs: bytes | None = None,
    supplemental_csvs: Mapping[str, bytes] | None = None,
) -> SnapshotBundle:
    """Derive every target/audit byte from verified raw acquisition and scope."""
    if matching_policy_version not in {
        MATCHING_POLICY_VERSION,
        *ANCHOR_PRIORITY_POLICIES,
    }:
        raise ValueError("unsupported IUPHAR matching policy")
    projection = project_official_export(evidence)
    files = _source_files(evidence)
    files.update(
        {"targets.json": projection.targets, "projection-audit.json": projection.audit}
    )
    reviewed_sources = dict(supplemental_csvs or {})
    if reviewed_inputs is not None:
        if matching_policy_version != REVIEWED_CLASS_POLICY_VERSION:
            raise ValueError("reviewed inputs require the reviewed matching policy")
        review = parse_reviewed_inputs(reviewed_inputs)
        if {
            name: sha256(raw) for name, raw in reviewed_sources.items()
        } != review.source_hashes:
            raise ValueError(
                "supplemental CSV bytes differ from reviewed source digests"
            )
        files["reviewed-inputs.json"] = reviewed_inputs
    elif reviewed_sources:
        raise ValueError("supplemental CSVs require reviewed inputs")
    identity = _snapshot_identity(evidence, projection.targets, reviewed_inputs)
    snapshot = {
        "artifact": "bioetl_iuphar_snapshot",
        "schema_version": 2,
        "format": SNAPSHOT_FORMAT,
        "annotation_capability": "family_only",
        "snapshot_id": "gtopdb:" + evidence.provider_release + ":" + identity,
        "provider_release": evidence.provider_release,
        "retrieved_at": evidence.retrieved_at,
        "targets": _reference("targets.json", projection.targets),
        "projection_audit": _reference("projection-audit.json", projection.audit),
        "acquisition": _reference(
            "sources/acquisition/acquisition.json", evidence.acquisition_bytes
        ),
        "coverage": _reference(
            "sources/coverage/coverage.json", evidence.coverage_bytes
        ),
    }
    if reviewed_inputs is not None:
        snapshot["reviewed_inputs"] = _reference(
            "reviewed-inputs.json", reviewed_inputs
        )
        if reviewed_sources:
            references = {}
            for name, raw in sorted(reviewed_sources.items()):
                path = f"sources/reviewed/{name}"
                files[path] = raw
                references[name] = _reference(path, raw)
            snapshot["supplemental_csvs"] = references
    files[_SNAPSHOT_JSON] = canonical_json_bytes(snapshot)
    profile = {
        "artifact": "bioetl_iuphar_profile",
        "schema_version": 2,
        "snapshot": _reference(_SNAPSHOT_JSON, files[_SNAPSHOT_JSON]),
        "acceptance": None,
        "normalization_version": "bioetl-iuphar-input-v1",
        "rules_version": LOCAL_CATALOG_VERSION,
        "classification_schema_version": "3.1.0",
        "matching_policy_version": matching_policy_version,
    }
    files["profile.json"] = canonical_json_bytes(profile)
    return SnapshotBundle(
        MappingProxyType(files),
        sha256(files[_SNAPSHOT_JSON]),
        sha256(files["profile.json"]),
    )


def verify_snapshot_sources(
    document: Mapping[str, object], root: Path, targets: bytes
) -> tuple[SourceEvidence, OfficialProjection, bytes | None]:
    """Recompute published projections; manifest flags cannot establish admission."""
    acquisition, acquisition_hash = referenced_path(root, document.get("acquisition"))
    coverage, coverage_hash = referenced_path(root, document.get("coverage"))
    evidence = load_source_evidence(
        acquisition, acquisition_hash, coverage, coverage_hash
    )
    projection = project_official_export(evidence)
    if targets != projection.targets:
        raise ValueError(
            "snapshot targets differ from the verified official source projection"
        )
    if (
        document.get("provider_release") != evidence.provider_release
        or document.get("retrieved_at") != evidence.retrieved_at
    ):
        raise ValueError(
            "snapshot release or timestamp differs from acquisition evidence"
        )
    if document.get("annotation_capability") != "family_only":
        raise ValueError("snapshot claims unsupported direct target-type capability")
    reviewed_inputs = None
    if "reviewed_inputs" in document:
        review, review_hash = referenced_path(root, document["reviewed_inputs"])
        reviewed_inputs = checked_bytes(review, review_hash)
        _verify_supplemental_files(document, root, reviewed_inputs)
    identity = _snapshot_identity(evidence, projection.targets, reviewed_inputs)
    if (
        document.get("snapshot_id")
        != "gtopdb:" + evidence.provider_release + ":" + identity
    ):
        raise ValueError("snapshot identity differs from source-derived bytes")
    return evidence, projection, reviewed_inputs


def _verify_supplemental_files(
    document: Mapping[str, object], root: Path, reviewed_inputs: bytes
) -> None:
    references = document.get("supplemental_csvs", {})
    hashes = parse_reviewed_inputs(reviewed_inputs).source_hashes
    if not isinstance(references, Mapping) or references.keys() != hashes.keys():
        raise ValueError("snapshot supplemental CSV manifest differs from review")
    for name, expected_hash in hashes.items():
        path, digest = referenced_path(root, references[name])
        if digest != expected_hash:
            raise ValueError("snapshot supplemental CSV digest differs from review")
        checked_bytes(path, digest)


def _snapshot_identity(
    evidence: SourceEvidence, targets: bytes, reviewed_inputs: bytes | None
) -> str:
    source_bytes = evidence.acquisition_bytes + evidence.coverage_bytes + targets
    if reviewed_inputs is not None:
        source_bytes += b"\x00reviewed-inputs\x00" + bytes.fromhex(
            sha256(reviewed_inputs)
        )
    return sha256(source_bytes)


def build_snapshot_bundle(
    *,
    acquisition: Path,
    acquisition_sha256: str,
    coverage: Path,
    coverage_sha256: str,
    output_dir: Path,
    matching_policy_version: str = MATCHING_POLICY_VERSION,
    reviewed_inputs: Path | None = None,
    reviewed_inputs_sha256: str | None = None,
    supplemental_csv_dir: Path | None = None,
) -> SnapshotBundle:
    """Write a new immutable bundle only after all input/source checks succeed."""
    evidence = load_source_evidence(
        acquisition, acquisition_sha256, coverage, coverage_sha256
    )
    if (reviewed_inputs is None) != (reviewed_inputs_sha256 is None):
        raise ValueError("reviewed inputs require a path and SHA-256")
    review = (
        checked_bytes(reviewed_inputs, reviewed_inputs_sha256)
        if reviewed_inputs is not None and reviewed_inputs_sha256 is not None
        else None
    )
    if review is None and supplemental_csv_dir is not None:
        raise ValueError("supplemental CSV directory requires reviewed inputs")
    sources = (
        {
            name: checked_bytes(supplemental_csv_dir / name, digest)
            for name, digest in parse_reviewed_inputs(review).source_hashes.items()
        }
        if review is not None and supplemental_csv_dir is not None
        else None
    )
    bundle = compile_snapshot_bundle(
        evidence,
        matching_policy_version=matching_policy_version,
        reviewed_inputs=review,
        supplemental_csvs=sources,
    )
    output = output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for relative, content in sorted(bundle.files.items()):
        destination = output / relative
        if not destination.resolve().is_relative_to(output):
            raise ValueError("snapshot output escapes the bundle directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(content)
    return bundle
