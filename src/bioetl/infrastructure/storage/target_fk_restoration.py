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

from bioetl.infrastructure.schemas.filter_config import GoldFiltersFileConfig
from bioetl.infrastructure.storage.delta.schema_ops import (
    coerce_null_types_for_delta,
    delta_schema_to_pyarrow,
)
from bioetl.infrastructure.storage.target_fk_restoration_documents import (
    _candidate_files,
    _contained,
    _contained_source,
    _decision_document,
    _document,
    _LiveTables,
    _reject_overlap,
    _require_manifest,
)
from bioetl.infrastructure.storage.target_fk_restoration_plan import (
    ASSAY_TARGET_CLOSURE_ERROR,
    GoldRowFilter,
    TargetFKRestorationPlan,
    TargetRecoveryInput,
    _source_payload,
    canonical_row_sha256,
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
class PublishedTargetRestoration:
    """Rows a validated candidate adds, keyed by target id and SCD version."""

    additions: Mapping[str, tuple[dict[str, object], ...]]
    addition_keys: Mapping[str, frozenset[tuple[str, int | None]]]


def load_target_gold_filter(config: Path) -> GoldRowFilter:
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
    written = _read_candidates(manifest.parent)
    recoveries = _recoveries_from_document(document, workspace, written)
    plan = plan_target_fk_restoration(
        silver_rows=live.silver,
        gold_rows=live.gold,
        assay_rows=live.assay,
        recoveries=recoveries,
        gold_filter=load_target_gold_filter(config),
    )
    if plan.blockers:
        raise ValueError(ASSAY_TARGET_CLOSURE_ERROR)
    additions = _addition_rows(written, plan)
    expected = canonical_json_bytes(
        _validated_document(manifest.parent, live, plan, workspace, additions, written)
    )
    if payload != expected:
        raise ValueError(
            "target FK restoration manifest does not match the frozen baseline"
        )
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
    additions: Mapping[str, Sequence[Mapping[str, object]]] | None = None,
    written: Mapping[str, Sequence[Mapping[str, object]]] | None = None,
) -> dict[str, object]:
    tables = written if written is not None else _read_candidates(root)
    if additions is None:
        additions = _addition_rows(tables, plan)
    _require_preservation(live, root, plan, tables)
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
    _require_preservation(live, root, plan, _read_candidates(root))


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
    written_rows: Mapping[str, Sequence[Mapping[str, object]]],
) -> None:
    for layer in ("silver", "gold"):
        written = by_id(written_rows[layer])
        original = by_id(getattr(live, layer))
        if set(original) - set(written):
            raise ValueError("existing target rows were dropped")
        for key, row in original.items():
            if canonical_row_sha256(written[key]) != canonical_row_sha256(row):
                raise ValueError(f"existing target changed: {key[0]}")
        added = set(written) - set(original)
        planned = _layer_rows(plan, layer)
        expected = (
            {key for key, row in by_id(planned).items() if row.get("_is_current", True)}
            if planned
            else set()
        )
        if added != expected:
            raise ValueError("published target cohort does not match the plan")
    assay = root / "assay"
    if assay.exists():
        raise ValueError("target FK restoration must not write assay rows")


def _addition_rows(
    written_rows: Mapping[str, Sequence[Mapping[str, object]]],
    plan: TargetFKRestorationPlan,
) -> dict[str, tuple[dict[str, object], ...]]:
    additions: dict[str, tuple[dict[str, object], ...]] = {}
    for layer in ("silver", "gold"):
        written = by_id(written_rows[layer])
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


def _read_candidates(root: Path) -> dict[str, list[dict[str, object]]]:
    return {layer: read_delta(root / layer) for layer in ("silver", "gold")}


def _recoveries_from_document(
    document: Mapping[str, object],
    workspace: Path,
    written_rows: Mapping[str, Sequence[Mapping[str, object]]],
) -> tuple[TargetRecoveryInput, ...]:
    findings = document.get("findings")
    if not isinstance(findings, list):
        raise ValueError("target FK restoration findings are incomplete")
    additions = {
        layer: {
            str(row["target_id"]): row
            for row in written_rows[layer]
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
        gold_row = additions["gold"][target_id]
        layers = item.get("layers", [])
        if isinstance(layers, list) and "silver" in layers:
            silver_row = additions["silver"].get(target_id)
        else:
            silver_row = _pinned_source_silver(
                target_id,
                str(item["source_path"]),
                source,
                str(item["source_sha256"]),
                gold_row,
            )
        recoveries.append(
            TargetRecoveryInput(
                target_id,
                str(item["source_kind"]),
                str(item["source_path"]),
                source,
                str(item["source_sha256"]),
                silver_row,
                gold_row,
            )
        )
    return tuple(recoveries)


def _pinned_source_silver(
    target_id: str,
    source_path: str,
    source: Path,
    digest: str,
    gold_row: Mapping[str, object],
) -> dict[str, object] | None:
    """Keep a source Silver row that was verified but not added to the candidate."""
    stored = _source_payload(
        TargetRecoveryInput(
            target_id,
            "verified_pipeline_output",
            source_path,
            source,
            digest,
            None,
            gold_row,
        )
    ).get("silver")
    if stored is None:
        return None
    if not isinstance(stored, dict):
        raise ValueError(
            "target recovery source does not contain the restored silver row"
        )
    return dict(stored)


def _read_live(silver: Path, gold: Path, assay: Path) -> _LiveTables:
    paths = {"silver": silver, "gold": gold, "assay": assay}
    return _LiveTables(
        paths,
        read_delta(silver),
        read_delta(gold),
        read_delta(assay),
    )


__all__ = [
    "PublishedTargetRestoration",
    "load_published_restoration",
    "load_target_gold_filter",
    "publish_target_fk_restoration",
]
