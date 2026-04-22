"""Control-plane helpers for runtime runner assembly."""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING, cast

from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    create_and_persist_effective_config_artifact,
)
from bioetl.composition.runtime_builders.run_manifest_builder import (
    _ManifestControlPlaneRefs,
    create_run_manifest,
)
from bioetl.domain.normalization import normalize_runtime_anchor_payload

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext


_OPTIONAL_CONTROL_PLANE_FIELDS = (
    "execution_fingerprint",
    "config_hash",
    "resolved_config_hash",
    "effective_config_hash",
    "dq_contract_compatibility_hash",
    "effective_config_artifact_id",
    "contract_ref",
    "contract_version",
    "contract_schema_hash",
    "dq_policy_ref",
    "rule_bundle_version",
)


def _iter_optional_control_plane_updates(
    *,
    execution_fingerprint: str | None = None,
    config_hash: str | None = None,
    resolved_config_hash: str | None = None,
    effective_config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    contract_schema_hash: str | None = None,
    dq_policy_ref: str | None = None,
    rule_bundle_version: str | None = None,
) -> tuple[tuple[str, str], ...]:
    values = normalize_runtime_anchor_payload(
        {
            "execution_fingerprint": execution_fingerprint,
            "config_hash": config_hash,
            "resolved_config_hash": resolved_config_hash,
            "effective_config_hash": effective_config_hash,
            "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
            "effective_config_artifact_id": effective_config_artifact_id,
            "contract_ref": contract_ref,
            "contract_version": contract_version,
            "contract_schema_hash": contract_schema_hash,
            "dq_policy_ref": dq_policy_ref,
            "rule_bundle_version": rule_bundle_version,
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
    ctx: object,
    manifest_id: str,
    *,
    optional_updates: tuple[tuple[str, str], ...],
) -> object:
    ctx.manifest_id = manifest_id
    for field_name, field_value in optional_updates:
        setattr(ctx, field_name, field_value)
    return ctx


def attach_manifest_id(
    ctx: PipelineRunContext,
    manifest_id: str,
    *,
    execution_fingerprint: str | None = None,
    config_hash: str | None = None,
    resolved_config_hash: str | None = None,
    effective_config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    contract_schema_hash: str | None = None,
    dq_policy_ref: str | None = None,
    rule_bundle_version: str | None = None,
) -> PipelineRunContext:
    """Return context carrying manifest/control-plane provenance values."""
    optional_updates = _iter_optional_control_plane_updates(
        execution_fingerprint=execution_fingerprint,
        config_hash=config_hash,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
    )
    if is_dataclass(ctx):
        return cast(
            "PipelineRunContext",
            replace(
                cast("DataclassInstance", ctx),
                **_build_dataclass_manifest_updates(
                    ctx,
                    manifest_id,
                    optional_updates=optional_updates,
                ),
            ),
        )
    if hasattr(ctx, "__dict__"):
        return cast(
            "PipelineRunContext",
            _apply_manifest_updates_to_mutable_context(
                ctx,
                manifest_id,
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
    if "_" in ctx.pipeline_name:
        provider, entity = ctx.pipeline_name.split("_", 1)
    else:
        provider = ctx.pipeline_name
        entity = ctx.pipeline_name
    (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        dq_contract_compatibility_hash,
    ) = create_and_persist_effective_config_artifact(
        ctx=ctx,
        inputs=inputs,
        provider=provider,
        entity=entity,
    )
    return create_run_manifest(
        ctx=ctx,
        inputs=inputs,
        ledger_enabled=ledger_enabled,
        effective_config_artifact_id=effective_config_artifact_id,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
    )
