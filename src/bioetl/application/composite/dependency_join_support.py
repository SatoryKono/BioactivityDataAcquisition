"""Support helpers for dependency join preparation and execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import polars as pl

from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.join_planner_helpers import (
    build_join_key_set,
    find_missing_keys,
    prepare_join_frames,
)
from bioetl.application.composite.protocols import JoinKeyResolverProtocol
from bioetl.domain.composite.config import DependencyConfig
from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class CompositeJoinContext:
    """Join context for composite (multi-key) dependency joins."""

    join_keys_list: list[str]
    left_pipeline: str | None


@dataclass(frozen=True, slots=True)
class SingleKeyJoinContext:
    """Join context for single-key dependency joins."""

    join_keys_list: list[str]
    primary_key: str
    right_key: str
    right_keys_list: list[str]
    left_pipeline: str | None


@dataclass(frozen=True, slots=True)
class PreparedDependencyJoinContext:
    """Prepared DataFrames ready for dependency join execution."""

    merged_df: pl.DataFrame
    dep_df: pl.DataFrame


@dataclass(frozen=True, slots=True)
class ResolvedCompositeJoinContext:
    """Resolved join keys and frames for composite dependency joins."""

    prepared_context: PreparedDependencyJoinContext
    left_keys: list[str]
    right_keys: list[str]
    join_key_set: set[str]


@dataclass(frozen=True, slots=True)
class ResolvedSingleKeyJoinContext:
    """Resolved join keys and frames for single-key dependency joins."""

    prepared_context: PreparedDependencyJoinContext
    seed_join_key: str
    dep_join_key: str
    join_key_set: set[str]


def resolve_left_pipeline(
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> str | None:
    """Resolve left-side pipeline name for a dependency join.

    If the dependency specifies a ``key_source`` other than ``"seed"``,
    that source is used; otherwise falls back to the seed pipeline.

    Args:
        dep: Dependency configuration with optional key_source override.
        seed_pipeline: Default seed pipeline name.

    Returns:
        Pipeline name to use as the left side of the join, or None.
    """
    if dep.key_source and dep.key_source != "seed":
        return dep.key_source
    return seed_pipeline


def build_composite_join_metadata(
    *,
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> CompositeJoinContext:
    """Build join metadata for a multi-key composite dependency.

    Args:
        dep: Dependency configuration containing join key definitions.
        seed_pipeline: Seed pipeline name for left-side resolution.

    Returns:
        Context with resolved join keys list and left pipeline name.
    """
    return CompositeJoinContext(
        join_keys_list=list(dep.join_keys),
        left_pipeline=resolve_left_pipeline(dep, seed_pipeline),
    )


def build_single_key_join_metadata(
    *,
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> SingleKeyJoinContext:
    """Build join metadata for a single-key dependency.

    Resolves primary key, right key (from filter_field or primary key),
    and right keys list for the join operation.

    Args:
        dep: Dependency configuration with join key and filter field.
        seed_pipeline: Seed pipeline name for left-side resolution.

    Returns:
        Context with resolved primary/right keys and left pipeline.
    """
    join_keys_list = list(dep.join_keys)
    primary_key = dep.primary_join_key
    right_key = dep.filter_field if dep.filter_field else primary_key
    right_keys_list = [right_key] if dep.filter_field else join_keys_list
    return SingleKeyJoinContext(
        join_keys_list=join_keys_list,
        primary_key=primary_key,
        right_key=right_key,
        right_keys_list=right_keys_list,
        left_pipeline=resolve_left_pipeline(dep, seed_pipeline),
    )


def log_missing_composite_key_columns(
    *,
    logger: LoggerPort,
    dependency: str,
    missing_left: list[str],
    missing_right: list[str],
) -> None:
    """Log a warning when composite key columns are absent from join frames.

    Args:
        logger: Structured logger port.
        dependency: Name of the dependency being joined.
        missing_left: Column names missing from the left (seed) frame.
        missing_right: Column names missing from the right (dependency) frame.
    """
    logger.warning(
        "Composite key join skipped: missing columns",
        dependency=dependency,
        missing_left=missing_left,
        missing_right=missing_right,
    )


def prepare_dependency_join_frames(
    *,
    deduplicator: EnricherDeduplicatorService,
    join_key_resolver: JoinKeyResolverProtocol,
    renamer: ColumnRenamer,
    logger: LoggerPort,
    field_alias_resolver: Callable[[str], dict[str, str] | None],
    drop_system_columns: Callable[[pl.DataFrame], pl.DataFrame],
    merged_df: pl.DataFrame,
    dep_df: pl.DataFrame,
    dep: DependencyConfig,
    left_join_keys: list[str],
    right_join_keys: list[str],
    seed_pipeline: str | None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Prepare left and right DataFrames for a dependency join.

    Delegates to ``prepare_join_frames`` with deduplication, column
    renaming to qualified format, and system column removal.

    Args:
        deduplicator: Service for removing duplicate enricher records.
        join_key_resolver: Resolver for qualified join key names.
        renamer: Column renamer for qualified (pipeline-prefixed) names.
        logger: Structured logger port.
        field_alias_resolver: Resolves field aliases for a pipeline.
        drop_system_columns: Callable to strip internal system columns.
        merged_df: Accumulated left-side DataFrame.
        dep_df: Right-side dependency DataFrame.
        dep: Dependency configuration.
        left_join_keys: Join key column names on the left side.
        right_join_keys: Join key column names on the right side.
        seed_pipeline: Seed pipeline name for context.

    Returns:
        Tuple of (prepared_left, prepared_right) DataFrames.
    """
    return prepare_join_frames(
        merged_df=merged_df,
        right_df=dep_df,
        left_join_keys=left_join_keys,
        right_join_keys=right_join_keys,
        right_pipeline=dep.pipeline,
        seed_pipeline=seed_pipeline,
        deduplicator=deduplicator,
        join_key_resolver=join_key_resolver,
        renamer=renamer,
        logger=logger,
        field_alias_resolver=field_alias_resolver,
        drop_system_columns=drop_system_columns,
        log_message="Renamed dependency columns to qualified format",
        log_field_name="dependency",
    )


def resolve_composite_join_context(
    *,
    join_key_resolver: JoinKeyResolverProtocol,
    logger: LoggerPort,
    prepared_context: PreparedDependencyJoinContext,
    metadata: CompositeJoinContext,
    dependency: str,
) -> ResolvedCompositeJoinContext | None:
    """Resolve qualified join keys for a composite dependency and validate presence.

    Returns None if any required key columns are missing from either frame,
    logging a warning with the missing column details.

    Args:
        join_key_resolver: Resolver for qualified composite join key names.
        logger: Structured logger port.
        prepared_context: Pre-prepared left and right DataFrames.
        metadata: Composite join metadata with raw key names.
        dependency: Name of the dependency being joined.

    Returns:
        Resolved context with qualified keys, or None if columns are missing.
    """
    left_keys, right_keys, join_key_set = join_key_resolver.resolve_composite_join_keys(
        metadata.join_keys_list,
        metadata.left_pipeline,
        dependency,
        prepared_context.merged_df.columns,
    )
    missing_left = find_missing_keys(prepared_context.merged_df.columns, left_keys)
    missing_right = find_missing_keys(prepared_context.dep_df.columns, right_keys)
    if missing_left or missing_right:
        log_missing_composite_key_columns(
            logger=logger,
            dependency=dependency,
            missing_left=missing_left,
            missing_right=missing_right,
        )
        return None

    return ResolvedCompositeJoinContext(
        prepared_context=prepared_context,
        left_keys=left_keys,
        right_keys=right_keys,
        join_key_set=join_key_set,
    )


def resolve_single_key_join_context(
    *,
    join_key_resolver: JoinKeyResolverProtocol,
    metadata: SingleKeyJoinContext,
    dependency: str,
    prepared_context: PreparedDependencyJoinContext,
) -> ResolvedSingleKeyJoinContext:
    """Resolve qualified join keys for a single-key dependency.

    Uses asymmetric key resolution to handle cases where left and right
    key names differ (e.g., when filter_field overrides primary key).

    Args:
        join_key_resolver: Resolver for qualified join key names.
        metadata: Single-key join metadata with primary/right keys.
        dependency: Name of the dependency being joined.
        prepared_context: Pre-prepared left and right DataFrames.

    Returns:
        Resolved context with seed/dep join keys and join key set.
    """
    seed_join_key, dep_join_key, seed_join_key_qualified = (
        join_key_resolver.resolve_join_key_names_asymmetric(
            left_key=metadata.primary_key,
            right_key=metadata.right_key,
            left_pipeline=metadata.left_pipeline,
            right_pipeline=dependency,
            merged_columns=prepared_context.merged_df.columns,
        )
    )
    return ResolvedSingleKeyJoinContext(
        prepared_context=prepared_context,
        seed_join_key=seed_join_key,
        dep_join_key=dep_join_key,
        join_key_set=build_join_key_set(
            left_join_key=seed_join_key,
            right_join_key=dep_join_key,
            left_join_key_qualified=seed_join_key_qualified,
        ),
    )


def execute_dependency_join(
    *,
    conflict_resolver: ConflictResolverService,
    logger: LoggerPort,
    merged_df: pl.DataFrame,
    dep_df: pl.DataFrame,
    join_key_set: set[str],
    execute_join: Callable[[pl.DataFrame, pl.DataFrame], pl.DataFrame],
    log_message: str,
    dependency: str,
    log_fields: Mapping[str, object],
) -> pl.DataFrame:
    """Execute a dependency join with conflict resolution and logging.

    Detects and resolves column name conflicts between frames before
    delegating to the provided join callable.

    Args:
        conflict_resolver: Service for detecting/resolving column conflicts.
        logger: Structured logger port.
        merged_df: Accumulated left-side DataFrame.
        dep_df: Right-side dependency DataFrame.
        join_key_set: Set of join key column names to preserve.
        execute_join: Callable performing the actual Polars join.
        log_message: Message template for the debug log entry.
        dependency: Name of the dependency being joined.
        log_fields: Additional structured fields for logging.

    Returns:
        Joined DataFrame with conflicts resolved.
    """
    resolved_merged, resolved_dep = conflict_resolver.detect_and_resolve_conflicts(
        merged_df,
        dep_df,
        join_key_set,
    )
    result = execute_join(resolved_merged, resolved_dep)
    logger.debug(
        log_message,
        dependency=dependency,
        result_rows=len(result),
        **log_fields,
    )
    return result
