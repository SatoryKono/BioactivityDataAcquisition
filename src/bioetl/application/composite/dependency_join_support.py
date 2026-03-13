"""Support helpers for dependency join preparation and execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import polars as pl

from bioetl.application.composite.column_renamer import ColumnRenamerService
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.join_planner_helpers import (
    prepare_qualified_right_join_dataframe,
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
    if dep.key_source and dep.key_source != "seed":
        return dep.key_source
    return seed_pipeline


def build_asymmetric_join_key_set(
    *,
    left_join_key: str,
    right_join_key: str,
    left_join_key_qualified: str | None,
) -> set[str]:
    join_key_set = {left_join_key, right_join_key}
    if left_join_key_qualified and left_join_key_qualified != left_join_key:
        join_key_set.add(left_join_key_qualified)
    return join_key_set

def find_missing_keys(columns: list[str], keys: list[str]) -> list[str]:
    return [key for key in keys if key not in columns]


def build_composite_join_metadata(
    *,
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> CompositeJoinContext:
    return CompositeJoinContext(
        join_keys_list=list(dep.join_keys),
        left_pipeline=resolve_left_pipeline(dep, seed_pipeline),
    )


def build_single_key_join_metadata(
    *,
    dep: DependencyConfig,
    seed_pipeline: str | None,
) -> SingleKeyJoinContext:
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
    logger.warning(
        "Composite key join skipped: missing columns",
        dependency=dependency,
        missing_left=missing_left,
        missing_right=missing_right,
    )


def normalize_dependency_join_inputs(
    *,
    join_key_resolver: JoinKeyResolverProtocol,
    merged_df: pl.DataFrame,
    left_join_keys: list[str],
    seed_pipeline: str | None,
) -> pl.DataFrame:
    return join_key_resolver.normalize_join_key_columns(
        merged_df,
        left_join_keys,
        pipeline=seed_pipeline,
    )


def prepare_dependency_join_frames(
    *,
    deduplicator: EnricherDeduplicatorService,
    join_key_resolver: JoinKeyResolverProtocol,
    renamer: ColumnRenamerService,
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
    normalized_merged = normalize_dependency_join_inputs(
        join_key_resolver=join_key_resolver,
        merged_df=merged_df,
        left_join_keys=left_join_keys,
        seed_pipeline=seed_pipeline,
    )
    prepared_dep = prepare_qualified_right_join_dataframe(
        source_df=dep_df,
        pipeline=dep.pipeline,
        join_keys=right_join_keys,
        deduplicator=deduplicator,
        join_key_resolver=join_key_resolver,
        renamer=renamer,
        logger=logger,
        field_alias_resolver=field_alias_resolver,
        drop_system_columns=drop_system_columns,
        log_message="Renamed dependency columns to qualified format",
        log_field_name="dependency",
    )
    return normalized_merged, prepared_dep


def resolve_composite_join_context(
    *,
    join_key_resolver: JoinKeyResolverProtocol,
    logger: LoggerPort,
    prepared_context: PreparedDependencyJoinContext,
    metadata: CompositeJoinContext,
    dependency: str,
) -> ResolvedCompositeJoinContext | None:
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
        join_key_set=build_asymmetric_join_key_set(
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
