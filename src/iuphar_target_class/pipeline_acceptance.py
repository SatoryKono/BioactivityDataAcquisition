"""Run the TC-10 volume contract only on a frozen, admitted Stage-0 cohort."""

from __future__ import annotations

import hashlib
import json
import platform
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypedDict, cast

from .models import RawTargetRow, RunProvenance
from .pipeline import BatchResult, IndexedSnapshot, classify_batch
from .pipeline_io import (
    BIOETL_TARGET_KERNEL_CSV_V1,
    read_bioetl_target_kernel_csv_v1,
    read_chembl_target_csv_v1,
    read_legacy_batch,
)
from .policy import VOLUME_TEST_SECONDS
from .stage0.io import atomic_write_bytes, canonical_json_bytes
from .stage0.v2 import verify_stage0_v2


@dataclass(frozen=True, slots=True)
class SourceImport:
    """Owner-selected versioned conversion, frozen before volume execution."""

    source_path: str
    format_version: str
    target_kind: str


@dataclass(frozen=True, slots=True)
class VolumePlan:
    """Caller-provided, owner-approved pre-run configuration."""

    manifest_sha256: str
    selected_source_paths: tuple[str, ...]
    expected_rows: int
    approval_reference: str
    environment: str
    source_imports: tuple[SourceImport, ...] = ()


@dataclass(frozen=True, slots=True)
class AdmittedCohort:
    """Verified snapshot of configured inputs; source files remain untouched."""

    manifest_sha256: str
    source_digests: tuple[tuple[str, str], ...]
    rows: tuple[RawTargetRow, ...]
    schema_version: int = 1
    evidence_digests: tuple[tuple[str, str], ...] = ()
    cohort_manifest_sha256: str | None = None
    conversion_ledger_sha256: str | None = None


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


def _cohort_source_rows(
    content: bytes, source: str, profile: SourceImport | None
) -> tuple[RawTargetRow, ...]:
    """Convert only already verified bytes using the owner-selected profile."""
    if profile is None:
        return read_legacy_batch(content)
    if profile.format_version == BIOETL_TARGET_KERNEL_CSV_V1:
        return read_bioetl_target_kernel_csv_v1(
            content, source_path=source, target_kind=profile.target_kind
        )
    if profile.format_version == "chembl_target_csv_v1":
        return read_chembl_target_csv_v1(
            content, source_path=source, target_kind=profile.target_kind
        )
    raise ValueError(f"unsupported Stage-0 source import profile: {source}")


def _load_verified_copies(
    root: Path,
    copies: list[_ManifestCopy],
    selected_source_paths: tuple[str, ...],
    imports: Mapping[str, SourceImport],
) -> tuple[list[RawTargetRow], list[tuple[str, str]]]:
    entries = {entry["source_path"]: entry for entry in copies}
    requested = tuple(dict.fromkeys(selected_source_paths))
    if len(entries) != len(copies) or requested != selected_source_paths:
        raise ValueError("duplicate Stage-0 source identity")
    if set(requested) != set(entries):
        raise ValueError("volume requires the complete pinned Stage-0 source set")
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
        profile = imports.get(source)
        rows.extend(_cohort_source_rows(content, source, profile))
        hashes.append((source, digest))
    return rows, hashes


def _require_cohort_plan(plan: VolumePlan) -> None:
    """Require the approved execution scope before reading proof artifacts."""
    if (
        not plan.approval_reference.strip()
        or not plan.environment.strip()
        or plan.expected_rows <= 0
    ):
        raise ValueError(
            "approved cohort, environment and expected count must be pinned"
        )


def _cohort_source_profiles(plan: VolumePlan) -> dict[str, SourceImport]:
    """Reject ambiguous or unselected conversion profiles after proof checks."""
    imports = {profile.source_path: profile for profile in plan.source_imports}
    if len(imports) != len(plan.source_imports) or set(imports) - set(
        plan.selected_source_paths
    ):
        raise ValueError("duplicate or unselected Stage-0 source import profile")
    return imports


def load_admitted_cohort(manifest_path: Path, plan: VolumePlan) -> AdmittedCohort:
    """Fail closed on a missing/empty, changed or incompletely selected cohort."""
    raw = manifest_path.read_bytes()
    if _sha(raw) != plan.manifest_sha256:
        raise ValueError("expected pinned Stage-0 manifest")
    manifest = json.loads(raw)
    if manifest.get("artifact") != "stage0_manifest" or manifest.get("stage") != "0":
        raise ValueError("not a Stage-0 manifest")
    if manifest.get("schema_version") == 2:
        return _load_admitted_cohort_v2(manifest_path, plan)
    copies = manifest.get("copies")
    if not copies or not plan.selected_source_paths:
        raise ValueError("Stage-0 cohort has no admitted source copies")
    _require_cohort_plan(plan)
    root = manifest_path.parent
    _verified_artifacts(manifest, root)
    imports = _cohort_source_profiles(plan)
    rows, hashes = _load_verified_copies(
        root, copies, plan.selected_source_paths, imports
    )
    if len(rows) != plan.expected_rows or len({r.input_row_id for r in rows}) != len(
        rows
    ):
        raise ValueError("cohort count differs or row identities are not unique")
    return AdmittedCohort(plan.manifest_sha256, tuple(hashes), tuple(rows))


def _load_admitted_cohort_v2(manifest_path: Path, plan: VolumePlan) -> AdmittedCohort:
    """Verify evidence bytes as well as the entire selected cohort material set."""
    _require_cohort_plan(plan)
    frozen = verify_stage0_v2(
        manifest_path, plan.manifest_sha256, plan.selected_source_paths
    )
    imports = _cohort_source_profiles(plan)
    if set(imports) != set(frozen.cohort_payloads):
        raise ValueError(
            "Stage-0 V2 requires an explicit profile for every cohort copy"
        )
    entries = {
        item["source_path"]: item
        for item in cast("list[dict[str, object]]", frozen.document["copies"])
    }
    rows: list[RawTargetRow] = []
    for source in plan.selected_source_paths:
        profile = imports[source]
        entry = entries[source]
        if (profile.format_version, profile.target_kind) != (
            entry["format_version"],
            entry["target_kind"],
        ):
            raise ValueError(
                "cohort import profile differs from its frozen Stage-0 declaration"
            )
        rows.extend(
            _cohort_source_rows(frozen.cohort_payloads[source], source, profile)
        )
    if len(rows) != plan.expected_rows or len(
        {row.input_row_id for row in rows}
    ) != len(rows):
        raise ValueError("cohort count differs or row identities are not unique")
    return AdmittedCohort(
        plan.manifest_sha256,
        frozen.cohort_digests,
        tuple(rows),
        2,
        frozen.evidence_digests,
        frozen.cohort_manifest_sha256,
        frozen.conversion_ledger_sha256,
    )


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
    admitted = (
        snapshot.admission_complete
        if snapshot.admission_complete is not None
        else snapshot.complete
    )
    if not admitted or not all(
        (
            provenance.normalization_version,
            provenance.rules_version,
            provenance.schema_version,
            provenance.retrieved_at,
            provenance.run_started_at,
        )
    ):
        raise ValueError(
            "qualified volume needs admitted snapshot scope and versioned provenance"
        )
    cohort = load_admitted_cohort(manifest_path, plan)
    config = canonical_json_bytes(
        {
            "stage0_manifest_sha256": cohort.manifest_sha256,
            "source_digests": dict(cohort.source_digests),
            "source_imports": [asdict(profile) for profile in plan.source_imports],
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
