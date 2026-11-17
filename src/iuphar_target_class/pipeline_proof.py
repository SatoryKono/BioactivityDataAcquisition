"""Verify actual row-store completion and the matching pipeline run report."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from ._pipeline_proof_rows import (
    OUTPUT_NAMES,
    document,
    mapping,
    require_values,
    validate_row_outputs,
    version_identity,
)
from .models import RunProvenance
from .stage0.io import sha256_bytes


def _digest(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("invalid pipeline proof SHA256")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing pipeline proof identity")
    return value


def _artifact(root: Path, relative: str, digest: object) -> bytes:
    part = PurePosixPath(relative)
    if (
        part.is_absolute()
        or str(part) != relative
        or ".." in part.parts
        or "\\" in relative
    ):
        raise ValueError("integration artifact escapes proof root")
    target = (root / relative).resolve(strict=True)
    if not target.is_relative_to(root.resolve()) or target == root.resolve():
        raise ValueError("integration artifact escapes proof root")
    content = target.read_bytes()
    if sha256_bytes(content) != _digest(digest):
        raise ValueError("integration artifact digest mismatch")
    return content


def _require_occurrence(
    proof: Mapping[str, object], snapshot: str, provenance: RunProvenance
) -> tuple[str, str, set[str]]:
    require_values(
        proof,
        {
            "artifact": "bioetl_iuphar_pipeline_evidence",
            "pipeline_name": "chembl_target",
            "status": "complete",
            "snapshot_manifest_sha256": _digest(snapshot),
            **version_identity(provenance),
        },
    )
    if type(proof.get("schema_version")) is not int or proof["schema_version"] != 1:
        raise ValueError("unsupported pipeline evidence schema")
    if proof.get("mode") not in {"shadow", "enrich"}:
        raise ValueError("missing actual target integration mode")
    ids = proof.get("input_row_ids")
    if not isinstance(ids, list) or not ids:
        raise ValueError("pipeline proof lacks input row identities")
    rows = {_text(value) for value in ids}
    if (
        len(rows) != len(ids)
        or type(proof.get("row_count")) is not int
        or proof["row_count"] != len(rows)
    ):
        raise ValueError("pipeline proof row count or identities differ")
    return _text(proof.get("run_id")), _digest(proof.get("profile_sha256")), rows


def _load_artifacts(root: Path, proof: Mapping[str, object]) -> dict[str, bytes]:
    hashes = mapping(proof.get("artifact_sha256"))
    if not hashes:
        raise ValueError("integration proof lacks output bytes")
    return {name: _artifact(root, name, digest) for name, digest in hashes.items()}


def _row_outputs(
    path: str, manifest: Mapping[str, object], artifacts: Mapping[str, bytes]
) -> tuple[dict[str, bytes], set[str]]:
    parts = PurePosixPath(path).parts
    if len(parts) != 5 or parts[0] != "batches" or parts[2] != "rows":
        raise ValueError("pipeline row manifest has an invalid store path")
    row_id = _text(manifest.get("input_row_id"))
    if parts[3] != hashlib.sha256(row_id.encode()).hexdigest():
        raise ValueError("pipeline row identity differs from its store key")
    hashes = mapping(manifest.get("artifact_sha256"))
    if set(hashes) != OUTPUT_NAMES:
        raise ValueError("pipeline row needs all six output artifacts")
    outputs: dict[str, bytes] = {}
    names = {path}
    for name, digest in hashes.items():
        relative = str(PurePosixPath(path).parent / name)
        raw = artifacts.get(relative)
        if raw is None or sha256_bytes(raw) != _digest(digest):
            raise ValueError("pipeline row output is missing or changed")
        outputs[name] = raw
        names.add(relative)
    return outputs, names


def _verify_rows(
    artifacts: Mapping[str, bytes],
    *,
    rows: set[str],
    run_id: str,
    profile: str,
    provenance: RunProvenance,
) -> None:
    found: dict[str, dict[str, bytes]] = {}
    covered: set[str] = set()
    for path, content in artifacts.items():
        if PurePosixPath(path).name != "row-manifest.json":
            continue
        manifest = document(content)
        require_values(manifest, {"run_id": run_id, "profile_sha256": profile})
        row_id = _text(manifest.get("input_row_id"))
        outputs, names = _row_outputs(path, manifest, artifacts)
        validate_row_outputs(
            outputs, row_id=row_id, run_id=run_id, provenance=provenance
        )
        if row_id in found and found[row_id] != outputs:
            raise ValueError("conflicting duplicate pipeline evidence row")
        found[row_id] = outputs
        covered.update(names)
    if set(found) != rows or covered != set(artifacts):
        raise ValueError("pipeline proof outputs do not cover exactly its claimed rows")


def _report_content(
    root: Path, proof: Mapping[str, object], external: Path | None
) -> bytes:
    reference = proof.get("pipeline_report")
    embedded = None
    if reference is not None:
        item = mapping(reference)
        embedded = _artifact(root, _text(item.get("path")), item.get("sha256"))
    raw = external.read_bytes() if external is not None else embedded
    if raw is None or (embedded is not None and raw != embedded):
        raise ValueError("integration proof lacks its matching pipeline report")
    return raw


def _check_report(
    report: Mapping[str, object],
    proof: Mapping[str, object],
    proof_path: Path,
    proof_hash: str,
) -> None:
    if report.get("schema_version") not in {
        "pipeline_run_report_v1",
        "pipeline_run_report_v2",
    }:
        raise ValueError("unsupported pipeline run report schema")
    identity = mapping(report.get("identity"))
    require_values(identity, {"run_id": proof["run_id"], "status": "success"})
    if (identity.get("pipeline") or identity.get("pipeline_name")) != "chembl_target":
        raise ValueError("integration proof belongs to another pipeline")
    observations = mapping(report.get("observations"))
    observation = mapping(observations.get("Target Classification"))
    require_values(
        observation,
        {"verdict": "OK", "reason": "verified_target_classification_evidence"},
    )
    facts = mapping(observation.get("facts"))
    if type(facts.get("row_count")) is not int:
        raise ValueError("pipeline report classification row count is invalid")
    keys = (
        "run_id",
        "mode",
        "snapshot_manifest_sha256",
        "profile_sha256",
        "normalization_version",
        "rules_version",
        "classification_schema_version",
        "row_count",
    )
    require_values(facts, {key: proof[key] for key in keys})
    require_values(
        facts,
        {
            "evidence_manifest_sha256": proof_hash,
            "evidence_manifest_uri": proof_path.resolve().as_uri(),
        },
    )


def verify_stored_pipeline_proof(
    path: Path,
    snapshot_sha256: str,
    pipeline_report: Path | None,
    provenance: RunProvenance,
    *,
    expected_row_ids: tuple[str, ...] | None = None,
) -> str:
    """Bind bytes, rows, versions and report occurrence; allow shadow profile identity."""
    content = path.read_bytes()
    proof_hash = sha256_bytes(content)
    proof = document(content)
    run_id, profile, rows = _require_occurrence(proof, snapshot_sha256, provenance)
    if expected_row_ids is not None and (
        len(set(expected_row_ids)) != len(expected_row_ids)
        or rows != set(expected_row_ids)
    ):
        raise ValueError("pipeline proof belongs to another admitted cohort")
    artifacts = _load_artifacts(path.parent, proof)
    _verify_rows(
        artifacts, rows=rows, run_id=run_id, profile=profile, provenance=provenance
    )
    report = document(_report_content(path.parent, proof, pipeline_report))
    _check_report(report, proof, path, proof_hash)
    return proof_hash
