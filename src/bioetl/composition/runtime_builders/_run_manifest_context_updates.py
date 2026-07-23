"""Control-plane context update helpers for run manifest attachment."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._run_manifest_identity_ref_values import (
    CONTRACT_IDENTITY_FIELD_NAMES,
    build_contract_identity_field_values_from_mapping,
    build_control_plane_identity_ref_values,
)
from bioetl.domain.normalization import normalize_runtime_anchor_payload

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext

__all__ = [
    "apply_manifest_updates_to_mutable_context",
    "build_dataclass_manifest_updates",
    "extract_optional_updates_from_refs",
    "iter_optional_control_plane_updates",
    "iter_optional_control_plane_updates_from_mapping",
]

_BASE_CONTROL_PLANE_CONTEXT_UPDATE_FIELDS: tuple[str, ...] = (
    "execution_fingerprint",
    "config_hash",
    "resolved_config_hash",
    "effective_config_hash",
    "source_fingerprint",
    "dq_contract_compatibility_hash",
    "effective_config_artifact_id",
    "replay_of_run_id",
    "replay_of_manifest_id",
    "input_snapshot_fingerprint",
)

_CONTROL_PLANE_CONTEXT_UPDATE_FIELDS: tuple[str, ...] = (
    _BASE_CONTROL_PLANE_CONTEXT_UPDATE_FIELDS + CONTRACT_IDENTITY_FIELD_NAMES
)


class _MutableManifestContext:
    manifest_id: str | None


def iter_optional_control_plane_updates(
    **fields: object,
) -> tuple[tuple[str, str], ...]:
    """Return non-empty control-plane context updates for runner attachment.

    Accepts the control-plane field names as kwargs (S107-friendly). Prefer
    ``iter_optional_control_plane_updates_from_mapping`` for bulk projection.
    """
    return iter_optional_control_plane_updates_from_mapping(fields)


def iter_optional_control_plane_updates_from_mapping(
    values: Mapping[str, object],
) -> tuple[tuple[str, str], ...]:
    """Project optional control-plane fields from a broader candidate mapping."""
    projected = {
        field_name: values.get(field_name)
        for field_name in _CONTROL_PLANE_CONTEXT_UPDATE_FIELDS
    }
    contract_identity_values = build_contract_identity_field_values_from_mapping(
        projected
    )
    normalized = normalize_runtime_anchor_payload(
        {
            "execution_fingerprint": projected.get("execution_fingerprint"),
            "config_hash": projected.get("config_hash"),
            "resolved_config_hash": projected.get("resolved_config_hash"),
            "effective_config_hash": projected.get("effective_config_hash"),
            "source_fingerprint": projected.get("source_fingerprint"),
            "dq_contract_compatibility_hash": projected.get(
                "dq_contract_compatibility_hash"
            ),
            "effective_config_artifact_id": projected.get(
                "effective_config_artifact_id"
            ),
            "replay_of_run_id": projected.get("replay_of_run_id"),
            "replay_of_manifest_id": projected.get("replay_of_manifest_id"),
            "input_snapshot_fingerprint": projected.get("input_snapshot_fingerprint"),
            **build_control_plane_identity_ref_values(
                contract_identity_values=contract_identity_values,
                required_persistence_profile=None,
            ),
        }
    )
    return tuple(
        (field_name, field_value)
        for field_name, field_value in normalized.items()
        if field_value is not None
    )


def extract_optional_updates_from_refs(
    control_plane_refs: object,
) -> tuple[tuple[str, str], ...]:
    """Extract optional control-plane updates from manifest refs."""
    return tuple(
        (field_name, field_value)
        for field_name in _CONTROL_PLANE_CONTEXT_UPDATE_FIELDS
        if (field_value := getattr(control_plane_refs, field_name, None)) is not None
    )


def build_dataclass_manifest_updates(
    ctx: PipelineRunContext,
    manifest_id: str,
    *,
    optional_updates: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    """Build dataclass replace() kwargs for manifest attachment."""
    updates: dict[str, object] = {"manifest_id": manifest_id}
    for field_name, field_value in optional_updates:
        if hasattr(ctx, field_name):
            updates[field_name] = field_value
    return updates


def apply_manifest_updates_to_mutable_context(
    ctx: _MutableManifestContext,
    manifest_id: str,
    *,
    optional_updates: tuple[tuple[str, str], ...],
) -> _MutableManifestContext:
    """Mutate a legacy mutable context with manifest/control-plane anchors."""
    ctx.manifest_id = manifest_id
    for field_name, field_value in optional_updates:
        setattr(ctx, field_name, field_value)
    return ctx
