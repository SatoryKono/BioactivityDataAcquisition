"""Manifest and ledger normalization helpers for control-plane payloads."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import TypeGuard, cast

from bioetl.domain.normalization._control_plane_identity import (
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_opaque_hash_ref,
)
from bioetl.domain.normalization._control_plane_primitives import (
    canonicalize_container,
    normalize_mapping,
    normalize_optional_datetime,
    normalize_optional_uuid,
    normalize_run_ledger_details,
    normalize_run_ledger_metrics_snapshot,
    normalize_set_like_sequence,
)

_MANIFEST_SET_LIKE_FIELDS = frozenset({"source_refs", "planned_artifacts"})
_CODE_PROVENANCE_SHA256_FIELDS = frozenset(
    {
        "config_hash",
        "contract_schema_hash",
        "dq_contract_compatibility_hash",
        "resolved_config_hash",
        "effective_config_hash",
    }
)


def normalize_run_manifest_spec(payload: Mapping[str, object]) -> dict[str, object]:
    """Normalize a manifest fingerprint/persist payload into canonical primitives."""
    normalized = normalize_mapping(payload)
    _normalize_manifest_code_provenance_field(payload, normalized)
    _normalize_manifest_source_refs_field(payload, normalized)
    _normalize_manifest_set_like_fields(payload, normalized)
    return normalized


def normalize_run_ledger_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Normalize a ledger append payload into canonical primitives."""
    normalized = normalize_mapping(payload)
    if "run_id" in payload:
        normalized["run_id"] = normalize_optional_uuid(payload.get("run_id"))
    if "occurred_at" in payload:
        normalized["occurred_at"] = normalize_optional_datetime(
            payload.get("occurred_at")
        )
    metrics_snapshot = normalize_run_ledger_metrics_snapshot(
        payload.get("metrics_snapshot")
    )
    if metrics_snapshot is not None:
        normalized["metrics_snapshot"] = metrics_snapshot
    details = normalize_run_ledger_details(payload.get("details"))
    if details is not None:
        normalized["details"] = details
    return normalized


def _normalize_manifest_code_provenance(
    payload: Mapping[str, object] | None,
) -> dict[str, object]:
    if payload is None:
        return {}
    normalized = normalize_mapping(payload)
    _normalize_manifest_hash_fields(normalized)
    _apply_manifest_field_normalizer(
        normalized,
        field_name="contract_ref",
        normalizer=normalize_contract_ref,
    )
    _apply_manifest_field_normalizer(
        normalized,
        field_name="contract_version",
        normalizer=normalize_contract_version,
    )
    _apply_manifest_field_normalizer(
        normalized,
        field_name="effective_config_artifact_id",
        normalizer=_normalize_optional_text,
    )
    return normalized


def _normalize_manifest_hash_fields(normalized: dict[str, object]) -> None:
    for field_name in _CODE_PROVENANCE_SHA256_FIELDS:
        value = normalized.get(field_name)
        if value is None:
            continue
        normalized[field_name] = normalize_control_plane_opaque_hash_ref(value)


def _apply_manifest_field_normalizer(
    normalized: dict[str, object],
    *,
    field_name: str,
    normalizer: Callable[[object | None], object],
) -> None:
    if field_name not in normalized:
        return
    normalized[field_name] = normalizer(normalized.get(field_name))


def _normalize_manifest_code_provenance_field(
    payload: Mapping[str, object],
    normalized: dict[str, object],
) -> None:
    code_provenance = payload.get("code_provenance")
    if not isinstance(code_provenance, Mapping):
        return
    normalized["code_provenance"] = _normalize_manifest_code_provenance(code_provenance)


def _normalize_manifest_source_refs_field(
    payload: Mapping[str, object],
    normalized: dict[str, object],
) -> None:
    source_refs = payload.get("source_refs")
    if not _is_non_string_sequence(source_refs):
        return
    normalized["source_refs"] = canonicalize_container(
        normalize_set_like_sequence(
            _normalize_manifest_source_ref(item) for item in source_refs
        )
    )


def _normalize_manifest_set_like_fields(
    payload: Mapping[str, object],
    normalized: dict[str, object],
) -> None:
    for field_name in _MANIFEST_SET_LIKE_FIELDS - {"source_refs"}:
        _normalize_manifest_set_like_field(payload, normalized, field_name)


def _normalize_manifest_set_like_field(
    payload: Mapping[str, object],
    normalized: dict[str, object],
    field_name: str,
) -> None:
    raw_value = payload.get(field_name)
    if not _is_non_string_sequence(raw_value):
        return
    normalized[field_name] = canonicalize_container(
        normalize_set_like_sequence(raw_value)
    )


def _is_non_string_sequence(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _normalize_manifest_source_ref(item: object) -> object:
    if not isinstance(item, Mapping):
        return item
    normalized = normalize_mapping(item)
    raw_snapshots = item.get("input_snapshots")
    if isinstance(raw_snapshots, Sequence) and not isinstance(
        raw_snapshots, (str, bytes)
    ):
        normalized["input_snapshots"] = canonicalize_container(
            _normalize_manifest_input_snapshots(cast(Sequence[object], raw_snapshots))
        )
    return normalized


def _normalize_manifest_input_snapshots(
    raw_snapshots: Sequence[object],
) -> list[object]:
    """Normalize manifest snapshots with deterministic identity-first ordering."""
    normalized = [
        normalize_mapping(item) if isinstance(item, Mapping) else item
        for item in raw_snapshots
    ]
    return sorted(
        normalized,
        key=_manifest_snapshot_sort_key,
    )


def _manifest_snapshot_sort_key(item: object) -> tuple[str, str]:
    if not isinstance(item, Mapping):
        return ("", str(item))
    snapshot_id = item.get("snapshot_id", "")
    if snapshot_id is None:
        snapshot_id = ""
    return (str(snapshot_id), str(item))


def _normalize_optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "normalize_run_ledger_payload",
    "normalize_run_manifest_spec",
]
