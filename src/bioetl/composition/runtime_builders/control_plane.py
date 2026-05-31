"""Control-plane helpers for runtime runner assembly."""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING, cast

from bioetl.composition.runtime_builders._manifest_publication_context_support import (
    resolve_manifest_publication_context,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    apply_manifest_updates_to_mutable_context,
    build_run_manifest_provenance_bundle,
    build_dataclass_manifest_updates,
    extract_optional_updates_from_refs,
    iter_optional_control_plane_updates_from_mapping,
)
from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    create_and_persist_effective_config_artifact,
)
from bioetl.composition.runtime_builders.run_manifest_builder import create_run_manifest
from bioetl.composition.runtime_builders.run_manifest_support import (
    ManifestControlPlaneRefs as _ManifestControlPlaneRefs,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext


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
        optional_updates = extract_optional_updates_from_refs(control_plane_refs)
    else:
        if manifest_id is None:
            raise TypeError(
                "attach_manifest_id requires either manifest_id or control_plane_refs"
            )
        optional_updates = iter_optional_control_plane_updates_from_mapping(
            locals()
        )
    if is_dataclass(ctx):
        return cast(
            "PipelineRunContext",
            replace(
                cast("DataclassInstance", ctx),
                **build_dataclass_manifest_updates(
                    ctx,
                    cast(str, manifest_id),
                    optional_updates=optional_updates,
                ),
            ),
        )
    if hasattr(ctx, "__dict__"):
        return cast(
            "PipelineRunContext",
            apply_manifest_updates_to_mutable_context(
                ctx,
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
    provenance = build_run_manifest_provenance_bundle(
        create_and_persist_effective_config_artifact(
            ctx=ctx,
            inputs=inputs,
            provider=publication_context.provider,
            entity=publication_context.entity,
            reproducibility_context=publication_context.reproducibility_context,
            contract_identity=publication_context.contract_identity,
        )
    )
    return create_run_manifest(
        ctx=ctx,
        inputs=inputs,
        ledger_enabled=ledger_enabled,
        provenance=provenance,
        reproducibility_context=publication_context.reproducibility_context,
        contract_identity=publication_context.contract_identity,
    )
