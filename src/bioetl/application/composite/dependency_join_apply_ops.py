"""Apply-path helpers for DependencyJoinerService join orchestration."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.composite.dependency_join_context_builders import (
    build_composite_join_metadata,
    build_single_key_join_metadata,
)
from bioetl.application.composite.dependency_join_execution import (
    resolve_single_key_join_context,
)
from bioetl.application.composite.dependency_join_service_ops import (
    execute_composite_dependency_join,
    execute_single_key_dependency_join,
    prepare_dependency_join_context,
    resolve_composite_join_context_for_service,
)
from bioetl.application.composite.protocols import (
    JoinExecutorProtocol,
    JoinKeyResolverProtocol,
)
from bioetl.application.composite.target_protein_classification_summary import (
    TARGET_PROTEIN_CLASSIFICATION_PIPELINE,
    summarize_target_protein_classification_dependency,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.domain.composite import DependencyConfig
    from bioetl.domain.ports import LoggerPort

__all__ = [
    "apply_composite_key_dependency_join",
    "apply_loaded_dependency_join",
    "apply_resolved_dependency_join",
    "apply_single_key_dependency_join",
]


def apply_single_key_dependency_join(
    *,
    deduplicator: EnricherDeduplicatorService,
    join_key_resolver: JoinKeyResolverProtocol,
    renamer: ColumnRenamer,
    logger: LoggerPort,
    field_alias_resolver: Callable[[str], dict[str, str] | None],
    drop_system_columns: Callable[[pl.DataFrame], pl.DataFrame],
    conflict_resolver: ConflictResolverService,
    join_executor: JoinExecutorProtocol,
    merged_df: pl.DataFrame,
    dep_df: pl.DataFrame,
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> pl.DataFrame:
    metadata = build_single_key_join_metadata(
        dep=dep,
        seed_pipeline=seed_pipeline,
    )
    prepared_context = prepare_dependency_join_context(
        deduplicator=deduplicator,
        join_key_resolver=join_key_resolver,
        renamer=renamer,
        logger=logger,
        field_alias_resolver=field_alias_resolver,
        drop_system_columns=drop_system_columns,
        merged_df=merged_df,
        dep_df=dep_df,
        dep=dep,
        left_join_keys=metadata.join_keys_list,
        right_join_keys=metadata.right_keys_list,
        seed_pipeline=seed_pipeline,
    )
    resolved_context = resolve_single_key_join_context(
        join_key_resolver=join_key_resolver,
        metadata=metadata,
        dependency=dep.pipeline,
        prepared_context=prepared_context,
    )
    return execute_single_key_dependency_join(
        conflict_resolver=conflict_resolver,
        logger=logger,
        join_executor=join_executor,
        resolved_context=resolved_context,
        dep=dep,
    )


def apply_composite_key_dependency_join(
    *,
    deduplicator: EnricherDeduplicatorService,
    join_key_resolver: JoinKeyResolverProtocol,
    renamer: ColumnRenamer,
    logger: LoggerPort,
    field_alias_resolver: Callable[[str], dict[str, str] | None],
    drop_system_columns: Callable[[pl.DataFrame], pl.DataFrame],
    conflict_resolver: ConflictResolverService,
    join_executor: JoinExecutorProtocol,
    merged_df: pl.DataFrame,
    dep_df: pl.DataFrame,
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> pl.DataFrame:
    metadata = build_composite_join_metadata(
        dep=dep,
        seed_pipeline=seed_pipeline,
    )
    prepared_context = prepare_dependency_join_context(
        deduplicator=deduplicator,
        join_key_resolver=join_key_resolver,
        renamer=renamer,
        logger=logger,
        field_alias_resolver=field_alias_resolver,
        drop_system_columns=drop_system_columns,
        merged_df=merged_df,
        dep_df=dep_df,
        dep=dep,
        left_join_keys=metadata.join_keys_list,
        right_join_keys=metadata.join_keys_list,
        seed_pipeline=metadata.left_pipeline,
    )
    resolved_context = resolve_composite_join_context_for_service(
        join_key_resolver=join_key_resolver,
        logger=logger,
        prepared_context=prepared_context,
        metadata=metadata,
        dependency=dep.pipeline,
    )
    if resolved_context is None:
        return merged_df
    return execute_composite_dependency_join(
        conflict_resolver=conflict_resolver,
        logger=logger,
        join_executor=join_executor,
        resolved_context=resolved_context,
        dep=dep,
    )


def apply_resolved_dependency_join(
    *,
    deduplicator: EnricherDeduplicatorService,
    join_key_resolver: JoinKeyResolverProtocol,
    renamer: ColumnRenamer,
    logger: LoggerPort,
    field_alias_resolver: Callable[[str], dict[str, str] | None],
    drop_system_columns: Callable[[pl.DataFrame], pl.DataFrame],
    conflict_resolver: ConflictResolverService,
    join_executor: JoinExecutorProtocol,
    merged_df: pl.DataFrame,
    dep_df: pl.DataFrame,
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> pl.DataFrame:
    if dep.is_multi_field_filter:
        return apply_composite_key_dependency_join(
            deduplicator=deduplicator,
            join_key_resolver=join_key_resolver,
            renamer=renamer,
            logger=logger,
            field_alias_resolver=field_alias_resolver,
            drop_system_columns=drop_system_columns,
            conflict_resolver=conflict_resolver,
            join_executor=join_executor,
            merged_df=merged_df,
            dep_df=dep_df,
            dep=dep,
            seed_pipeline=seed_pipeline,
        )

    return apply_single_key_dependency_join(
        deduplicator=deduplicator,
        join_key_resolver=join_key_resolver,
        renamer=renamer,
        logger=logger,
        field_alias_resolver=field_alias_resolver,
        drop_system_columns=drop_system_columns,
        conflict_resolver=conflict_resolver,
        join_executor=join_executor,
        merged_df=merged_df,
        dep_df=dep_df,
        dep=dep,
        seed_pipeline=seed_pipeline,
    )


def apply_loaded_dependency_join(
    *,
    deduplicator: EnricherDeduplicatorService,
    join_key_resolver: JoinKeyResolverProtocol,
    renamer: ColumnRenamer,
    logger: LoggerPort,
    field_alias_resolver: Callable[[str], dict[str, str] | None],
    drop_system_columns: Callable[[pl.DataFrame], pl.DataFrame],
    conflict_resolver: ConflictResolverService,
    join_executor: JoinExecutorProtocol,
    merged_df: pl.DataFrame,
    dependency_dfs: dict[str, pl.DataFrame],
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> pl.DataFrame:
    dep_df = dependency_dfs.get(dep.pipeline)
    if dep_df is None:
        return merged_df
    if dep.pipeline == TARGET_PROTEIN_CLASSIFICATION_PIPELINE:
        dep_df = summarize_target_protein_classification_dependency(dep_df)

    return apply_resolved_dependency_join(
        deduplicator=deduplicator,
        join_key_resolver=join_key_resolver,
        renamer=renamer,
        logger=logger,
        field_alias_resolver=field_alias_resolver,
        drop_system_columns=drop_system_columns,
        conflict_resolver=conflict_resolver,
        join_executor=join_executor,
        merged_df=merged_df,
        dep_df=dep_df,
        dep=dep,
        seed_pipeline=seed_pipeline,
    )
