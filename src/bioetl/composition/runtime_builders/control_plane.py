"""Control-plane helpers for runtime runner assembly."""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.composition.runtime_builders._manifest_publication_context_support import (
    resolve_manifest_publication_context,
)
from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    create_and_persist_effective_config_artifact,
)
from bioetl.composition.runtime_builders.run_manifest_builder import create_run_manifest
from bioetl.composition.runtime_builders.run_manifest_support import (
    ManifestControlPlaneRefs as _ManifestControlPlaneRefs,
)
from bioetl.domain.normalization import normalize_runtime_anchor_payload

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext


class _MutableManifestContext(Protocol):
    manifest_id: str | None


def _iter_optional_control_plane_updates(
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
            "contract_ref": contract_ref,
            "contract_version": contract_version,
            "contract_schema_hash": contract_schema_hash,
            "dq_policy_ref": dq_policy_ref,
            "rule_bundle_version": rule_bundle_version,
            "normalization_profile_ref": normalization_profile_ref,
            "normalization_profile_version": normalization_profile_version,
            "normalization_profile_hash": normalization_profile_hash,
        }
    )
    return tuple(
        (field_name, field_value)
        for field_name, field_value in values.items()
        if field_value is not None
    )


def _build_dataclass_manifest_updates(
    ctx: PipelineRunContext,
    manifest_id: str,
    *,
    optional_updates: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    updates: dict[str, object] = {"manifest_id": manifest_id}
    for field_name, field_value in optional_updates:
        if hasattr(ctx, field_name):
            updates[field_name] = field_value
    return updates


def _apply_manifest_updates_to_mutable_context(
    ctx: _MutableManifestContext,
    manifest_id: str,
    *,
    optional_updates: tuple[tuple[str, str], ...],
) -> _MutableManifestContext:
    ctx.manifest_id = manifest_id
    for field_name, field_value in optional_updates:
        setattr(ctx, field_name, field_value)
    return ctx


def _extract_optional_updates_from_refs(
    control_plane_refs: _ManifestControlPlaneRefs,
) -> tuple[tuple[str, str], ...]:
    """Extract optional control-plane updates from manifest refs."""
    return _iter_optional_control_plane_updates(
        execution_fingerprint=getattr(
            control_plane_refs, "execution_fingerprint", None
        ),
        config_hash=getattr(control_plane_refs, "config_hash", None),
        resolved_config_hash=getattr(control_plane_refs, "resolved_config_hash", None),
        effective_config_hash=getattr(
            control_plane_refs, "effective_config_hash", None
        ),
        source_fingerprint=getattr(control_plane_refs, "source_fingerprint", None),
        dq_contract_compatibility_hash=getattr(
            control_plane_refs, "dq_contract_compatibility_hash", None
        ),
        effective_config_artifact_id=getattr(
            control_plane_refs, "effective_config_artifact_id", None
        ),
        replay_of_run_id=getattr(control_plane_refs, "replay_of_run_id", None),
        replay_of_manifest_id=getattr(
            control_plane_refs, "replay_of_manifest_id", None
        ),
        input_snapshot_fingerprint=getattr(
            control_plane_refs, "input_snapshot_fingerprint", None
        ),
        contract_ref=getattr(control_plane_refs, "contract_ref", None),
        contract_version=getattr(control_plane_refs, "contract_version", None),
        contract_schema_hash=getattr(control_plane_refs, "contract_schema_hash", None),
        dq_policy_ref=getattr(control_plane_refs, "dq_policy_ref", None),
        rule_bundle_version=getattr(control_plane_refs, "rule_bundle_version", None),
        normalization_profile_ref=getattr(
            control_plane_refs, "normalization_profile_ref", None
        ),
        normalization_profile_version=getattr(
            control_plane_refs, "normalization_profile_version", None
        ),
        normalization_profile_hash=getattr(
            control_plane_refs, "normalization_profile_hash", None
        ),
    )


def attach_manifest_id(
    ctx: PipelineRunContext,
    manifest_id: str | None = None,
    *,
    control_plane_refs: _ManifestControlPlaneRefs | None = None,
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
) -> PipelineRunContext:
    """Return context carrying manifest/control-plane provenance values."""
    if control_plane_refs is not None:
        manifest_id = control_plane_refs.manifest_id
        optional_updates = _extract_optional_updates_from_refs(control_plane_refs)
    else:
        if manifest_id is None:
            raise TypeError(
                "attach_manifest_id requires either manifest_id or control_plane_refs"
            )
        optional_updates = _iter_optional_control_plane_updates(
            execution_fingerprint=execution_fingerprint,
            config_hash=config_hash,
            resolved_config_hash=resolved_config_hash,
            effective_config_hash=effective_config_hash,
            source_fingerprint=source_fingerprint,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
            replay_of_run_id=replay_of_run_id,
            replay_of_manifest_id=replay_of_manifest_id,
            input_snapshot_fingerprint=input_snapshot_fingerprint,
            contract_ref=contract_ref,
            contract_version=contract_version,
            contract_schema_hash=contract_schema_hash,
            dq_policy_ref=dq_policy_ref,
            rule_bundle_version=rule_bundle_version,
            normalization_profile_ref=normalization_profile_ref,
            normalization_profile_version=normalization_profile_version,
            normalization_profile_hash=normalization_profile_hash,
        )
    if is_dataclass(ctx):
        return cast(
            "PipelineRunContext",
            replace(
                cast("DataclassInstance", ctx),
                **_build_dataclass_manifest_updates(
                    ctx,
                    cast(str, manifest_id),
                    optional_updates=optional_updates,
                ),
            ),
        )
    if hasattr(ctx, "__dict__"):
        return cast(
            "PipelineRunContext",
            _apply_manifest_updates_to_mutable_context(
                cast(_MutableManifestContext, ctx),
                cast(str, manifest_id),
                optional_updates=optional_updates,
            ),
        )
    raise TypeError("PipelineRunContext must support manifest_id attachment")


def create_run_manifest_with_effective_config(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
) -> tuple[_ManifestControlPlaneRefs, RunLedgerService | None]:
    """Create immutable manifest before pipeline assembly begins."""
    publication_context = resolve_manifest_publication_context(
        ctx=ctx,
        inputs=inputs,
    )
    (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        source_fingerprint,
        dq_contract_compatibility_hash,
    ) = create_and_persist_effective_config_artifact(
        ctx=ctx,
        inputs=inputs,
        provider=publication_context.provider,
        entity=publication_context.entity,
        reproducibility_context=publication_context.reproducibility_context,
        contract_identity=publication_context.contract_identity,
    )
    return create_run_manifest(
        ctx=ctx,
        inputs=inputs,
        ledger_enabled=ledger_enabled,
        effective_config_artifact_id=effective_config_artifact_id,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        reproducibility_context=publication_context.reproducibility_context,
        contract_identity=publication_context.contract_identity,
    )
