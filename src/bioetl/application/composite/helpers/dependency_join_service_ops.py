"""Private operation collaborators for DependencyJoinerService."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.composite.dependency_join_context_builders import (
    build_prepared_dependency_join_context,
)
from bioetl.application.composite.dependency_join_execution import (
    build_composite_join_execution_plan,
    build_single_key_join_execution_plan,
    execute_planned_dependency_join,
    resolve_composite_join_context,
)
from bioetl.application.composite.dependency_join_models import (
    CompositeJoinContext,
    DependencyJoinExecutionSpec,
    PreparedDependencyJoinContext,
    ResolvedCompositeJoinContext,
    ResolvedSingleKeyJoinContext,
)
from bioetl.application.composite.protocols import (
    JoinExecutorProtocol,
    JoinKeyResolverProtocol,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.domain.composite import DependencyConfig
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "execute_composite_dependency_join",
    "execute_prepared_dependency_join",
    "execute_single_key_dependency_join",
    "prepare_dependency_join_context",
    "resolve_composite_join_context_for_service",
]


def prepare_dependency_join_context(
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
) -> PreparedDependencyJoinContext:
    return build_prepared_dependency_join_context(
        deduplicator=deduplicator,
        join_key_resolver=join_key_resolver,
        renamer=renamer,
        logger=logger,
        field_alias_resolver=field_alias_resolver,
        drop_system_columns=drop_system_columns,
        merged_df=merged_df,
        dep_df=dep_df,
        dep=dep,
        left_join_keys=left_join_keys,
        right_join_keys=right_join_keys,
        seed_pipeline=seed_pipeline,
    )


def resolve_composite_join_context_for_service(
    *,
    join_key_resolver: JoinKeyResolverProtocol,
    logger: LoggerPort,
    prepared_context: PreparedDependencyJoinContext,
    metadata: CompositeJoinContext,
    dependency: str,
) -> ResolvedCompositeJoinContext | None:
    return resolve_composite_join_context(
        join_key_resolver=join_key_resolver,
        logger=logger,
        prepared_context=prepared_context,
        metadata=metadata,
        dependency=dependency,
    )


def execute_prepared_dependency_join(
    *,
    conflict_resolver: ConflictResolverService,
    logger: LoggerPort,
    dependency: str,
    execution_plan: DependencyJoinExecutionSpec,
) -> pl.DataFrame:
    return execute_planned_dependency_join(
        conflict_resolver=conflict_resolver,
        logger=logger,
        dependency=dependency,
        execution_plan=execution_plan,
    )


def execute_composite_dependency_join(
    *,
    conflict_resolver: ConflictResolverService,
    logger: LoggerPort,
    join_executor: JoinExecutorProtocol,
    resolved_context: ResolvedCompositeJoinContext,
    dep: DependencyConfig,
) -> pl.DataFrame:
    return execute_prepared_dependency_join(
        conflict_resolver=conflict_resolver,
        logger=logger,
        dependency=dep.pipeline,
        execution_plan=build_composite_join_execution_plan(
            resolved_context=resolved_context,
            dependency=dep.pipeline,
            join_executor=join_executor.execute_composite_key_join,
        ),
    )


def execute_single_key_dependency_join(
    *,
    conflict_resolver: ConflictResolverService,
    logger: LoggerPort,
    join_executor: JoinExecutorProtocol,
    resolved_context: ResolvedSingleKeyJoinContext,
    dep: DependencyConfig,
) -> pl.DataFrame:
    return execute_prepared_dependency_join(
        conflict_resolver=conflict_resolver,
        logger=logger,
        dependency=dep.pipeline,
        execution_plan=build_single_key_join_execution_plan(
            resolved_context=resolved_context,
            dependency=dep.pipeline,
            join_executor=join_executor.execute_polars_join,
        ),
    )
