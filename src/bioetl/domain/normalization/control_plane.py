"""Pure control-plane normalization helpers for manifests and ledger payloads."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence

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
    "build_execution_identity_payload",
    "normalize_contract_ref",
    "normalize_contract_version",
    "normalize_control_plane_datetime",
    "normalize_control_plane_opaque_hash_ref",
    "normalize_control_plane_sha256",
    "normalize_control_plane_strict_sha256",
    "normalize_control_plane_uuid",
    "normalize_execution_identity_payload",
    "normalize_run_ledger_payload",
    "normalize_run_manifest_spec",
    "normalize_runtime_anchor_effective_config_hash",
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
_RUNTIME_ANCHOR_SHA256_FIELDS = frozenset(
    {
        "config_hash",
        "contract_schema_hash",
        "dq_contract_compatibility_hash",
        "effective_config_hash",
    }
)
_EXECUTION_IDENTITY_SHA256_FIELDS = frozenset(
    {
        "dq_contract_compatibility_hash",
        "effective_config_hash",
        "input_snapshot_fingerprint",
    }
)
_SEMVER_PARTS = 3
_CONTRACT_REF_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _normalize_optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_control_plane_opaque_hash_ref(value: object | None) -> str | None:
    """Normalize an optional opaque hash-like reference without strict validation."""
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    normalized = normalized.lower()
    return normalized or None


def normalize_control_plane_sha256(value: str | None) -> str | None:
    """Backward-compatible alias for opaque control-plane hash-like normalization."""
    return normalize_control_plane_opaque_hash_ref(value)


def normalize_control_plane_strict_sha256(value: object | None) -> str | None:
    """Return canonical lowercase 64-char SHA256 hex or fail closed."""
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    normalized = _strip_optional_sha256_prefix(normalized).lower()
    if not _SHA256_HEX_PATTERN.fullmatch(normalized):
        raise ValueError("Invalid SHA256 format: expected lowercase 64-char SHA256 hex")
    return normalized


def normalize_runtime_anchor_effective_config_hash(value: object | None) -> str | None:
    """Return canonical runtime-anchor effective_config_hash or fail closed."""
    try:
        return normalize_control_plane_strict_sha256(value)
    except ValueError as exc:
        raise ValueError(
            "Invalid effective_config_hash format: expected lowercase 64-char SHA256 hex"
        ) from exc


def normalize_contract_ref(value: object | None) -> str | None:
    """Return canonical contract reference text for runtime/checkpoint anchors."""
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    normalized = normalized.lower()
    if not _CONTRACT_REF_PATTERN.fullmatch(normalized):
        raise ValueError(
            f"Invalid contract_ref format: {normalized!r} (expected lowercase dotted identifier)"
        )
    return normalized


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


def normalize_execution_identity_payload(
    payload: Mapping[str, object | None],
) -> dict[str, str | None]:
    """Normalize canonical execution-identity fields to stable comparable strings.

    This payload is shared by manifest creation, checkpoint metadata assembly,
    and runtime-compatibility fallback anchors. Callers may provide a sparse
    subset of fields; missing keys simply remain absent from the normalized
    payload.
    """

    return {
        key: _normalize_execution_identity_value(key, value)
        for key, value in payload.items()
    }


def build_execution_identity_payload(
    *,
    pipeline_name: str | None,
    run_type: str | None,
    pipeline_version: str | None,
    effective_config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    contract_ref: str | None,
    contract_version: str | None,
    effective_config_artifact_id: str | None,
    exact_replay: bool | str | None,
    input_snapshot_fingerprint: str | None,
) -> dict[str, str | None]:
    """Build the canonical execution-identity payload shared across layers."""

    return normalize_execution_identity_payload(
        {
            "pipeline_name": pipeline_name,
            "run_type": run_type,
            "pipeline_version": pipeline_version,
            "effective_config_hash": effective_config_hash,
            "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
            "contract_ref": contract_ref,
            "contract_version": contract_version,
            "effective_config_artifact_id": effective_config_artifact_id,
            "exact_replay": exact_replay,
            "input_snapshot_fingerprint": input_snapshot_fingerprint,
        }
    )


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
    return normalize_control_plane_opaque_hash_ref(value)


def _normalize_runtime_anchor_value(key: str, value: object | None) -> str | None:
    """Normalize one runtime anchor field according to its canonical contract."""
    if key == "effective_config_hash":
        return normalize_runtime_anchor_effective_config_hash(value)
    if key in _RUNTIME_ANCHOR_SHA256_FIELDS:
        return _normalize_runtime_anchor_hash(value)
    if key == "contract_ref":
        return normalize_contract_ref(value)
    if key == "contract_version":
        return normalize_contract_version(value)
    return _normalize_optional_text(value)


def _normalize_execution_identity_value(
    key: str,
    value: object | None,
) -> str | None:
    """Normalize one canonical execution-identity field."""
    direct_normalizer = _EXECUTION_IDENTITY_FIELD_NORMALIZERS.get(key)
    if direct_normalizer is not None:
        return direct_normalizer(value)
    if key in _EXECUTION_IDENTITY_SHA256_FIELDS:
        return normalize_control_plane_opaque_hash_ref(value)
    return _normalize_optional_text(value)


def _normalize_optional_bool_token(value: object | None) -> str | None:
    """Return canonical lowercase bool tokens for execution-identity fields."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return _normalize_bool_text_token(value)


def _normalize_optional_lower_text(value: object | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return None if normalized is None else normalized.lower()


def _normalize_bool_text_token(value: object | None) -> str | None:
    normalized = _normalize_optional_lower_text(value)
    if normalized is None or normalized in {"true", "false"}:
        return normalized
    raise ValueError(
        "Invalid exact_replay format: expected a boolean or 'true'/'false' token"
    )


_EXECUTION_IDENTITY_FIELD_NORMALIZERS: dict[
    str,
    Callable[[object | None], str | None],
] = {
    "effective_config_hash": normalize_runtime_anchor_effective_config_hash,
    "contract_ref": normalize_contract_ref,
    "contract_version": normalize_contract_version,
    "exact_replay": _normalize_optional_bool_token,
    "run_type": _normalize_optional_lower_text,
}


def _strip_optional_sha256_prefix(value: str) -> str:
    """Remove an optional sha256: prefix before strict hash validation."""
    if value.lower().startswith("sha256:"):
        return value.split(":", 1)[1]
    return value


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
        normalized[field_name] = normalize_control_plane_opaque_hash_ref(value)


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
    _normalize_manifest_code_provenance_field(payload, normalized)
    _normalize_manifest_source_refs_field(payload, normalized)
    _normalize_manifest_set_like_fields(payload, normalized)
    return normalized


def _normalize_manifest_code_provenance_field(
    payload: Mapping[str, object],
    normalized: dict[str, object],
) -> None:
    """Normalize nested code provenance when present."""
    code_provenance = payload.get("code_provenance")
    if not isinstance(code_provenance, Mapping):
        return
    normalized["code_provenance"] = _normalize_manifest_code_provenance(code_provenance)


def _normalize_manifest_source_refs_field(
    payload: Mapping[str, object],
    normalized: dict[str, object],
) -> None:
    """Normalize nested source refs when present."""
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
    """Normalize remaining set-like manifest fields."""
    for field_name in _MANIFEST_SET_LIKE_FIELDS - {"source_refs"}:
        _normalize_manifest_set_like_field(payload, normalized, field_name)


def _normalize_manifest_set_like_field(
    payload: Mapping[str, object],
    normalized: dict[str, object],
    field_name: str,
) -> None:
    """Normalize one set-like manifest field when present."""
    raw_value = payload.get(field_name)
    if not _is_non_string_sequence(raw_value):
        return
    normalized[field_name] = canonicalize_container(normalize_set_like_sequence(raw_value))


def _is_non_string_sequence(value: object) -> bool:
    """Return whether the value is a sequence that should be canonicalized."""
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _normalize_manifest_source_ref(item: object) -> object:
    """Normalize one source-ref payload, including nested snapshot refs."""
    if not isinstance(item, Mapping):
        return item
    normalized = normalize_mapping(item)
    raw_snapshots = item.get("input_snapshots")
    if isinstance(raw_snapshots, Sequence) and not isinstance(raw_snapshots, (str, bytes)):
        normalized["input_snapshots"] = canonicalize_container(
            normalize_set_like_sequence(raw_snapshots)
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
