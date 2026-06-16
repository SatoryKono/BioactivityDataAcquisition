"""Source manifest helpers for ChEMBL target protein-classification snapshots."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping

from bioetl.domain.types import JsonDict

_DATASET_VERSION = "target-protein-classification-path-v2.1.0"
_SOURCE_URL = "https://www.ebi.ac.uk/chembl/api/data/protein_classification"
_UNKNOWN_METADATA = "unknown"


def source_manifest(
    *,
    target_rows: Iterable[Mapping[str, object]],
    target_component_rows: Iterable[Mapping[str, object]],
    protein_class_rows: Iterable[Mapping[str, object]],
) -> JsonDict:
    """Build deterministic source metadata from local snapshot inputs."""
    target_rows_tuple = tuple(target_rows)
    target_component_rows_tuple = tuple(target_component_rows)
    protein_class_rows_tuple = tuple(protein_class_rows)
    return {
        "dataset_version": _DATASET_VERSION,
        "source_url": _SOURCE_URL,
        "chembl_release": _first_text(
            protein_class_rows_tuple,
            "chembl_release",
            "chembl_db_version",
            "db_version",
        ),
        "chembl_api_version": _first_text(
            protein_class_rows_tuple,
            "chembl_api_version",
            "api_version",
        ),
        "source_manifest_status": _manifest_status(protein_class_rows_tuple),
        "source_snapshot_fingerprint": _source_snapshot_fingerprint(
            target_rows=target_rows_tuple,
            target_component_rows=target_component_rows_tuple,
            protein_class_rows=protein_class_rows_tuple,
        ),
        "target_snapshot_row_count": len(target_rows_tuple),
        "target_component_snapshot_row_count": len(target_component_rows_tuple),
        "protein_class_snapshot_row_count": len(protein_class_rows_tuple),
    }


def with_source_manifest(
    row: JsonDict, source_manifest: Mapping[str, object]
) -> JsonDict:
    """Attach source manifest fields to one relation row."""
    enriched = dict(row)
    enriched.update(source_manifest)
    return enriched


def _first_text(
    rows: Iterable[Mapping[str, object]],
    *field_names: str,
) -> str:
    """Return the first non-empty metadata value from snapshot rows."""
    for row in rows:
        for field_name in field_names:
            value = row.get(field_name)
            if value is None:
                continue
            stripped = str(value).strip()
            if stripped:
                return stripped
    return _UNKNOWN_METADATA


def _manifest_status(rows: Iterable[Mapping[str, object]]) -> str:
    """Return whether release metadata was available in the local snapshot."""
    release = _first_text(rows, "chembl_release", "chembl_db_version", "db_version")
    api_version = _first_text(rows, "chembl_api_version", "api_version")
    if release == _UNKNOWN_METADATA or api_version == _UNKNOWN_METADATA:
        return "release_metadata_unavailable"
    return "release_metadata_available"


def _source_snapshot_fingerprint(
    *,
    target_rows: Iterable[Mapping[str, object]],
    target_component_rows: Iterable[Mapping[str, object]],
    protein_class_rows: Iterable[Mapping[str, object]],
) -> str:
    """Hash stable identifiers from source snapshots for manifest drift checks."""
    payload = {
        "targets": sorted(
            str(row.get("target_id"))
            for row in target_rows
            if row.get("target_id") is not None
        ),
        "target_components": sorted(
            str(row.get("component_id"))
            for row in target_component_rows
            if row.get("component_id") is not None
        ),
        "protein_classes": sorted(
            str(row.get("protein_class_id"))
            for row in protein_class_rows
            if row.get("protein_class_id") is not None
        ),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
