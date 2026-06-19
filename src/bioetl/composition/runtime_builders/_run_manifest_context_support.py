"""Manifest context/provenance helpers kept separate from data-root refs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    CONTRACT_IDENTITY_FIELD_NAMES,
    build_contract_identity_field_values,
)
from bioetl.domain.normalization import normalize_runtime_anchor_payload

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext

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


class _MutableManifestContext(Protocol):
    manifest_id: str | None


def iter_optional_control_plane_updates(
    *,
    execution_fingerprint: str | None = None,
    config_hash: str | None = None,
    resolved_config_hash: str | None = None,
    effective_config_hash: str | None = None,
    source_fingerprint: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    replay_of_run_id: str | None = None,
    replay_of_manifest_id: str | None = None,
    input_snapshot_fingerprint: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    contract_schema_hash: str | None = None,
    dq_policy_ref: str | None = None,
    rule_bundle_version: str | None = None,
    normalization_profile_ref: str | None = None,
    normalization_profile_version: str | None = None,
    normalization_profile_hash: str | None = None,
) -> tuple[tuple[str, str], ...]:
    """Return non-empty control-plane context updates for runner attachment."""
    values = normalize_runtime_anchor_payload(
        {
            "execution_fingerprint": execution_fingerprint,
            "config_hash": config_hash,
            "resolved_config_hash": resolved_config_hash,
            "effective_config_hash": effective_config_hash,
            "source_fingerprint": source_fingerprint,
            "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
            "effective_config_artifact_id": effective_config_artifact_id,
            "replay_of_run_id": replay_of_run_id,
            "replay_of_manifest_id": replay_of_manifest_id,
            "input_snapshot_fingerprint": input_snapshot_fingerprint,
            **build_contract_identity_field_values(
                contract_ref=contract_ref,
                contract_version=contract_version,
                contract_schema_hash=contract_schema_hash,
                dq_policy_ref=dq_policy_ref,
                rule_bundle_version=rule_bundle_version,
                normalization_profile_ref=normalization_profile_ref,
                normalization_profile_version=normalization_profile_version,
                normalization_profile_hash=normalization_profile_hash,
            ),
        }
    )
    return tuple(
        (field_name, field_value)
        for field_name, field_value in values.items()
        if field_value is not None
    )


def iter_optional_control_plane_updates_from_mapping(
    values: Mapping[str, object],
) -> tuple[tuple[str, str], ...]:
    """Project optional control-plane fields from a broader candidate mapping."""
    return iter_optional_control_plane_updates(
        **{
            field_name: cast(str | None, values.get(field_name))
            for field_name in _CONTROL_PLANE_CONTEXT_UPDATE_FIELDS
        }
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


@dataclass(frozen=True, slots=True)
class RunManifestProvenanceBundle:
    """Effective-config provenance bundle passed into manifest creation."""

    effective_config_artifact_id: str
    resolved_config_hash: str
    effective_config_hash: str
    source_fingerprint: str | None
    dq_contract_compatibility_hash: str


def build_run_manifest_provenance_bundle(
    artifact_result: tuple[str, str, str, str | None, str],
) -> RunManifestProvenanceBundle:
    """Convert one persisted effective-config result tuple into manifest provenance."""
    (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        source_fingerprint,
        dq_contract_compatibility_hash,
    ) = artifact_result
    return RunManifestProvenanceBundle(
        effective_config_artifact_id=effective_config_artifact_id,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
    )


def resolve_run_context_values(
    ctx: PipelineRunContext,
) -> tuple[str, str]:
    """Resolve run type and execution context values from context."""
    raw_run_type = getattr(ctx, "run_type", "incremental")
    run_type_value = str(getattr(raw_run_type, "value", raw_run_type))
    raw_execution_context = getattr(ctx, "execution_context", "isolated")
    execution_context_value = str(
        getattr(raw_execution_context, "value", raw_execution_context)
    )
    return run_type_value, execution_context_value
