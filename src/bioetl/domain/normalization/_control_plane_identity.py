"""Identity and anchor normalization helpers for control-plane payloads."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

_EXECUTION_IDENTITY_SHA256_FIELDS = frozenset(
    {
        "dq_contract_compatibility_hash",
        "effective_config_hash",
        "input_snapshot_fingerprint",
    }
)
_RUNTIME_ANCHOR_SHA256_FIELDS = frozenset(
    {
        "config_hash",
        "contract_schema_hash",
        "dq_contract_compatibility_hash",
        "resolved_config_hash",
        "effective_config_hash",
    }
)
_SEMVER_PARTS = 3
_CONTRACT_REF_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def normalize_control_plane_opaque_hash_ref(value: object | None) -> str | None:
    """Normalize an optional opaque hash-like reference without strict validation."""
    normalized = _normalize_optional_text(value)
    if normalized is None:
        return None
    return normalized.lower() or None


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
    parts = _strip_contract_version_prefix(normalized).split(".")
    _validate_contract_version_parts(parts, normalized)
    return ".".join(_pad_contract_version_parts(parts))


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
    """Normalize canonical execution-identity fields to stable comparable strings."""
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


def _normalize_optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_runtime_anchor_value(key: str, value: object | None) -> str | None:
    if key == "effective_config_hash":
        return normalize_runtime_anchor_effective_config_hash(value)
    if key in _RUNTIME_ANCHOR_SHA256_FIELDS:
        return normalize_control_plane_opaque_hash_ref(value)
    if key == "contract_ref":
        return normalize_contract_ref(value)
    if key == "contract_version":
        return normalize_contract_version(value)
    return _normalize_optional_text(value)


def _normalize_execution_identity_value(
    key: str,
    value: object | None,
) -> str | None:
    direct_normalizer = _EXECUTION_IDENTITY_FIELD_NORMALIZERS.get(key)
    if direct_normalizer is not None:
        return direct_normalizer(value)
    if key in _EXECUTION_IDENTITY_SHA256_FIELDS:
        return normalize_control_plane_opaque_hash_ref(value)
    return _normalize_optional_text(value)


def _normalize_optional_bool_token(value: object | None) -> str | None:
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
    if value.lower().startswith("sha256:"):
        return value.split(":", 1)[1]
    return value


def _strip_contract_version_prefix(value: str) -> str:
    if value.lower().startswith("v"):
        return value[1:]
    return value


def _validate_contract_version_parts(parts: list[str], normalized: str) -> None:
    if not all(part.isdigit() for part in parts):
        raise ValueError(
            f"Invalid contract_version format: {normalized!r} (expected numeric semver)"
        )
    if len(parts) > _SEMVER_PARTS:
        raise ValueError(
            f"Invalid contract_version format: {normalized!r} (expected X.Y.Z)"
        )


def _pad_contract_version_parts(parts: list[str]) -> list[str]:
    while len(parts) < _SEMVER_PARTS:
        parts.append("0")
    return parts


__all__ = [
    "build_execution_identity_payload",
    "normalize_contract_ref",
    "normalize_contract_version",
    "normalize_control_plane_opaque_hash_ref",
    "normalize_control_plane_sha256",
    "normalize_control_plane_strict_sha256",
    "normalize_execution_identity_payload",
    "normalize_runtime_anchor_effective_config_hash",
    "normalize_runtime_anchor_payload",
]
