"""Checkpoint and lineage protection helpers for lifecycle planning."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from bioetl.domain.control_plane import ControlPlaneArtifactSurface
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_surfaces import (
    iter_surface_files,
    lineage_fragment_files,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_payloads import (
    _is_payload_stale,
    _lineage_fragment_id_candidates,
    _manifest_or_run_is_protected,
    _payload_text,
    _read_json_object_or_empty,
)


def collect_checkpoint_protections(
    *,
    base_path: Path,
    cutoff: datetime,
    refs: Any,  # Any: Mutable collector object with .checkpoint_ids set
) -> None:
    for checkpoint_path in iter_surface_files(
        base_path, ControlPlaneArtifactSurface.CHECKPOINT
    ):
        payload = _read_json_object_or_empty(checkpoint_path)
        if not payload or _is_payload_stale(checkpoint_path, payload, cutoff):
            continue
        record_checkpoint_protections(payload=payload, refs=refs)


def record_checkpoint_protections(
    *,
    payload: dict[str, object],
    refs: Any,  # Any: Mutable collector object with .run_ids, .manifest_ids, .effective_config_artifact_ids sets
) -> None:
    run_id = _payload_text(payload, "run_id")
    if run_id is not None:
        refs.run_ids.add(run_id)
    manifest_id = _payload_text(payload, "manifest_id")
    if manifest_id is not None:
        refs.manifest_ids.add(manifest_id)
    artifact_id = _payload_text(payload, "effective_config_artifact_id")
    if artifact_id is not None:
        refs.effective_config_artifact_ids.add(artifact_id)


def collect_lineage_protections(
    *,
    base_path: Path,
    refs: Any,  # Any: Mutable collector object with .manifest_ids, .lineage_fragment_ids sets
) -> None:
    manifest_ids = frozenset(refs.manifest_ids)
    run_ids = frozenset(refs.run_ids)
    evidence_floor_manifest_ids = frozenset(refs.evidence_floor_manifest_ids)
    evidence_floor_run_ids = frozenset(refs.evidence_floor_run_ids)
    for fragment_path in lineage_fragment_files(base_path):
        payload = _read_json_object_or_empty(fragment_path)
        if not payload:
            continue
        if _manifest_or_run_is_protected(
            payload,
            manifest_ids=manifest_ids,
            run_ids=run_ids,
        ):
            refs.lineage_fragment_ids.update(_lineage_fragment_id_candidates(payload))
        if _manifest_or_run_is_protected(
            payload,
            manifest_ids=evidence_floor_manifest_ids,
            run_ids=evidence_floor_run_ids,
        ):
            refs.evidence_floor_lineage_fragment_ids.update(
                _lineage_fragment_id_candidates(payload)
            )
