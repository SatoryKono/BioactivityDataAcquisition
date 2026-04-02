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

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.application.services.run_ledger_service import RunLedgerService
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext


def _get_manifest_updates(
    manifest_id: str,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    contract_schema_hash: str | None = None,
    dq_policy_ref: str | None = None,
    rule_bundle_version: str | None = None,
) -> dict[str, str | None]:
    """Helper to collect non-None manifest updates."""
    updates: dict[str, str | None] = {"manifest_id": manifest_id}
    if config_hash is not None:
        updates["config_hash"] = config_hash
    if dq_contract_compatibility_hash is not None:
        updates["dq_contract_compatibility_hash"] = dq_contract_compatibility_hash
    if effective_config_artifact_id is not None:
        updates["effective_config_artifact_id"] = effective_config_artifact_id
    if contract_ref is not None:
        updates["contract_ref"] = contract_ref
    if contract_version is not None:
        updates["contract_version"] = contract_version
    if contract_schema_hash is not None:
        updates["contract_schema_hash"] = contract_schema_hash
    if dq_policy_ref is not None:
        updates["dq_policy_ref"] = dq_policy_ref
    if rule_bundle_version is not None:
        updates["rule_bundle_version"] = rule_bundle_version
    return updates


def attach_manifest_id(
    ctx: PipelineRunContext,
    manifest_id: str,
    *,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    contract_schema_hash: str | None = None,
    dq_policy_ref: str | None = None,
    rule_bundle_version: str | None = None,
) -> PipelineRunContext:
    """Return context carrying manifest/control-plane provenance values."""
    updates = _get_manifest_updates(
        manifest_id=manifest_id,
        config_hash=config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
    )

    if is_dataclass(ctx):
        filtered_updates = {
            k: v for k, v in updates.items() if hasattr(ctx, k) or k == "manifest_id"
        }
        return cast(
            "PipelineRunContext",
            replace(cast("DataclassInstance", ctx), **filtered_updates),
        )

    if hasattr(ctx, "__dict__"):
        for k, v in updates.items():
            setattr(ctx, k, v)
        return ctx

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
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
    )
