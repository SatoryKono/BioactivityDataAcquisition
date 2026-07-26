"""Manifest protection helpers for control-plane lifecycle planning."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from bioetl.domain.control_plane import ControlPlaneArtifactSurface
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    resolve_reproducibility_family_profile,
)
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_surfaces import (
    INDEX_DIR_NAMES,
    iter_surface_files,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_payloads import (
    _effective_config_artifact_id,
    _input_snapshot_ids,
    _is_payload_stale,
    _optional_text,
    _read_json_object_or_empty,
)

_EVIDENCE_FLOOR_PROFILES = STRICT_PERSISTENCE_PROFILES


def collect_manifest_protections(
    *,
    base_path: Path,
    cutoff: datetime,
    refs: Any,  # Any: Mutable collector object with .manifest_ids, .evidence_floor_manifest_ids, .run_ids sets
    allow_profile_floor_violation: bool,
) -> None:
    for manifest_path in iter_surface_files(
        base_path, ControlPlaneArtifactSurface.RUN_MANIFEST
    ):
        if manifest_path.parent.name in INDEX_DIR_NAMES:
            continue
        payload = _read_json_object_or_empty(manifest_path)
        if not payload:
            continue
        is_stale = _is_payload_stale(manifest_path, payload, cutoff)
        if not is_stale:
            record_manifest_protections(
                path=manifest_path,
                payload=payload,
                refs=refs,
                evidence_floor=False,
            )
            continue
        if allow_profile_floor_violation or not requires_evidence_floor(payload):
            continue
        record_manifest_protections(
            path=manifest_path,
            payload=payload,
            refs=refs,
            evidence_floor=True,
        )


def record_manifest_protections(
    *,
    path: Path,
    payload: dict[str, object],
    refs: Any,  # Any: Mutable collector object with .manifest_ids, .evidence_floor_manifest_ids, .run_ids sets
    evidence_floor: bool,
) -> None:
    manifest_id = str(payload.get("manifest_id") or path.stem)
    refs.manifest_ids.add(manifest_id)
    if evidence_floor:
        refs.evidence_floor_manifest_ids.add(manifest_id)
    run_id = _optional_text(payload.get("run_id"))
    if run_id is not None:
        refs.run_ids.add(run_id)
        if evidence_floor:
            refs.evidence_floor_run_ids.add(run_id)
    replay_manifest_id = _optional_text(payload.get("replay_of_manifest_id"))
    if replay_manifest_id is not None:
        refs.manifest_ids.add(replay_manifest_id)
    artifact_id = _effective_config_artifact_id(payload)
    if artifact_id is not None:
        refs.effective_config_artifact_ids.add(artifact_id)
        if evidence_floor:
            refs.evidence_floor_effective_config_artifact_ids.add(artifact_id)
    snapshot_ids = _input_snapshot_ids(payload)
    refs.input_snapshot_ids.update(snapshot_ids)
    if evidence_floor:
        refs.evidence_floor_input_snapshot_ids.update(snapshot_ids)


def requires_evidence_floor(payload: dict[str, object]) -> bool:
    profile = required_persistence_profile(payload)
    return profile in _EVIDENCE_FLOOR_PROFILES or supports_historical_replay_floor(
        payload
    )


def required_persistence_profile(payload: dict[str, object]) -> str:
    launch_context = payload.get("launch_context")
    if isinstance(launch_context, dict):
        profile = _optional_text(launch_context.get("required_persistence_profile"))
        if profile is not None:
            return profile
    return _optional_text(payload.get("required_persistence_profile")) or ""


def supports_historical_replay_floor(payload: dict[str, object]) -> bool:
    provider = _optional_text(payload.get("provider"))
    entity = _optional_text(payload.get("entity"))
    if provider is None or entity is None:
        return False
    contract_ref = payload_contract_ref(payload) or f"{provider}.{entity}"
    try:
        profile = resolve_reproducibility_family_profile(
            provider=provider,
            entity=entity,
            contract_ref=contract_ref,
            execution_context=payload_execution_context(payload),
        )
    except ValueError:
        return False
    return (
        profile.broader_historical_exact_replay_policy
        == "certified_historical_exact_replay_tranche_supported"
    )


def payload_contract_ref(payload: dict[str, object]) -> str | None:
    provenance = payload.get("code_provenance")
    if not isinstance(provenance, dict):
        return None
    return _optional_text(provenance.get("contract_ref"))


def payload_execution_context(
    payload: dict[str, object],
) -> Literal["source", "composite"]:
    launch_context = payload.get("launch_context")
    if isinstance(launch_context, dict):
        execution_context = _optional_text(launch_context.get("execution_context"))
        if execution_context == "composite":
            return "composite"
        if execution_context == "source":
            return "source"
    if _optional_text(payload.get("provider")) == "composite":
        return "composite"
    return "source"
