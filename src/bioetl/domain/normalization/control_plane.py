"""Pure control-plane normalization helpers for manifests and ledger payloads."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime

from bioetl.domain.normalization._control_plane_primitives import (
    canonicalize_container,
    normalize_control_plane_datetime,
    normalize_control_plane_uuid,
    normalize_mapping,
    normalize_optional_datetime,
    normalize_optional_uuid,
    normalize_run_ledger_details,
    normalize_run_ledger_metrics_snapshot,
    normalize_set_like_sequence,
)

__all__ = [
    "normalize_contract_ref",
    "normalize_contract_version",
    "normalize_control_plane_datetime",
    "normalize_control_plane_sha256",
    "normalize_control_plane_uuid",
    "normalize_run_ledger_payload",
    "normalize_run_manifest_spec",
    "normalize_runtime_anchor_payload",
]

_MANIFEST_SET_LIKE_FIELDS = frozenset({"source_refs", "planned_artifacts"})
_CODE_PROVENANCE_SHA256_FIELDS = frozenset(
    {
        "config_hash",
        "contract_schema_hash",
        "dq_contract_compatibility_hash",
    }
)
_SEMVER_PARTS = 3


def _normalize_optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_control_plane_sha256(value: str | None) -> str | None:
    """Normalize an optional hash-like value without enforcing policy strictness."""
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    normalized = normalized.lower()
    return normalized or None


def normalize_contract_ref(value: object | None) -> str | None:
    """Return canonical contract reference text for runtime/checkpoint anchors."""
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    return normalized.lower()


def normalize_contract_version(value: object | None) -> str | None:
    """Return canonical semver-style contract version for runtime anchors."""
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    normalized = _strip_contract_version_prefix(normalized)
    parts = normalized.split(".")
    _validate_contract_version_parts(parts, normalized)
    parts = _pad_contract_version_parts(parts)
    return ".".join(parts)


def normalize_runtime_anchor_payload(
    payload: Mapping[str, object | None],
) -> dict[str, str | None]:
    """Normalize checkpoint/runtime anchor fields to stable comparable strings."""
    return {
        key: _normalize_runtime_anchor_value(key, value)
        for key, value in payload.items()
    }


def _strip_contract_version_prefix(value: str) -> str:
    """Remove the optional leading v-prefix from contract versions."""
    if value.lower().startswith("v"):
        return value[1:]
    return value


def _validate_contract_version_parts(parts: list[str], normalized: str) -> None:
    """Validate numeric semver parts before canonical padding."""
    if not all(part.isdigit() for part in parts):
        raise ValueError(
            f"Invalid contract_version format: {normalized!r} (expected numeric semver)"
        )
    if len(parts) > _SEMVER_PARTS:
        raise ValueError(
            f"Invalid contract_version format: {normalized!r} (expected X.Y.Z)"
        )


def _pad_contract_version_parts(parts: list[str]) -> list[str]:
    """Pad shorter semver forms to the canonical three-part representation."""
    while len(parts) < _SEMVER_PARTS:
        parts.append("0")
    return parts


def _normalize_runtime_anchor_hash(value: object | None) -> str | None:
    """Normalize hash-like runtime anchor fields into canonical lowercase text."""
    return normalize_control_plane_sha256(None if value is None else str(value))


def _normalize_runtime_anchor_value(key: str, value: object | None) -> str | None:
    """Normalize one runtime anchor field according to its canonical contract."""
    if key == "effective_config_hash":
        return _normalize_runtime_anchor_hash(value)
    if key == "contract_ref":
        return normalize_contract_ref(value)
    if key == "contract_version":
        return normalize_contract_version(value)
    return _normalize_optional_text(value)


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
    """Normalize hash-like code provenance fields in place."""
    for field_name in _CODE_PROVENANCE_SHA256_FIELDS:
        value = normalized.get(field_name)
        if value is None:
            continue
        normalized[field_name] = normalize_control_plane_sha256(str(value))


def _apply_manifest_field_normalizer(
    normalized: dict[str, object],
    *,
    field_name: str,
    normalizer: Callable[[object | None], object],
) -> None:
    """Apply one optional-field normalizer when the field is present."""
    if field_name not in normalized:
        return
    normalized[field_name] = normalizer(normalized.get(field_name))


def normalize_run_manifest_spec(payload: Mapping[str, object]) -> dict[str, object]:
    """Normalize a manifest fingerprint/persist payload into canonical primitives."""
    normalized = normalize_mapping(payload)

    code_provenance = payload.get("code_provenance")
    if isinstance(code_provenance, Mapping):
        normalized["code_provenance"] = _normalize_manifest_code_provenance(code_provenance)

    for field_name in _MANIFEST_SET_LIKE_FIELDS:
        raw_value = payload.get(field_name)
        if isinstance(raw_value, Sequence) and not isinstance(raw_value, (str, bytes)):
            normalized[field_name] = canonicalize_container(
                normalize_set_like_sequence(raw_value)
            )

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
