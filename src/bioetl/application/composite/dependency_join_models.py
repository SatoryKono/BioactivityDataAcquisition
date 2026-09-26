"""Data models for dependency join preparation and execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import polars as pl


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


@dataclass(frozen=True, slots=True)
class DependencyJoinExecutionSpec:
    """Execution plan separated from dependency join context preparation."""

    prepared_context: PreparedDependencyJoinContext
    join_key_set: set[str]
    execute_join: Callable[[pl.DataFrame, pl.DataFrame], pl.DataFrame]
    log_message: str
    log_fields: Mapping[str, object]
