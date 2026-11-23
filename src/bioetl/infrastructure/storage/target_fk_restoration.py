"""Publish verified assay→target rows without changing the frozen baseline.

Original Silver, Gold and assay tables stay byte-for-byte unchanged. Admissible
rows are copied into a separate candidate directory. A Gold-filter or contract
conflict writes a decision record and keeps the closure blocker.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import orjson
import pyarrow as pa
import yaml
from deltalake import DeltaTable, write_deltalake

from bioetl.domain.filtering.gold_config import GoldFilterConfig
from bioetl.infrastructure.schemas.filter_config import GoldFiltersFileConfig
from bioetl.infrastructure.storage.delta.schema_ops import (
    coerce_null_types_for_delta,
    delta_schema_to_pyarrow,
)
from bioetl.infrastructure.storage.target_migration_classification_checks import (
    ASSAY_TARGET_CLOSURE_ERROR,
    TargetFKRestorationPlan,
    TargetRecoveryInput,
    canonical_row_sha256,
    current_assay_target_ids,
    current_target_ids,
    plan_target_fk_restoration,
)
from bioetl.infrastructure.storage.target_migration_row_ops import (
    by_id,
    read_delta,
)
from iuphar_target_class.stage0.io import atomic_write_bytes, canonical_json_bytes

_MANIFEST = "manifest.json"
_DECISION = "contract-decision.json"


@dataclass(frozen=True, slots=True)
class _LiveTables:
    paths: Mapping[str, Path]
    silver: list[dict[str, object]]
    gold: list[dict[str, object]]
    assay: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class PublishedTargetRestoration:
    """Rows a validated candidate adds, keyed by target id and SCD version."""

    additions: Mapping[str, tuple[dict[str, object], ...]]
    addition_keys: Mapping[str, frozenset[tuple[str, int | None]]]


def load_target_gold_filter(config: Path) -> GoldFilterConfig:
    """Load the executable Gold filter from the entity configuration."""
    document = yaml.safe_load(config.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("target configuration must be a mapping")
    filters = document.get("filters")
    if not isinstance(filters, dict) or "gold_filters" not in filters:
        raise ValueError("target configuration has no Gold filter")
    return GoldFiltersFileConfig.model_validate(filters["gold_filters"]).to_domain()


def publish_target_fk_restoration(
    *,
    silver: Path,
    gold: Path,
    assay: Path,
    config: Path,
    recoveries: Sequence[TargetRecoveryInput],
    destination: Path,
    workspace: Path,
) -> Path:
    """Write additive candidate tables, or a blocker decision, then stop."""
    root = _contained(destination, workspace)
    for source in (silver, gold, assay, config):
        _reject_overlap(root, source)
    for item in recoveries:
        _contained_source(item, workspace)
    live = _read_live(silver, gold, assay)
    plan = plan_target_fk_restoration(
        silver_rows=live.silver,
        gold_rows=live.gold,
        assay_rows=live.assay,
        recoveries=recoveries,
        gold_filter=load_target_gold_filter(config),
    )
    manifest = root / _MANIFEST
    if plan.blockers:
        _publish_blocker(root, manifest, live, plan)
    if manifest.is_file():
        _require_manifest(manifest, _validated_document(root, live, plan, workspace))
        return manifest
    if root.exists():
        raise ValueError("target FK restoration destination must be new")
    _write_candidates(root, live, plan, silver, gold)
    atomic_write_bytes(
        manifest,
        canonical_json_bytes(_validated_document(root, live, plan, workspace)),
        root=root,
    )
    return manifest


def load_published_restoration(
    manifest: Path,
    *,
    workspace: Path,
    silver: Path,
    gold: Path,
    assay: Path,
    config: Path,
) -> PublishedTargetRestoration:
    """Re-check a validated manifest against the live baseline and its tables."""
    payload = manifest.read_bytes()
    document = orjson.loads(payload)
    if (
        not isinstance(document, dict)
        or document.get("status") != "validated_candidate"
    ):
        raise ValueError(ASSAY_TARGET_CLOSURE_ERROR)
    live = _read_live(silver, gold, assay)
    recoveries = _recoveries_from_document(document, workspace, manifest.parent)
    plan = plan_target_fk_restoration(
        silver_rows=live.silver,
        gold_rows=live.gold,
        assay_rows=live.assay,
        recoveries=recoveries,
        gold_filter=load_target_gold_filter(config),
    )
    if plan.blockers:
        raise ValueError(ASSAY_TARGET_CLOSURE_ERROR)
    expected = canonical_json_bytes(
        _validated_document(manifest.parent, live, plan, workspace)
    )
    if payload != expected:
        raise ValueError(
            "target FK restoration manifest does not match the frozen baseline"
        )
    additions = _addition_rows(manifest.parent, plan)
    return PublishedTargetRestoration(
        additions,
        {
            layer: frozenset(by_id(rows)) if rows else frozenset()
            for layer, rows in additions.items()
        },
    )


def _publish_blocker(
    root: Path,
    manifest: Path,
    live: _LiveTables,
    plan: TargetFKRestorationPlan,
) -> None:
    document = _blocked_document(root, live, plan)
    if manifest.is_file():
        _require_manifest(manifest, document)
    else:
        if root.exists():
            raise ValueError("target FK restoration destination must be new")
        decision = _decision_document(plan)
        atomic_write_bytes(root / _DECISION, canonical_json_bytes(decision), root=root)
        atomic_write_bytes(manifest, canonical_json_bytes(document), root=root)
    raise ValueError(ASSAY_TARGET_CLOSURE_ERROR)


def _validated_document(
    root: Path,
    live: _LiveTables,
    plan: TargetFKRestorationPlan,
    workspace: Path,
) -> dict[str, object]:
    additions = _addition_rows(root, plan)
    _require_preservation(live, root, plan)
    return _document(
        live,
        plan,
        status="validated_candidate",
        candidate_files=_candidate_files(root, workspace),
        row_hashes=_row_hashes(additions),
        closed=True,
    )


def _blocked_document(
    root: Path,
    live: _LiveTables,
    plan: TargetFKRestorationPlan,
) -> dict[str, object]:
    decision = _decision_document(plan)
    payload = canonical_json_bytes(decision)
    decision_path = root / _DECISION
    if decision_path.is_file() and decision_path.read_bytes() != payload:
        raise ValueError("target FK contract decision already differs")
    document = _document(
        live,
        plan,
        status="blocked",
        candidate_files=[],
        row_hashes={},
        closed=False,
    )
    document["contract_decision"] = {
        "path": _DECISION,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "status": "blocked_pending_contract_reconciliation",
    }
    return document


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
    from bioetl.infrastructure.storage.target_migration_classification_checks import (
        TargetAbsenceFinding,
    )

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


def _write_candidates(
    root: Path,
    live: _LiveTables,
    plan: TargetFKRestorationPlan,
    silver: Path,
    gold: Path,
) -> None:
    rows = {
        "silver": [*live.silver, *_layer_rows(plan, "silver")],
        "gold": [*live.gold, *_layer_rows(plan, "gold")],
    }
    originals = {"silver": silver, "gold": gold}
    for layer, table_rows in rows.items():
        _write_layer(originals[layer], root / layer, table_rows)
    _require_preservation(live, root, plan)


def _layer_rows(plan: TargetFKRestorationPlan, layer: str) -> list[dict[str, object]]:
    selected = []
    for item in plan.restorations:
        row = item.silver_row if layer == "silver" else item.gold_row
        if layer in item.layers and row is not None:
            selected.append(dict(row))
    return selected


def _write_layer(
    original: Path, destination: Path, rows: list[dict[str, object]]
) -> None:
    delta = DeltaTable(str(original))
    schema = delta_schema_to_pyarrow(delta.schema())
    table = coerce_null_types_for_delta(pa.Table.from_pylist(rows, schema=schema))
    partitions = list(delta.metadata().partition_columns)
    write_deltalake(
        str(destination),
        table,
        mode="error",
        partition_by=partitions or None,
    )


def _require_preservation(
    live: _LiveTables,
    root: Path,
    plan: TargetFKRestorationPlan,
) -> None:
    for layer in ("silver", "gold"):
        written = by_id(read_delta(root / layer))
        original = by_id(getattr(live, layer))
        if set(original) - set(written):
            raise ValueError("existing target rows were dropped")
        for key, row in original.items():
            if canonical_row_sha256(written[key]) != canonical_row_sha256(row):
                raise ValueError(f"existing target changed: {key[0]}")
        added = set(written) - set(original)
        planned = _layer_rows(plan, layer)
        expected = (
            {
                key
                for key, row in by_id(planned).items()
                if row.get("_is_current", True)
            }
            if planned
            else set()
        )
        if added != expected:
            raise ValueError("published target cohort does not match the plan")
    assay = root / "assay"
    if assay.exists():
        raise ValueError("target FK restoration must not write assay rows")


def _addition_rows(
    root: Path, plan: TargetFKRestorationPlan
) -> dict[str, tuple[dict[str, object], ...]]:
    additions: dict[str, tuple[dict[str, object], ...]] = {}
    for layer in ("silver", "gold"):
        written = by_id(read_delta(root / layer))
        rows = []
        for item in plan.restorations:
            if layer not in item.layers:
                continue
            matches = [
                dict(row)
                for key, row in written.items()
                if key[0] == item.target_id and row.get("_is_current", True)
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"published restoration is missing {layer}:{item.target_id}"
                )
            rows.append(matches[0])
        additions[layer] = tuple(rows)
    return additions


def _row_hashes(
    additions: Mapping[str, Sequence[Mapping[str, object]]],
) -> dict[str, dict[str, str]]:
    hashes: dict[str, dict[str, str]] = {}
    for layer, rows in additions.items():
        for row in rows:
            hashes.setdefault(str(row["target_id"]), {})[layer] = canonical_row_sha256(
                row
            )
    return hashes


def _recoveries_from_document(
    document: Mapping[str, object], workspace: Path, root: Path
) -> tuple[TargetRecoveryInput, ...]:
    findings = document.get("findings")
    if not isinstance(findings, list):
        raise ValueError("target FK restoration findings are incomplete")
    additions = {
        layer: {
            str(row["target_id"]): row
            for row in read_delta(root / layer)
            if row.get("_is_current", True)
        }
        for layer in ("silver", "gold")
    }
    recoveries: list[TargetRecoveryInput] = []
    for item in findings:
        if not isinstance(item, dict) or item.get("disposition") != "restore":
            raise ValueError(ASSAY_TARGET_CLOSURE_ERROR)
        target_id = str(item["target_id"])
        source = workspace / str(item["source_path"])
        silver_row = (
            additions["silver"].get(target_id)
            if "silver" in item.get("layers", [])
            else None
        )
        recoveries.append(
            TargetRecoveryInput(
                target_id,
                str(item["source_kind"]),
                str(item["source_path"]),
                source,
                str(item["source_sha256"]),
                silver_row,
                additions["gold"][target_id],
            )
        )
    return tuple(recoveries)


def _read_live(silver: Path, gold: Path, assay: Path) -> _LiveTables:
    paths = {"silver": silver, "gold": gold, "assay": assay}
    return _LiveTables(
        paths,
        read_delta(silver),
        read_delta(gold),
        read_delta(assay),
    )


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


__all__ = [
    "PublishedTargetRestoration",
    "load_published_restoration",
    "load_target_gold_filter",
    "publish_target_fk_restoration",
]
