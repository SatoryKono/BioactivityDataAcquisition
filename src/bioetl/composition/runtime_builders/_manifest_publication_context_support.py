"""Shared manifest publication context resolution for runtime builders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
    ManifestReproducibilityContext,
    resolve_manifest_reproducibility_context,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    resolve_provider_entity,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    RunManifestContractIdentity,
    resolve_contract_identity,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.domain.context import PipelineRunContext


@dataclass(frozen=True, slots=True)
class ResolvedManifestPublicationContext:
    """Provider, entity, reproducibility, and contract identity for one run."""

    provider: str
    entity: str
    reproducibility_context: ManifestReproducibilityContext
    contract_identity: RunManifestContractIdentity


class ManifestPublicationIdentityKwargs(TypedDict):
    """Typed keyword payload for manifest publication identity resolution."""

    ctx: PipelineRunContext
    inputs: RunnerInputs
    provider: str
    entity: str
    reproducibility_context: ManifestReproducibilityContext | None


def contract_identity_requires_strict_resolution(
    *,
    exact_replay_requested: bool,
    required_persistence_profile: str,
) -> bool:
    """Return whether contract identity must be resolved in strict mode."""
    return (
        exact_replay_requested
        or required_persistence_profile in STRICT_PERSISTENCE_PROFILES
    )


def resolve_manifest_publication_context(
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    reproducibility_context: ManifestReproducibilityContext | None = None,
    contract_identity: RunManifestContractIdentity | None = None,
) -> ResolvedManifestPublicationContext:
    """Resolve provider, reproducibility context, and contract identity."""
    provider, entity = resolve_provider_entity(
        pipeline_name=ctx.pipeline_name,
        yaml_config=inputs.yaml_config,
    )
    contract_ref = f"{provider}.{entity}"
    if reproducibility_context is None:
        reproducibility_context = resolve_manifest_reproducibility_context(
            ctx=ctx,
            inputs=inputs,
            provider=provider,
            entity=entity,
            contract_ref=contract_ref,
        )
    if contract_identity is None:
        contract_identity = resolve_contract_identity(
            provider=provider,
            entity=entity,
            strict=contract_identity_requires_strict_resolution(
                exact_replay_requested=bool(getattr(ctx, "exact_replay", False)),
                required_persistence_profile=(
                    reproducibility_context.required_persistence_profile
                ),
            ),
        )
    return ResolvedManifestPublicationContext(
        provider=provider,
        entity=entity,
        reproducibility_context=reproducibility_context,
        contract_identity=contract_identity,
    )


def ensure_manifest_publication_identity(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    reproducibility_context: ManifestReproducibilityContext | None = None,
    contract_identity: RunManifestContractIdentity | None = None,
) -> tuple[ManifestReproducibilityContext, RunManifestContractIdentity]:
    """Fill missing reproducibility context and contract identity for one run."""
    contract_ref = f"{provider}.{entity}"
    if reproducibility_context is None:
        reproducibility_context = resolve_manifest_reproducibility_context(
            ctx=ctx,
            inputs=inputs,
            provider=provider,
            entity=entity,
            contract_ref=contract_ref,
        )
    if contract_identity is None:
        contract_identity = resolve_contract_identity(
            provider=provider,
            entity=entity,
            strict=contract_identity_requires_strict_resolution(
                exact_replay_requested=bool(getattr(ctx, "exact_replay", False)),
                required_persistence_profile=(
                    reproducibility_context.required_persistence_profile
                ),
            ),
        )
    return reproducibility_context, contract_identity


def build_manifest_publication_identity_kwargs(
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    reproducibility_context: ManifestReproducibilityContext | None = None,
) -> ManifestPublicationIdentityKwargs:
    """Return the shared identity-resolution kwargs used by manifest builders."""
    return {
        "ctx": ctx,
        "inputs": inputs,
        "provider": provider,
        "entity": entity,
        "reproducibility_context": reproducibility_context,
    }


resolve_manifest_publication_identity = ensure_manifest_publication_identity


__all__ = [
    "ManifestPublicationIdentityKwargs",
    "ResolvedManifestPublicationContext",
    "build_manifest_publication_identity_kwargs",
    "contract_identity_requires_strict_resolution",
    "ensure_manifest_publication_identity",
    "resolve_manifest_publication_context",
    "resolve_manifest_publication_identity",
]
