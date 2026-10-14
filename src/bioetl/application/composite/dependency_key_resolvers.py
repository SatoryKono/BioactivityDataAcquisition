# Host attrs/methods provided by concrete composition.
"""Key resolver strategies for dependency coordinator (ADR-026)."""

from __future__ import annotations

import asyncio
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeVar

import polars as pl

from bioetl.application.composite.dependency_progress_tracker import (
    DependencyProgressService,
)
from bioetl.application.composite.dependency_result_mapper import (
    DependencyResultService,
)
from bioetl.application.composite.helpers.dependency_chained_key_resolver import (
    ChainedKeyResolver as ChainedKeyResolver,
)
from bioetl.application.composite.helpers.resolver_helper import ResolverHelper
from bioetl.application.composite.join_key_normalization import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    JoinKeyNormalizationPolicy,
    normalize_join_key_dataframe_columns,
)
from bioetl.domain.composite import DependencyConfig
from bioetl.domain.ports import DeltaReaderPort, LoggerPort

TResolver = TypeVar("TResolver", "SeedKeyResolver", ChainedKeyResolver)


def create_resolver_helper(
    logger: LoggerPort,
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy] | None = None,
) -> ResolverHelper:
    """Create a ResolverHelper instance with optional normalization policies."""
    return ResolverHelper(
        logger=logger,
        normalization_policies=normalization_policies
        or JOIN_KEY_NORMALIZATION_POLICIES,
    )


class SeedKeyResolver:
    """Resolve dependency keys by reusing normalized seed keys directly."""

    def __init__(
        self,
        resolver_helper: ResolverHelper,
    ) -> None:
        self._resolver_helper = resolver_helper

    async def resolve(
        self,
        dependency: DependencyConfig,
        seed_keys: pl.DataFrame,
        dep_config_lookup: dict[str, DependencyConfig],
        delta_reader: DeltaReaderPort | None,
    ) -> pl.DataFrame:
        """Resolve keys by passing through the seed keys unchanged.

        Args:
            dependency: Dependency configuration describing the target pipeline.
            seed_keys: DataFrame of seed keys from the composite seed pipeline.
            dep_config_lookup: Mapping of pipeline name to DependencyConfig (unused here).
            delta_reader: Delta Lake reader port (unused here).

        Returns:
            The seed_keys DataFrame with canonical join-key normalization applied.
        """
        await asyncio.sleep(0)
        del dep_config_lookup, delta_reader
        normalized_keys = normalize_join_key_dataframe_columns(
            df=seed_keys,
            join_keys=dependency.join_keys,
            normalization_policies=self._resolver_helper._normalization_policies,
        )
        self._resolver_helper.log_debug(
            "Using seed keys for dependency",
            dependency=dependency.pipeline,
            key_count=len(normalized_keys),
        )
        return normalized_keys


def create_seed_key_resolver(
    logger: LoggerPort,
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> SeedKeyResolver:
    """Create default seed-key resolver.

    Args:
        logger: Logger instance for diagnostic messages.

    Returns:
        New SeedKeyResolver instance wired with the provided logger.
    """
    resolver_helper = create_resolver_helper(logger, normalization_policies)
    return SeedKeyResolver(resolver_helper)


def create_chained_key_resolver(
    logger: LoggerPort,
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> ChainedKeyResolver:
    """Create default chained-key resolver.

    Args:
        logger: Logger instance for diagnostic messages.

    Returns:
        New ChainedKeyResolver instance wired with the provided logger.
    """
    resolver_helper = create_resolver_helper(logger, normalization_policies)
    return ChainedKeyResolver(resolver_helper)


def _create_key_resolver[TResolver: (SeedKeyResolver, ChainedKeyResolver)](
    resolver_type: type[TResolver],
    logger: LoggerPort,
    *,
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy],
) -> TResolver:
    """Build one dependency key resolver with the configured normalization policies."""
    resolver_helper = create_resolver_helper(logger, normalization_policies)
    return resolver_type(resolver_helper)


__all__ = [
    "ChainedKeyResolver",
    "DependencyCoordinatorCollaborators",
    "SeedKeyResolver",
    "create_chained_key_resolver",
    "create_seed_key_resolver",
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
