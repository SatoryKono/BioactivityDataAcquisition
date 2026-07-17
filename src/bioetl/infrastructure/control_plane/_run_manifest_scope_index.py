"""Atomic low-cardinality index records for latest run manifests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from bioetl.domain.types import RunType
from bioetl.infrastructure.storage.atomic import atomic_write_text

_INDEX_SCHEMA_VERSION = 1
_INDEX_DIR = "_latest_by_scope"
_CATALOG_FILE = "_catalog.json"


@dataclass(frozen=True, slots=True)
class LatestScopeIndexRecord:
    """Validated latest-manifest pointer for one exact scope."""

    pipeline_name: str
    run_type: RunType
    manifest_id: str


@dataclass(frozen=True, slots=True)
class LatestScopeIndexCatalog:
    """Completeness marker and known-scope catalog for bounded lookups."""

    complete: bool
    scopes: tuple[tuple[str, RunType], ...]


def latest_scope_index_path(
    base_path: Path,
    pipeline_name: str,
    run_type: RunType,
) -> Path:
    """Return a traversal-safe deterministic path for one scope record."""
    encoded_pipeline = quote(pipeline_name, safe="")
    return base_path / _INDEX_DIR / encoded_pipeline / f"{run_type.value}.json"


def latest_scope_catalog_path(base_path: Path) -> Path:
    """Return the single atomic catalog path for the scope index."""
    return base_path / _INDEX_DIR / _CATALOG_FILE


def _validate_scope_item(item: dict) -> tuple[str, RunType]:
    """Validate a single scope item and return the parsed tuple."""
    if not isinstance(item, dict):
        raise ValueError("latest-scope catalog scope must be a JSON object")
    pipeline_name = item.get("pipeline_name")
    run_type_value = item.get("run_type")
    if not isinstance(pipeline_name, str) or not pipeline_name:
        raise ValueError("latest-scope catalog pipeline_name is malformed")
    try:
        run_type = RunType(run_type_value)
    except (TypeError, ValueError) as error:
        raise ValueError("latest-scope catalog run_type is malformed") from error
    return (pipeline_name, run_type)


def load_latest_scope_catalog(path: Path) -> LatestScopeIndexCatalog | None:
    """Load the catalog marker, rejecting malformed or ambiguous state."""
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("latest-scope catalog payload must be a JSON object")
    if payload.get("schema_version") != _INDEX_SCHEMA_VERSION:
        raise ValueError("latest-scope catalog schema_version is unsupported")
    complete = payload.get("complete")
    scopes_payload = payload.get("scopes")
    if not isinstance(complete, bool) or not isinstance(scopes_payload, list):
        raise ValueError("latest-scope catalog fields are malformed")
    scopes: list[tuple[str, RunType]] = []
    for item in scopes_payload:
        scope = _validate_scope_item(item)
        if scope in scopes:
            raise ValueError("latest-scope catalog contains a duplicate scope")
        scopes.append(scope)
    if scopes != sorted(scopes, key=lambda item: (item[0], item[1].value)):
        raise ValueError("latest-scope catalog scopes are not deterministic")
    return LatestScopeIndexCatalog(complete=complete, scopes=tuple(scopes))


def load_latest_scope_index(
    path: Path,
    *,
    pipeline_name: str,
    run_type: RunType,
) -> LatestScopeIndexRecord | None:
    """Load and validate an exact-scope index record when it exists."""
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("latest-scope index payload must be a JSON object")
    if payload.get("schema_version") != _INDEX_SCHEMA_VERSION:
        raise ValueError("latest-scope index schema_version is unsupported")
    indexed_pipeline = payload.get("pipeline_name")
    indexed_run_type = payload.get("run_type")
    manifest_id = payload.get("manifest_id")
    if indexed_pipeline != pipeline_name or indexed_run_type != run_type.value:
        raise ValueError("latest-scope index record does not match its requested scope")
    if not isinstance(manifest_id, str) or not manifest_id.strip():
        raise ValueError("latest-scope index manifest_id must be a non-empty string")
    return LatestScopeIndexRecord(
        pipeline_name=pipeline_name,
        run_type=run_type,
        manifest_id=manifest_id,
    )


def write_latest_scope_index(path: Path, record: LatestScopeIndexRecord) -> None:
    """Atomically persist one exact-scope latest-manifest pointer."""
    atomic_write_text(
        path,
        json.dumps(
            {
                "manifest_id": record.manifest_id,
                "pipeline_name": record.pipeline_name,
                "run_type": record.run_type.value,
                "schema_version": _INDEX_SCHEMA_VERSION,
            },
            indent=2,
            sort_keys=True,
        ),
    )


def write_latest_scope_catalog(path: Path, catalog: LatestScopeIndexCatalog) -> None:
    """Atomically persist the completeness marker and known scopes."""
    atomic_write_text(
        path,
        json.dumps(
            {
                "complete": catalog.complete,
                "schema_version": _INDEX_SCHEMA_VERSION,
                "scopes": [
                    {"pipeline_name": pipeline_name, "run_type": run_type.value}
                    for pipeline_name, run_type in catalog.scopes
                ],
            },
            indent=2,
            sort_keys=True,
        ),
    )


def read_optional_text(path: Path) -> str | None:
    """Read an existing text file for transactional rollback."""
    return path.read_text(encoding="utf-8") if path.exists() else None


def restore_optional_text(path: Path, previous: str | None) -> None:
    """Restore one file to its pre-transaction state."""
    if previous is None:
        if path.exists():
            path.unlink()
        return
    atomic_write_text(path, previous)


__all__ = [
    "LatestScopeIndexCatalog",
    "LatestScopeIndexRecord",
    "latest_scope_catalog_path",
    "latest_scope_index_path",
    "load_latest_scope_catalog",
    "load_latest_scope_index",
    "read_optional_text",
    "restore_optional_text",
    "write_latest_scope_catalog",
    "write_latest_scope_index",
]
