"""Payload and identity helpers for control-plane artifact lifecycle planning."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from bioetl.domain.control_plane import ControlPlaneArtifactSurface

__all__ = [
    "_artifact_id",
    "_content_addressed_file_snapshot_id",
    "_effective_config_artifact_id",
    "_indexed_stem",
    "_input_snapshot_ids",
    "_is_payload_stale",
    "_lineage_fragment_id_candidates",
    "_manifest_or_run_is_protected",
    "_optional_text",
    "_parse_datetime",
    "_payload_text",
    "_payload_value",
    "_read_json_object_or_empty",
    "_resolve_lifecycle_reason",
    "_resolve_payload_or_file_time",
]


def _read_json_object_or_empty(path: Path) -> dict[str, object]:
    """Best-effort JSON object read for planner metadata."""
    if path.suffix not in {".json", ".jsonl"}:
        return {}
    try:
        if path.suffix == ".jsonl":
            line = next(
                (
                    item
                    for item in path.read_text(encoding="utf-8").splitlines()
                    if item
                ),
                "",
            )
            if not line:
                return {}
            payload = json.loads(line)
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, StopIteration, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items()}


def _is_payload_stale(path: Path, payload: dict[str, object], cutoff: datetime) -> bool:
    created_at = _resolve_payload_or_file_time(path, payload)
    return created_at is not None and created_at < cutoff


def _resolve_payload_or_file_time(
    path: Path,
    payload: dict[str, object],
) -> datetime | None:
    for key in ("created_at", "updated_at", "occurred_at"):
        timestamp = _parse_datetime(_payload_value(payload, key))
        if timestamp is not None:
            return timestamp
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except OSError:
        return None


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        timestamp = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _artifact_id(
    *,
    surface: ControlPlaneArtifactSurface,
    path: Path,
    payload: dict[str, object],
) -> str:
    if surface is ControlPlaneArtifactSurface.RUN_MANIFEST:
        return str(payload.get("manifest_id") or path.stem)
    if surface is ControlPlaneArtifactSurface.RUN_LEDGER:
        return str(payload.get("manifest_id") or path.stem)
    if surface is ControlPlaneArtifactSurface.EFFECTIVE_CONFIG:
        return str(payload.get("artifact_id") or path.stem)
    if surface is ControlPlaneArtifactSurface.LINEAGE:
        return str(
            payload.get("stored_fragment_id") or payload.get("fragment_id") or path.stem
        )
    if surface is ControlPlaneArtifactSurface.CHECKPOINT:
        return (
            _payload_text(payload, "manifest_id")
            or _payload_text(payload, "run_id")
            or path.stem
        )
    if surface is ControlPlaneArtifactSurface.CACHED_BRONZE:
        return _content_addressed_file_snapshot_id(path)
    return path.stem


def _effective_config_artifact_id(payload: dict[str, object]) -> str | None:
    code_provenance = payload.get("code_provenance")
    if not isinstance(code_provenance, dict):
        return None
    return _optional_text(code_provenance.get("effective_config_artifact_id"))


def _input_snapshot_ids(payload: dict[str, object]) -> tuple[str, ...]:
    source_refs = payload.get("source_refs")
    if not isinstance(source_refs, list):
        return ()
    snapshot_ids: list[str] = []
    for source_ref in source_refs:
        if not isinstance(source_ref, dict):
            continue
        input_snapshots = source_ref.get("input_snapshots")
        if not isinstance(input_snapshots, list):
            continue
        for input_snapshot in input_snapshots:
            if not isinstance(input_snapshot, dict):
                continue
            snapshot_id = _optional_text(input_snapshot.get("snapshot_id"))
            if snapshot_id is not None:
                snapshot_ids.append(snapshot_id)
    return tuple(snapshot_ids)


def _payload_text(payload: dict[str, object], key: str) -> str | None:
    return _optional_text(_payload_value(payload, key))


def _payload_value(payload: dict[str, object], key: str) -> object:
    if key in payload:
        return payload.get(key)
    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and key in metadata:
        return metadata.get(key)
    return None


def _content_addressed_file_snapshot_id(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return f"unreadable:{path.stem}"
    return f"sha256:{digest.hexdigest()}"


def _indexed_stem(path: Path) -> str | None:
    if path.parent.name not in {
        "_by_fragment_id",
        "_by_manifest_id",
        "_by_node_id",
        "_by_run_id",
        "_occurrences",
    }:
        return None
    return path.stem


def _lineage_fragment_id_candidates(payload: dict[str, object]) -> tuple[str, ...]:
    candidates = (
        _optional_text(payload.get("stored_fragment_id")),
        _optional_text(payload.get("fragment_id")),
    )
    return tuple(candidate for candidate in candidates if candidate)


def _manifest_or_run_is_protected(
    payload: dict[str, object],
    *,
    manifest_ids: frozenset[str],
    run_ids: frozenset[str],
) -> bool:
    manifest_id = _optional_text(payload.get("manifest_id"))
    run_id = _optional_text(payload.get("run_id"))
    return (manifest_id in manifest_ids) or (run_id in run_ids)


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_lifecycle_reason(*, stale: bool, protected_by: tuple[str, ...]) -> str:
    if protected_by:
        return "protected_reference"
    if stale:
        return "retention_expired"
    return "within_retention_window"
