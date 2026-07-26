"""Control-plane helpers for runtime runner assembly."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING, cast

from bioetl.composition.runtime_builders._manifest_publication_context_support import (
    resolve_manifest_publication_context,
)
from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    create_and_persist_effective_config_artifact,
)
from bioetl.composition.runtime_builders.run_manifest_builder import create_run_manifest
from bioetl.composition.runtime_builders.run_manifest_support import (
    ManifestControlPlaneRefs as _ManifestControlPlaneRefs,
    apply_manifest_updates_to_mutable_context,
    build_dataclass_manifest_updates,
    build_run_manifest_provenance_bundle,
    extract_optional_updates_from_refs,
    iter_optional_control_plane_updates_from_mapping,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.domain.context import PipelineRunContext


def attach_manifest_id(
    ctx: PipelineRunContext,
    manifest_id: str | None = None,
    *,
    control_plane_refs: _ManifestControlPlaneRefs | None = None,
    optional_fields: Mapping[str, object] | None = None,
) -> PipelineRunContext:
    """Return context carrying manifest/control-plane provenance values.

    Prefer ``control_plane_refs`` for full provenance. ``optional_fields`` is a
    compact mapping of residual control-plane anchors when refs are unavailable
    (keeps this surface under Sonar S107).
    """
    if control_plane_refs is not None:
        manifest_id = control_plane_refs.manifest_id
        optional_updates = extract_optional_updates_from_refs(control_plane_refs)
    else:
        if manifest_id is None:
            raise TypeError(
                "attach_manifest_id requires either manifest_id or control_plane_refs"
            )
        optional_updates = iter_optional_control_plane_updates_from_mapping(
            optional_fields or {}
        )
    if is_dataclass(ctx):
        return cast(
            "PipelineRunContext",
            replace(
                cast("DataclassInstance", ctx),
                **build_dataclass_manifest_updates(
                    ctx,
                    manifest_id,
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
