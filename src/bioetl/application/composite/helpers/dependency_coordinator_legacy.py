"""Backward-compatible collaborator resolution for DependencyCoordinatorService."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

from bioetl.application.composite.dependency_key_resolvers import (
    ChainedKeyResolver,
    SeedKeyResolver,
)
from bioetl.application.composite.dependency_progress_tracker import (
    DependencyProgressService,
)
from bioetl.application.composite.dependency_result_mapper import (
    DependencyResultService,
)

__all__ = [
    "DependencyCoordinatorCollaborators",
    "resolve_dependency_coordinator_collaborators",
]


@dataclass(frozen=True, slots=True)
class DependencyCoordinatorCollaborators:
    """Bundle of dependency coordinator collaborators."""

    seed_key_resolver: SeedKeyResolver
    chained_key_resolver: ChainedKeyResolver
    progress_service: DependencyProgressService
    result_service: DependencyResultService


def resolve_dependency_coordinator_collaborators(
    collaborators: DependencyCoordinatorCollaborators | None,
    *,
    seed_key_resolver: SeedKeyResolver | None,
    chained_key_resolver: ChainedKeyResolver | None,
    progress_service: DependencyProgressService | None,
    result_service: DependencyResultService | None,
) -> DependencyCoordinatorCollaborators:
    """Accept a collaborator bundle or the deprecated individual arguments.

    ``stacklevel`` points at the caller of ``DependencyCoordinatorService``,
    which is the only production caller of this resolver.
    """
    if collaborators is not None and any(
        item is not None
        for item in (
            seed_key_resolver,
            chained_key_resolver,
            progress_service,
            result_service,
        )
    ):
        raise TypeError(
            "Cannot combine 'collaborators' with legacy dependency arguments."
        )
    if collaborators is not None:
        return collaborators
    if (
        seed_key_resolver is None
        or chained_key_resolver is None
        or progress_service is None
        or result_service is None
    ):
        raise TypeError(
            "Either 'collaborators' or all of 'seed_key_resolver', "
            "'chained_key_resolver', 'progress_service', and "
            "'result_service' must be provided."
        )
    warnings.warn(
        "Passing 'seed_key_resolver', 'chained_key_resolver', 'progress_service', "
        "and 'result_service' directly is deprecated. Please pass a single "
        "'collaborators' argument of type DependencyCoordinatorCollaborators.",
        DeprecationWarning,
        stacklevel=3,
    )
    return DependencyCoordinatorCollaborators(
        seed_key_resolver=seed_key_resolver,
        chained_key_resolver=chained_key_resolver,
        progress_service=progress_service,
        result_service=result_service,
    )
