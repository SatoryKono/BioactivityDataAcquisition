"""Checkpoint anchor comparison for Control Plane identity evidence."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest
from bioetl.interfaces.http.control_plane_identity.extractors import (
    checkpoint_anchor_payload,
    composite_run_identity,
    input_snapshot_fingerprint,
    input_snapshots,
    normalize_checkpoint_metadata_payload,
)
from bioetl.interfaces.http.control_plane_identity.formatting import (
    format_full_value,
    is_present,
    short_value,
)
from bioetl.interfaces.http.control_plane_identity.specs import CHECKPOINT_ANCHORS


def _resolve_checkpoint_payload(
    manifest: RunManifest,
    checkpoint_metadata: dict[str, object] | None,
) -> dict[str, object]:
    if checkpoint_metadata is not None:
        return normalize_checkpoint_metadata_payload(checkpoint_metadata)
    return checkpoint_anchor_payload(manifest)


def _missing_checkpoint_rows(
    current: dict[str, object | None],
) -> list[dict[str, object]]:
    return [
        checkpoint_row(name, current.get(name), None, "MISSING")
        for name in CHECKPOINT_ANCHORS
        if is_present(current.get(name))
    ]


def _aggregate_checkpoint_status(statuses: list[str]) -> str:
    if "MISMATCH" in statuses:
        return "MISMATCH"
    if "MISSING" in statuses and "OK" in statuses:
        return "PARTIAL"
    if all(item == "MISSING" for item in statuses):
        return "MISSING"
    if all(item in {"OK", "N/A"} for item in statuses):
        return "OK"
    return "PARTIAL"


def _compare_checkpoint_pairs(
    current: dict[str, object | None],
    checkpoint: dict[str, object],
) -> tuple[str, list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    statuses: list[str] = []
    for name in CHECKPOINT_ANCHORS:
        current_value = current.get(name)
        checkpoint_value = checkpoint.get(name)
        status = checkpoint_pair_status(current_value, checkpoint_value)
        statuses.append(status)
        rows.append(checkpoint_row(name, current_value, checkpoint_value, status))
    return _aggregate_checkpoint_status(statuses), rows


def build_checkpoint_compare(
    manifest: RunManifest | None,
    *,
    checkpoint_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    if manifest is None:
        return {"status": "UNKNOWN", "rows": []}
    current = current_checkpoint_anchors(manifest)
    checkpoint = _resolve_checkpoint_payload(manifest, checkpoint_metadata)
    if not checkpoint:
        return {"status": "MISSING", "rows": _missing_checkpoint_rows(current)}
    status, rows = _compare_checkpoint_pairs(current, checkpoint)
    return {"status": status, "rows": rows}


def current_checkpoint_anchors(manifest: RunManifest) -> dict[str, object | None]:
    snapshots = input_snapshots(manifest)
    return {
        "manifest_id": manifest.manifest_id,
        "execution_fingerprint": manifest.execution_fingerprint,
        "effective_config_hash": manifest.code_provenance.effective_config_hash,
        "effective_config_artifact_id": (
            manifest.code_provenance.effective_config_artifact_id
        ),
        "input_snapshot_fingerprint": input_snapshot_fingerprint(snapshots),
        "composite_run_identity": composite_run_identity(manifest),
    }


def checkpoint_pair_status(
    current_value: object | None,
    checkpoint_value: object | None,
) -> str:
    if not is_present(current_value) and not is_present(checkpoint_value):
        return "N/A"
    if not is_present(current_value) or not is_present(checkpoint_value):
        return "MISSING"
    return "OK" if current_value == checkpoint_value else "MISMATCH"


def checkpoint_row(
    name: str,
    current_value: object | None,
    checkpoint_value: object | None,
    status: str,
) -> dict[str, object]:
    return {
        "anchor": name,
        "source_type": "checkpoint_metadata_compare",
        "source_quality": "derived",
        "drilldown_type": "checkpoint_compare",
        "drilldown_target": f"checkpoint.compare:{name}",
        "current_value_short": short_value(current_value),
        "current_value_full": format_full_value(current_value),
        "checkpoint_value_short": short_value(checkpoint_value),
        "checkpoint_value_full": format_full_value(checkpoint_value),
        "status": status,
        "ui_status": {
            "OK": "OK",
            "MISMATCH": "CRIT",
            "MISSING": "WARN",
            "N/A": "OK",
        }.get(
            status,
            "WARN",
        ),
    }
