"""Run-manifest lookup helpers for quarantine filtered-read views."""

from __future__ import annotations

import json
from pathlib import Path

from bioetl.domain.types import JsonDict

__all__ = ["_build_run_type_lookup"]


def _parse_run_type_from_manifest_payload(payload: object) -> str | None:
    """Extract run_type from one run-manifest JSON payload."""
    if not isinstance(payload, dict):
        return None
    candidate = payload.get("run_type")
    if not isinstance(candidate, str):
        return None
    normalized = candidate.strip()
    return normalized or None


def _resolve_run_manifest_root(base_path: str) -> Path | None:
    """Resolve run-manifest root directory from quarantine base path."""
    quarantine_root = Path(base_path).resolve()
    candidate_roots = (
        quarantine_root.parent / "control" / "run_manifest",
        quarantine_root.parent / "control_plane" / "run_manifest",
    )
    for root in candidate_roots:
        if (root / "_by_run_id").exists():
            return root
    return None


def _resolve_manifest_id(run_index_root: Path, run_id: str) -> str | None:
    try:
        return (run_index_root / f"{run_id}.txt").read_text(
            encoding="utf-8"
        ).strip() or None
    except OSError:
        return None


def _resolve_manifest_run_type(manifest_root: Path, manifest_id: str) -> str | None:
    try:
        payload = json.loads(
            (manifest_root / f"{manifest_id}.json").read_text(encoding="utf-8")
        )
        return _parse_run_type_from_manifest_payload(payload)
    except (OSError, json.JSONDecodeError):
        return None


def _build_run_type_lookup(
    table_records: list[JsonDict],
    *,
    base_path: str,
) -> dict[str, str]:
    """Build run_id -> run_type mapping from control-plane run manifests."""
    manifest_root = _resolve_run_manifest_root(base_path)
    if manifest_root is None:
        return {}

    run_index_root = manifest_root / "_by_run_id"
    run_type_by_run_id: dict[str, str] = {}
    manifest_run_type_cache: dict[str, str | None] = {}

    for record in table_records:
        run_id_raw = record.get("run_id")
        if not isinstance(run_id_raw, str):
            continue
        run_id = run_id_raw.strip()
        if not run_id or run_id in run_type_by_run_id:
            continue

        manifest_id = _resolve_manifest_id(run_index_root, run_id)
        if not manifest_id:
            continue

        if manifest_id not in manifest_run_type_cache:
            manifest_run_type_cache[manifest_id] = _resolve_manifest_run_type(
                manifest_root, manifest_id
            )

        run_type = manifest_run_type_cache.get(manifest_id)
        if run_type:
            run_type_by_run_id[run_id] = run_type

    return run_type_by_run_id
