"""Builders for dependency join contexts and prepared frames."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.join_planner_helpers import (
    PrepareJoinFramesRequest,
    prepare_join_frames,
)
from bioetl.application.composite.protocols import JoinKeyResolverProtocol
from bioetl.domain.composite.config import DependencyConfig
from bioetl.domain.ports import LoggerPort

from .dependency_join_models import (
    CompositeJoinContext,
    PreparedDependencyJoinContext,
    SingleKeyJoinContext,
)


def resolve_left_pipeline(
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> str | None:
    """Resolve left-side pipeline name for a dependency join."""
    if dep.key_source and dep.key_source != "seed":
        return dep.key_source
    return seed_pipeline


def build_composite_join_metadata(
    *,
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> CompositeJoinContext:
    """Build join metadata for a multi-key composite dependency."""
    return CompositeJoinContext(
        join_keys_list=list(dep.join_keys),
        left_pipeline=resolve_left_pipeline(dep, seed_pipeline),
    )


def build_single_key_join_metadata(
    *,
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> SingleKeyJoinContext:
    """Build join metadata for a single-key dependency."""
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
    """Prepare left and right DataFrames for a dependency join."""
    return prepare_join_frames(
        PrepareJoinFramesRequest(
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
    )


def build_prepared_dependency_join_context(
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
    """Build the prepared dependency join context before key resolution."""
    return PreparedDependencyJoinContext(
        *prepare_dependency_join_frames(
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
    )
