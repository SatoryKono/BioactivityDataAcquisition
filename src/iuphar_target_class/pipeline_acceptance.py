"""Run the TC-10 volume contract only on a frozen, admitted Stage-0 cohort."""

from __future__ import annotations

import hashlib
import json
import platform
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from .models import RawTargetRow, RunProvenance
from .pipeline import BatchResult, IndexedSnapshot, classify_batch
from .pipeline_io import read_legacy_batch
from .policy import VOLUME_TEST_SECONDS
from .stage0.io import atomic_write_bytes, canonical_json_bytes


@dataclass(frozen=True, slots=True)
class VolumePlan:
    """Caller-provided, owner-approved pre-run configuration."""

    manifest_sha256: str
    selected_source_paths: tuple[str, ...]
    expected_rows: int
    approval_reference: str
    environment: str


@dataclass(frozen=True, slots=True)
class AdmittedCohort:
    """Verified snapshot of configured inputs; source files remain untouched."""

    manifest_sha256: str
    source_digests: tuple[tuple[str, str], ...]
    rows: tuple[RawTargetRow, ...]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inside(root: Path, relative: str) -> Path:
    base = root.resolve()
    item = (base / relative).resolve()
    if not item.is_relative_to(base) or item == base:
        raise ValueError("cohort artifact path escapes its manifest directory")
    return item


def _verified_artifacts(manifest: Mapping[str, object], root: Path) -> None:
    artifacts = manifest["artifact_sha256"]
    if not isinstance(artifacts, dict) or not {
        "content_checks.csv",
        "m_code_versions.csv",
        "provenance_map.csv",
        "stage_report.json",
    }.issubset(artifacts):
        raise ValueError("missing Stage-0 proof artifacts")
    for name, digest in artifacts.items():
        if _sha(_inside(root, name).read_bytes()) != digest:
            raise ValueError(f"Stage-0 proof hash mismatch: {name}")


class _ManifestCopy(TypedDict):
    source_path: str
    copy_path: str
    sha256: str
    byte_count: int


def _load_verified_copies(
    root: Path,
    copies: list[_ManifestCopy],
    selected_source_paths: tuple[str, ...],
) -> tuple[list[RawTargetRow], list[tuple[str, str]]]:
    entries = {entry["source_path"]: entry for entry in copies}
    requested = tuple(dict.fromkeys(selected_source_paths))
    if len(entries) != len(copies) or requested != selected_source_paths:
        raise ValueError("duplicate Stage-0 source identity")
    rows: list[RawTargetRow] = []
    hashes: list[tuple[str, str]] = []
    for source in requested:
        if source not in entries:
            raise ValueError(f"cohort source has no Stage-0 copy: {source}")
        entry = entries[source]
        content = _inside(root, entry["copy_path"]).read_bytes()
        digest = _sha(content)
        if digest != entry["sha256"] or len(content) != entry["byte_count"]:
            raise ValueError(f"cohort source bytes differ from manifest: {source}")
        rows.extend(read_legacy_batch(content))
        hashes.append((source, digest))
    return rows, hashes


def load_admitted_cohort(manifest_path: Path, plan: VolumePlan) -> AdmittedCohort:
    """Fail closed on a missing/empty, changed or incompletely selected cohort."""
    raw = manifest_path.read_bytes()
    if _sha(raw) != plan.manifest_sha256:
        raise ValueError("expected pinned Stage-0 manifest")
    manifest = json.loads(raw)
    if manifest.get("artifact") != "stage0_manifest" or manifest.get("stage") != "0":
        raise ValueError("not a Stage-0 manifest")
    copies = manifest.get("copies")
    if not copies or not plan.selected_source_paths:
        raise ValueError("Stage-0 cohort has no admitted source copies")
    if (
        not plan.approval_reference.strip()
        or not plan.environment.strip()
        or plan.expected_rows <= 0
    ):
        raise ValueError(
            "approved cohort, environment and expected count must be pinned"
        )
    root = manifest_path.parent
    _verified_artifacts(manifest, root)
    rows, hashes = _load_verified_copies(root, copies, plan.selected_source_paths)
    if len(rows) != plan.expected_rows or len({r.input_row_id for r in rows}) != len(
        rows
    ):
        raise ValueError("cohort count differs or row identities are not unique")
    return AdmittedCohort(plan.manifest_sha256, tuple(hashes), tuple(rows))


def run_admitted_volume(
    *,
    manifest_path: Path,
    plan: VolumePlan,
    snapshot: IndexedSnapshot,
    provenance: RunProvenance,
    run_id: str,
    output_dir: Path,
    clock: Callable[[], float] = time.perf_counter,
) -> tuple[BatchResult, dict[str, object]]:
    """Write the frozen config before running the full indexed pipeline."""
    if not snapshot.complete or not all(
        (
            provenance.normalization_version,
            provenance.rules_version,
            provenance.schema_version,
            provenance.retrieved_at,
            provenance.run_started_at,
        )
    ):
        raise ValueError(
            "qualified volume needs complete snapshot and versioned provenance"
        )
    cohort = load_admitted_cohort(manifest_path, plan)
    config = canonical_json_bytes(
        {
            "stage0_manifest_sha256": cohort.manifest_sha256,
            "source_digests": dict(cohort.source_digests),
            "approval_reference": plan.approval_reference,
            "planned_environment": plan.environment,
            "observed_runtime": platform.python_version(),
            "snapshot_id": snapshot.snapshot_id,
            "mapping_version": snapshot.mapping_version,
            "normalization_version": provenance.normalization_version,
            "rules_version": provenance.rules_version,
            "schema_version": provenance.schema_version,
            "expected_rows": plan.expected_rows,
            "limit_seconds": VOLUME_TEST_SECONDS,
            "run_id": run_id,
        }
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / "volume-config.json"
    with config_path.open("xb") as f:
        f.write(config)
    started = clock()
    batch = classify_batch(
        cohort.rows,
        snapshot=snapshot,
        provenance=provenance,
        run_id=run_id,
    )
    elapsed = clock() - started
    report: dict[str, object] = {
        "status": "PASS"
        if 0 <= elapsed <= VOLUME_TEST_SECONDS and batch.status == "processed"
        else "FAIL",
        "scope": "volume timing and full-batch execution only",
        "biological_accuracy_accepted": False,
        "config_sha256": _sha(config),
        "elapsed_seconds": elapsed,
        "metrics": dict(batch.metrics),
        "snapshot_id": snapshot.snapshot_id,
    }
    atomic_write_bytes(
        output_dir / "volume-result.json", canonical_json_bytes(report), root=output_dir
    )
    return batch, report
