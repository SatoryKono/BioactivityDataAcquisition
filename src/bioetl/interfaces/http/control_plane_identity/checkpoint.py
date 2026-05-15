"""Checkpoint anchor comparison for Control Plane identity evidence."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest
from bioetl.interfaces.http.control_plane_identity.extractors import (
    checkpoint_anchor_payload,
    composite_run_identity,
    input_snapshot_fingerprint,
    input_snapshots,
)
from bioetl.interfaces.http.control_plane_identity.formatting import (
    format_full_value,
    is_present,
    short_value,
)
from bioetl.interfaces.http.control_plane_identity.specs import CHECKPOINT_ANCHORS


def build_checkpoint_compare(manifest: RunManifest | None) -> dict[str, object]:
    if manifest is None:
        return {"status": "UNKNOWN", "rows": []}
    current = current_checkpoint_anchors(manifest)
    checkpoint = checkpoint_anchor_payload(manifest)
    if not checkpoint:
        return {
            "status": "MISSING",
            "rows": [
                checkpoint_row(name, current.get(name), None, "MISSING")
                for name in CHECKPOINT_ANCHORS
                if is_present(current.get(name))
            ],
        }
    rows: list[dict[str, object]] = []
    statuses: list[str] = []
    for name in CHECKPOINT_ANCHORS:
        current_value = current.get(name)
        checkpoint_value = checkpoint.get(name)
        status = checkpoint_pair_status(current_value, checkpoint_value)
        statuses.append(status)
        rows.append(checkpoint_row(name, current_value, checkpoint_value, status))
    if "MISMATCH" in statuses:
        status = "MISMATCH"
    elif "MISSING" in statuses and "OK" in statuses:
        status = "PARTIAL"
    elif all(item == "MISSING" for item in statuses):
        status = "MISSING"
    elif all(item in {"OK", "N/A"} for item in statuses):
        status = "OK"
    else:
        status = "PARTIAL"
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
