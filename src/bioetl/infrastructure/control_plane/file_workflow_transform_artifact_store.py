"""File-backed workflow transform artifact persistence."""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileWorkflowTransformArtifactStore"]

_SCHEMA_VERSION = 1
_DEFAULT_DEBUG_EXPORT_ROOT = "artifacts/debug_exports"
_RESULT_FILE_NAME = "result.json"
_SUMMARY_FILE_NAME = "summary.json"


@dataclass(slots=True)
class FileWorkflowTransformArtifactStore:
    """Persist workflow transform artifacts under local control-plane roots."""

    base_path: Path
    clock: object
    _debug_refs: dict[tuple[str, str], tuple[dict[str, object], ...]] = field(
        default_factory=dict
    )

    def write_reconcile_result_artifact(
        self,
        *,
        context: object,
        payload: Mapping[str, object],
    ) -> tuple[Mapping[str, object], ...]:
        """Persist the compact normal-mode reconcile result artifact."""
        workflow_run_id = _required_attr(context, "workflow_run_id")
        step_id = _required_attr(context, "step_id")
        artifact_dir = self.base_path / workflow_run_id / step_id
        result_path = artifact_dir / _RESULT_FILE_NAME
        debug_refs = self._debug_refs.pop((workflow_run_id, step_id), ())
        payload_to_write = {
            "schema_version": _SCHEMA_VERSION,
            "created_at": _created_at_iso(context, self.clock),
            **dict(payload),
            "artifact_refs": list(debug_refs),
        }
        _write_json(result_path, payload_to_write)
        result_ref = _artifact_ref(
            artifact_type="workflow_transform_result",
            path=result_path,
            row_count=None,
        )
        return (*debug_refs, result_ref)

    def write_reconcile_debug_artifacts(
        self,
        *,
        context: object,
        request: object,
        result: object,
        retained_rows: tuple[Mapping[str, object], ...],
        orphan_rows: tuple[Mapping[str, object], ...],
    ) -> tuple[Mapping[str, object], ...]:
        """Persist row-level debug artifacts for one reconcile result."""
        if not bool(getattr(context, "debug_export_enabled", False)):
            return ()
        workflow_run_id = _required_attr(context, "workflow_run_id")
        step_id = _required_attr(context, "step_id")
        root = _debug_root(context) / _required_attr(context, "workflow_name")
        artifact_dir = root / "workflow_transforms" / workflow_run_id / step_id
        source_keys = tuple(
            str(item) for item in _attr_tuple(request, "effective_source_keys")
        )
        primary_keys = tuple(str(item) for item in _attr_tuple(request, "primary_keys"))
        refs = [
            _write_json_artifact(
                artifact_dir / _SUMMARY_FILE_NAME,
                {
                    "schema_version": _SCHEMA_VERSION,
                    "created_at": _created_at_iso(context, self.clock),
                    "workflow_name": getattr(context, "workflow_name", None),
                    "workflow_run_id": workflow_run_id,
                    "manifest_id": getattr(context, "manifest_id", None),
                    "step_id": step_id,
                    "transform_name": getattr(context, "transform_name", None),
                    "source_table": getattr(request, "source_table", None),
                    "reference_table": getattr(request, "reference_table", None),
                    "source_layer": getattr(request, "source_layer", None),
                    "reference_layer": getattr(request, "reference_layer", None),
                    "mutation_layer": getattr(result, "mutation_layer", None),
                    "scanned_rows": getattr(result, "scanned_rows", None),
                    "retained_rows": getattr(result, "retained_rows", None),
                    "orphan_rows_deleted": getattr(result, "orphan_rows_deleted", None),
                    "mutated": getattr(result, "mutated", None),
                    "dry_run": getattr(result, "dry_run", None),
                    "would_mutate": getattr(result, "would_mutate", None),
                    "mutation_mode": getattr(result, "mutation_mode", None),
                    "quarantine_rows_written": getattr(
                        result,
                        "quarantine_rows_written",
                        None,
                    ),
                    "quarantine_error_code": getattr(
                        result,
                        "quarantine_error_code",
                        None,
                    ),
                },
                artifact_type="workflow_transform_debug_summary",
            ),
            _write_csv_artifact(
                artifact_dir / "orphan_keys.csv",
                _key_rows(orphan_rows, (*primary_keys, *source_keys)),
                artifact_type="workflow_transform_orphan_keys",
            ),
            _write_csv_artifact(
                artifact_dir / "orphan_rows.csv",
                orphan_rows,
                artifact_type="workflow_transform_orphan_rows",
            ),
            _write_csv_artifact(
                artifact_dir / "retained_keys.csv",
                _key_rows(retained_rows, (*primary_keys, *source_keys)),
                artifact_type="workflow_transform_retained_keys",
            ),
        ]
        normalized_refs = tuple(dict(ref) for ref in refs)
        self._debug_refs[(workflow_run_id, step_id)] = normalized_refs
        return normalized_refs


def _debug_root(context: object) -> Path:
    configured = Path(
        str(getattr(context, "debug_export_dir", None) or _DEFAULT_DEBUG_EXPORT_ROOT)
    )
    if not configured.is_absolute():
        configured = Path.cwd() / configured
    return configured


def _created_at_iso(context: object, clock: object) -> str:
    value = getattr(context, "created_at", None)
    if isinstance(value, datetime):
        return value.isoformat()
    now = getattr(clock, "now", None)
    if callable(now):
        current = now()
        if isinstance(current, datetime):
            return current.isoformat()
    raise RuntimeError("Workflow transform artifact clock must expose now()")


def _required_attr(context: object, name: str) -> str:
    value = getattr(context, name, None)
    if value is None or not str(value).strip():
        raise ValueError(f"workflow transform artifact context requires {name}")
    return str(value)


def _attr_tuple(source: object, name: str) -> tuple[object, ...]:
    value = getattr(source, name, ())
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return ()


def _write_json_artifact(
    path: Path,
    payload: Mapping[str, object],
    *,
    artifact_type: str,
) -> dict[str, object]:
    _write_json(path, payload)
    return _artifact_ref(
        artifact_type=artifact_type,
        path=path,
        row_count=None,
    )


def _write_csv_artifact(
    path: Path,
    rows: tuple[Mapping[str, object], ...],
    *,
    artifact_type: str,
) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = _collect_headers(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})
    return _artifact_ref(
        artifact_type=artifact_type,
        path=path,
        row_count=len(rows),
    )


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    atomic_write_text(
        path,
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n",
    )


def _artifact_ref(
    *,
    artifact_type: str,
    path: Path,
    row_count: int | None,
) -> dict[str, object]:
    payload = path.read_bytes()
    ref: dict[str, object] = {
        "type": artifact_type,
        "path": str(path),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    if row_count is not None:
        ref["row_count"] = row_count
    return ref


def _collect_headers(rows: tuple[Mapping[str, object], ...]) -> list[str]:
    headers: list[str] = []
    for row in rows:
        for key in row:
            if key not in headers:
                headers.append(str(key))
    return headers


def _key_rows(
    rows: tuple[Mapping[str, object], ...],
    keys: tuple[str, ...],
) -> tuple[Mapping[str, object], ...]:
    unique_keys = tuple(dict.fromkeys(key for key in keys if key))
    return tuple({key: row.get(key) for key in unique_keys} for row in rows)


def _csv_value(value: object) -> object:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_jsonable(value), sort_keys=True)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value
