# Host attrs/methods provided by concrete composition.
"""Key resolver strategies for dependency coordinator (ADR-026)."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import TypeVar

import polars as pl

from bioetl.application.composite.dependency_chained_key_resolver import (
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
    "SeedKeyResolver",
    "create_chained_key_resolver",
    "create_seed_key_resolver",
]
