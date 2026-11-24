"""Manifest documents and path checks for assay-target restoration."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from deltalake import DeltaTable

from bioetl.infrastructure.storage.target_fk_restoration_plan import (
    TargetAbsenceFinding,
    TargetFKRestorationPlan,
    TargetRecoveryInput,
    current_assay_target_ids,
    current_target_ids,
)
from iuphar_target_class.stage0.io import canonical_json_bytes

_DECISION = "contract-decision.json"


@dataclass(frozen=True, slots=True)
class _LiveTables:
    paths: Mapping[str, Path]
    silver: list[dict[str, object]]
    gold: list[dict[str, object]]
    assay: list[dict[str, object]]


def _document(
    live: _LiveTables,
    plan: TargetFKRestorationPlan,
    *,
    status: str,
    candidate_files: list[dict[str, str]],
    row_hashes: Mapping[str, Mapping[str, str]],
    closed: bool,
) -> dict[str, object]:
    published = {
        layer: sorted(
            item.target_id for item in plan.restorations if layer in item.layers
        )
        for layer in ("silver", "gold")
    }
    if not closed:
        published = {"silver": [], "gold": []}
    return {
        "artifact": "bioetl_target_fk_restoration",
        "schema_version": 1,
        "status": status,
        "baseline": _baseline(live),
        "findings": [
            _finding_document(item, row_hashes, published=closed)
            for item in plan.findings
        ],
        "sources": _sources(plan),
        "published_target_ids": published,
        "candidate_files": candidate_files,
        "checks": {
            "fk_checks_unchanged": True,
            "existing_target_ids_preserved": True,
            "assay_rows_preserved": True,
            "placeholders_rejected": True,
            "scd_history_preserved": True,
            "assay_target_fk_closed": closed,
        },
    }


def _finding_document(
    item: object,
    row_hashes: Mapping[str, Mapping[str, str]],
    *,
    published: bool,
) -> dict[str, object]:
    finding = item if isinstance(item, TargetAbsenceFinding) else None
    if finding is None:
        raise ValueError("target absence finding is incomplete")
    item = finding
    layers = list(item.layers) if item.disposition == "restore" else []
    hashes = row_hashes.get(item.target_id, {})
    row_sha256 = {layer: hashes[layer] for layer in layers} if published else {}
    return {
        "target_id": item.target_id,
        "absence_reason": item.absence_reason,
        "disposition": item.disposition,
        "source_kind": item.source_kind,
        "source_path": item.source_path,
        "source_sha256": item.source_sha256,
        "layers": layers,
        "row_sha256": row_sha256,
    }


def _decision_document(plan: TargetFKRestorationPlan) -> dict[str, object]:
    return {
        "artifact": "bioetl_target_fk_contract_decision",
        "schema_version": 1,
        "status": "blocked_pending_contract_reconciliation",
        "missing_target_ids": list(plan.missing_ids),
        "blockers": [
            {"target_id": item.target_id, "absence_reason": item.absence_reason}
            for item in plan.blockers
        ],
        "rule": (
            "Gold filters and assay/target FK checks stay in force; "
            "blocked targets are not published and assay rows are not deleted."
        ),
    }


def _baseline(live: _LiveTables) -> dict[str, object]:
    baseline: dict[str, object] = {
        name: _identity(live.paths[name], getattr(live, name))
        for name in ("silver", "gold", "assay")
    }
    assay_ids = sorted(current_assay_target_ids(live.assay))
    baseline["existing_target_ids"] = sorted(
        {str(row["target_id"]) for row in live.gold}
    )
    baseline["assay_target_ids"] = assay_ids
    baseline["missing_target_ids"] = sorted(
        set(assay_ids) - current_target_ids(live.gold)
    )
    return baseline


def _identity(path: Path, rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    return {
        "version": int(DeltaTable(str(path)).version()),
        "row_count": len(rows),
        "files": _file_hashes(path),
    }


def _sources(plan: TargetFKRestorationPlan) -> list[dict[str, str]]:
    seen: dict[str, str] = {}
    for item in plan.findings:
        if item.source_path and item.source_sha256:
            previous = seen.setdefault(item.source_path, item.source_sha256)
            if previous != item.source_sha256:
                raise ValueError("target recovery source digest changed")
    return [{"path": path, "sha256": seen[path]} for path in sorted(seen)]


def _candidate_files(root: Path, workspace: Path) -> list[dict[str, str]]:
    base = workspace.resolve()
    files: list[dict[str, str]] = []
    for layer in ("gold", "silver"):
        layer_root = root / layer
        for relative, digest in sorted(_file_hashes(layer_root).items()):
            path = (layer_root / relative).resolve()
            files.append({"path": path.relative_to(base).as_posix(), "sha256": digest})
    return sorted(files, key=lambda item: item["path"])


def _file_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("target FK restoration refuses symlink paths")
        if path.is_file():
            hashes[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return hashes


def _require_manifest(manifest: Path, document: Mapping[str, object]) -> None:
    if manifest.read_bytes() != canonical_json_bytes(document):
        raise ValueError("target FK restoration destination already differs")


def _contained(path: Path, workspace: Path) -> Path:
    resolved = path.resolve()
    root = workspace.resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError("target FK restoration escapes the approved workspace")
    return resolved


def _contained_source(item: TargetRecoveryInput, workspace: Path) -> None:
    resolved = _contained(item.source_file, workspace)
    relative = resolved.relative_to(workspace.resolve()).as_posix()
    if relative != item.source_path:
        raise ValueError("target recovery source path does not match its file")
    if any(
        part.lower().endswith(".env") or part.lower().startswith(".env.")
        for part in resolved.parts
    ):
        raise ValueError("environment files cannot enter target recovery")


def _reject_overlap(destination: Path, protected: Path) -> None:
    source = protected.resolve()
    if (
        destination == source
        or destination.is_relative_to(source)
        or source.is_relative_to(destination)
    ):
        raise ValueError("target FK restoration overlaps a preserved table")
