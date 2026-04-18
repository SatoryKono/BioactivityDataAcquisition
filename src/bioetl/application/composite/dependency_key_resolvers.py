"""Key resolver strategies for dependency coordinator (ADR-026)."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import TypeVar

import polars as pl

from bioetl.application.composite.helpers.resolver_helper import ResolverHelper
from bioetl.application.composite.join_key_normalization import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    JoinKeyNormalizationPolicy,
    normalize_join_key_dataframe_columns,
)
from bioetl.domain.composite.config import DependencyConfig
from bioetl.domain.exceptions import (
    BioETLError,
    CheckpointConflictError,
    DataQualityError,
    NetworkError,
    StorageError,
)
from bioetl.domain.ports import DeltaReaderPort, LoggerPort


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


_KEY_FILTER_ERRORS = (ValueError, TypeError, RuntimeError)
_DEPENDENCY_KEY_READ_ERRORS = (
    StorageError,
    NetworkError,
    CheckpointConflictError,
    DataQualityError,
    OSError,
    RuntimeError,
    TypeError,
)

TResolver = TypeVar("TResolver", "SeedKeyResolver", "ChainedKeyResolver")


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


class ChainedKeyResolver:
    """Resolve dependency keys from another dependency's Silver table."""

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
        """Resolve keys by reading them from the source dependency's Silver table.

        Args:
            dependency: Dependency configuration with ``key_source`` specifying the
                chained dependency pipeline name.
            seed_keys: Fallback seed keys used when the Silver table is unavailable.
            dep_config_lookup: Mapping of pipeline name to DependencyConfig used to
                look up the chained source's Silver table path.
            delta_reader: Delta Lake reader port for reading the chained Silver table.

        Returns:
            DataFrame of keys from the chained source's Silver table, filtered by
            key_filter if configured; falls back to seed_keys on read failures.

        Raises:
            ValueError: If the chained dependency has no silver_table configured or
                if reading the Silver table fails.
        """
        reader = self._require_delta_reader(dependency, delta_reader)
        source_config = self._resolve_source_config(dependency, dep_config_lookup)
        source_table = source_config.silver_table
        if source_table is None:
            raise ValueError(
                f"Chained dependency '{dependency.pipeline}' references "
                f"key_source='{dependency.key_source}' which has no silver_table configured"
            )

        try:
            pa_table = await reader.read_table(source_table)
        except FileNotFoundError:
            self._resolver_helper.log_warning(
                "Source Silver table not found (first run?), falling back to seed keys",
                dependency=dependency.pipeline,
                key_source=dependency.key_source,
                source_table=source_table,
            )
            return seed_keys
        except ValueError:
            raise
        except (*_DEPENDENCY_KEY_READ_ERRORS, BioETLError) as exc:
            self._resolver_helper.log_error(
                "Failed to read chained dependency keys",
                dependency=dependency.pipeline,
                key_source=dependency.key_source,
                source_table=source_table,
                error=str(exc),
                error_type=type(exc).__name__,
                reason_code="chained_dependency_read_failed",
            )
            raise ValueError(
                f"Failed to read keys for chained dependency '{dependency.pipeline}' "
                f"from '{source_table}': {exc}"
            ) from exc

        if pa_table is None or pa_table.num_rows == 0:
            self._resolver_helper.log_warning(
                "Source Silver table is empty, falling back to seed keys",
                dependency=dependency.pipeline,
                key_source=dependency.key_source,
                source_table=source_table,
            )
            return seed_keys

        source_keys = self._to_source_keys(pa_table, source_table)
        self._validate_join_key(source_keys, dependency, source_table)
        source_keys = self._apply_key_filter(source_keys, dependency)
        source_keys = normalize_join_key_dataframe_columns(
            df=source_keys,
            join_keys=dependency.join_keys,
            normalization_policies=self._resolver_helper._normalization_policies,
        )

        self._resolver_helper.log_info(
            "Using chained dependency keys",
            dependency=dependency.pipeline,
            key_source=dependency.key_source,
            source_table=source_table,
            key_count=len(source_keys),
            columns=list(source_keys.columns),
        )
        return source_keys

    def _require_delta_reader(
        self,
        dependency: DependencyConfig,
        delta_reader: DeltaReaderPort | None,
    ) -> DeltaReaderPort:
        if delta_reader is not None:
            return delta_reader
        raise ValueError(
            f"Chained dependency '{dependency.pipeline}' requires delta_reader, "
            f"but none was provided. key_source='{dependency.key_source}'"
        )

    def _resolve_source_config(
        self,
        dependency: DependencyConfig,
        dep_config_lookup: dict[str, DependencyConfig],
    ) -> DependencyConfig:
        source_config = dep_config_lookup.get(dependency.key_source or "")
        if source_config is not None:
            return source_config
        raise ValueError(
            f"Chained dependency '{dependency.pipeline}' references unknown "
            f"key_source='{dependency.key_source}'. "
            f"Available dependencies: {list(dep_config_lookup.keys())}"
        )

    def _to_source_keys(
        self,
        pa_table: object,
        source_table: str,
    ) -> pl.DataFrame:
        source_keys_result = pl.from_arrow(pa_table)
        if isinstance(source_keys_result, pl.DataFrame):
            return source_keys_result
        raise TypeError(
            f"Expected DataFrame from PyArrow Table for '{source_table}', "
            f"got {type(source_keys_result)}"
        )

    def _validate_join_key(
        self,
        source_keys: pl.DataFrame,
        dependency: DependencyConfig,
        source_table: str,
    ) -> None:
        join_key = dependency.join_keys[0] if dependency.join_keys else None
        if join_key and join_key not in source_keys.columns:
            raise ValueError(
                f"Column '{join_key}' not found in source table "
                f"'{source_table}'. "
                f"Available columns: {list(source_keys.columns)}"
            )

    def _apply_key_filter(
        self,
        source_keys: pl.DataFrame,
        dependency: DependencyConfig,
    ) -> pl.DataFrame:
        if not dependency.key_filter:
            return source_keys
        try:
            original_count = len(source_keys)
            filtered = source_keys.filter(pl.sql_expr(dependency.key_filter))
            self._resolver_helper.log_info(
                "Applied key_filter to chained dependency",
                dependency=dependency.pipeline,
                key_filter=dependency.key_filter,
                original_count=original_count,
                filtered_count=len(filtered),
            )
            return filtered
        except (*_KEY_FILTER_ERRORS, BioETLError) as exc:
            self._resolver_helper.log_warning(
                "Failed to apply key_filter, using all keys",
                dependency=dependency.pipeline,
                key_filter=dependency.key_filter,
                error=str(exc),
                error_type=type(exc).__name__,
                reason_code="key_filter_apply_failed",
            )
            return source_keys


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


def _create_key_resolver(
    resolver_type: type[TResolver],
    logger: LoggerPort,
    *,
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy],
) -> TResolver:
    """Build one dependency key resolver with the configured normalization policies."""
    return resolver_type(logger, normalization_policies=normalization_policies)


__all__ = [
    "ChainedKeyResolver",
    "SeedKeyResolver",
    "create_chained_key_resolver",
    "create_seed_key_resolver",
]
