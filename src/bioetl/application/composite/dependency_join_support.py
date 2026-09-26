"""Public dependency-join helper exports.

Canonical consumers may still import the narrower builders/models/execution
modules directly, but this module is the sanctioned aggregate seam.
"""

from __future__ import annotations

from bioetl.application.composite.dependency_join_context_builders import (
    build_composite_join_metadata,
    build_prepared_dependency_join_context,
    build_single_key_join_metadata,
    prepare_dependency_join_frames,
    resolve_left_pipeline,
)
from bioetl.application.composite.dependency_join_execution import (
    build_composite_join_execution_plan,
    build_single_key_join_execution_plan,
    execute_dependency_join,
    execute_planned_dependency_join,
    log_missing_composite_key_columns,
    resolve_composite_join_context,
    resolve_single_key_join_context,
)
from bioetl.application.composite.dependency_join_models import (
    CompositeJoinContext,
    DependencyJoinExecutionSpec,
    PreparedDependencyJoinContext,
    ResolvedCompositeJoinContext,
    ResolvedSingleKeyJoinContext,
    SingleKeyJoinContext,
)

__all__ = [
    "CompositeJoinContext",
    "DependencyJoinExecutionSpec",
    "PreparedDependencyJoinContext",
    "ResolvedCompositeJoinContext",
    "ResolvedSingleKeyJoinContext",
    "SingleKeyJoinContext",
    "build_composite_join_execution_plan",
    "build_composite_join_metadata",
    "build_prepared_dependency_join_context",
    "build_single_key_join_execution_plan",
    "build_single_key_join_metadata",
    "execute_dependency_join",
    "execute_planned_dependency_join",
    "log_missing_composite_key_columns",
    "prepare_dependency_join_frames",
    "resolve_composite_join_context",
    "resolve_left_pipeline",
    "resolve_single_key_join_context",
]
