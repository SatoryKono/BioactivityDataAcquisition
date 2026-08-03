"""Execution helpers for dependency join resolution and join execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import polars as pl

from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.join_planner_helpers import (
    build_join_key_set,
    find_missing_keys,
)
from bioetl.application.composite.protocols import JoinKeyResolverProtocol
from bioetl.domain.ports import LoggerPort

from .dependency_join_models import (
    CompositeJoinContext,
    DependencyJoinExecutionSpec,
    PreparedDependencyJoinContext,
    ResolvedCompositeJoinContext,
    ResolvedSingleKeyJoinContext,
    SingleKeyJoinContext,
)


def log_missing_composite_key_columns(
    *,
    logger: LoggerPort,
    dependency: str,
    missing_left: list[str],
    missing_right: list[str],
) -> None:
    """Log a warning when composite key columns are absent from join frames."""
    logger.warning(
        "Composite key join skipped: missing columns",
        dependency=dependency,
        missing_left=missing_left,
        missing_right=missing_right,
    )


def resolve_composite_join_context(
    *,
    join_key_resolver: JoinKeyResolverProtocol,
    logger: LoggerPort,
    prepared_context: PreparedDependencyJoinContext,
    metadata: CompositeJoinContext,
    dependency: str,
) -> ResolvedCompositeJoinContext | None:
    """Resolve qualified join keys for a composite dependency and validate presence."""
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
    """Resolve qualified join keys for a single-key dependency."""
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


def build_composite_join_execution_plan(
    *,
    resolved_context: ResolvedCompositeJoinContext,
    dependency: str,
    join_executor: Callable[
        [pl.DataFrame, pl.DataFrame, list[str], list[str], str],
        pl.DataFrame,
    ],
) -> DependencyJoinExecutionSpec:
    """Plan composite-key join execution after context resolution."""
    return DependencyJoinExecutionSpec(
        prepared_context=resolved_context.prepared_context,
        join_key_set=resolved_context.join_key_set,
        execute_join=lambda resolved_merged, resolved_dep: join_executor(
            resolved_merged,
            resolved_dep,
            resolved_context.left_keys,
            resolved_context.right_keys,
            dependency,
        ),
        log_message="Joined dependency with composite key",
        log_fields={
            "left_keys": resolved_context.left_keys,
            "right_keys": resolved_context.right_keys,
        },
    )


def build_single_key_join_execution_plan(
    *,
    resolved_context: ResolvedSingleKeyJoinContext,
    dependency: str,
    join_executor: Callable[[pl.DataFrame, pl.DataFrame, str, str, str], pl.DataFrame],
) -> DependencyJoinExecutionSpec:
    """Plan single-key join execution after context resolution."""
    return DependencyJoinExecutionSpec(
        prepared_context=resolved_context.prepared_context,
        join_key_set=resolved_context.join_key_set,
        execute_join=lambda resolved_merged, resolved_dep: join_executor(
            resolved_merged,
            resolved_dep,
            resolved_context.seed_join_key,
            resolved_context.dep_join_key,
            dependency,
        ),
        log_message="Joined dependency",
        log_fields={
            "seed_join_key": resolved_context.seed_join_key,
            "dep_join_key": resolved_context.dep_join_key,
        },
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
    """Execute a dependency join with conflict resolution and logging."""
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


def execute_planned_dependency_join(
    *,
    conflict_resolver: ConflictResolverService,
    logger: LoggerPort,
    dependency: str,
    execution_plan: DependencyJoinExecutionSpec,
) -> pl.DataFrame:
    """Execute a dependency join from a prebuilt execution plan."""
    return execute_dependency_join(
        conflict_resolver=conflict_resolver,
        logger=logger,
        merged_df=execution_plan.prepared_context.merged_df,
        dep_df=execution_plan.prepared_context.dep_df,
        join_key_set=execution_plan.join_key_set,
        execute_join=execution_plan.execute_join,
        log_message=execution_plan.log_message,
        dependency=dependency,
        log_fields=execution_plan.log_fields,
    )
