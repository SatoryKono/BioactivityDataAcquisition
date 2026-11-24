"""Deterministic offline publication of a source-verified species snapshot."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from iuphar_target_class.policy import LOCAL_CATALOG_VERSION
from iuphar_target_class.stage0.io import canonical_json_bytes

from ._manifest import referenced_path, sha256
from ._official_target_projection import project_official_export
from ._official_targets_csv import OfficialProjection
from .snapshot_evidence import SourceEvidence, load_source_evidence

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


def compile_snapshot_bundle(evidence: SourceEvidence) -> SnapshotBundle:
    """Derive every target/audit byte from verified raw acquisition and scope."""
    projection = project_official_export(evidence)
    files = _source_files(evidence)
    files.update(
        {"targets.json": projection.targets, "projection-audit.json": projection.audit}
    )
    identity = sha256(
        evidence.acquisition_bytes + evidence.coverage_bytes + projection.targets
    )
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
    files[_SNAPSHOT_JSON] = canonical_json_bytes(snapshot)
    from iuphar_target_class.identifier_roles import MATCHING_POLICY_VERSION

    profile = {
        "artifact": "bioetl_iuphar_profile",
        "schema_version": 2,
        "snapshot": _reference(_SNAPSHOT_JSON, files[_SNAPSHOT_JSON]),
        "acceptance": None,
        "normalization_version": "bioetl-iuphar-input-v1",
        "rules_version": LOCAL_CATALOG_VERSION,
        "classification_schema_version": "3.1.0",
        "matching_policy_version": MATCHING_POLICY_VERSION,
    }
    files["profile.json"] = canonical_json_bytes(profile)
    return SnapshotBundle(
        MappingProxyType(files),
        sha256(files[_SNAPSHOT_JSON]),
        sha256(files["profile.json"]),
    )


def verify_snapshot_sources(
    document: Mapping[str, object], root: Path, targets: bytes
) -> tuple[SourceEvidence, OfficialProjection]:
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
    identity = sha256(
        evidence.acquisition_bytes + evidence.coverage_bytes + projection.targets
    )
    if (
        document.get("snapshot_id")
        != "gtopdb:" + evidence.provider_release + ":" + identity
    ):
        raise ValueError("snapshot identity differs from source-derived bytes")
    return evidence, projection


def build_snapshot_bundle(
    *,
    acquisition: Path,
    acquisition_sha256: str,
    coverage: Path,
    coverage_sha256: str,
    output_dir: Path,
) -> SnapshotBundle:
    """Write a new immutable bundle only after all input/source checks succeed."""
    evidence = load_source_evidence(
        acquisition, acquisition_sha256, coverage, coverage_sha256
    )
    bundle = compile_snapshot_bundle(evidence)
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
