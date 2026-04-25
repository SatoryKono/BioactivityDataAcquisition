"""Stable composite-runtime seam for composition bootstrap wiring.

This module intentionally re-exports the composite runtime collaborators that
``composition.bootstrap.runtime`` needs to assemble execution support, merge
dependencies, and runner services. Bootstrap code should prefer this seam over
importing many individual ``application.composite`` implementation modules.
"""

from __future__ import annotations

from bioetl.application.composite.aggregator import EnricherAggregator
from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointServiceContext,
)
from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrderer,
)
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.application.composite.cross_validator import EnrichmentCrossValidator
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.dependency_joiner import DependencyJoinerService
from bioetl.application.composite.dependency_key_resolvers import (
    create_chained_key_resolver,
    create_seed_key_resolver,
)
from bioetl.application.composite.dependency_progress_tracker import (
    DependencyProgressService,
)
from bioetl.application.composite.dependency_result_mapper import (
    DependencyResultService,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.join_execution import JoinHow
from bioetl.application.composite.join_key_normalization import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    JoinKeyNormalizationPolicy,
    stringify_join_key_value,
    validate_join_key_normalization_policies,
)
from bioetl.application.composite.join_key_resolution import JoinKeyResolverService
from bioetl.application.composite.join_planner import (
    JoinPlannerService,
    JoinPreparationCollaborators,
)
from bioetl.application.composite.join_planner_helpers import (
    parse_pipeline_name,
    resolve_field_aliases_from_registry,
)
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.merger import MergeCollaboratorGroup, MergeService
from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
    CompositePreflightValidator,
)
from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositePipelineRunnerService,
)
from bioetl.application.composite.runtime_models import CompositeRunnerDependencies
from bioetl.application.core.runner import PipelineRunner

__all__ = [
    "JOIN_KEY_NORMALIZATION_POLICIES",
    "CoalescePolicyService",
    "ColumnOrderService",
    "ColumnPriorityOrderer",
    "ColumnRenamer",
    "CompositeCheckpointService",
    "CompositeCheckpointServiceContext",
    "CompositeLifecycleObserverService",
    "CompositePipelineRunner",
    "CompositePipelineRunnerService",
    "CompositePreflightValidationService",
    "CompositePreflightValidator",
    "CompositeRunnerDependencies",
    "ConflictResolverService",
    "DependencyCoordinatorService",
    "DependencyJoinerService",
    "DependencyProgressService",
    "DependencyResultService",
    "EnricherAggregator",
    "EnricherDeduplicatorService",
    "EnrichmentCoordinatorService",
    "EnrichmentCrossValidator",
    "FSMStateHelperService",
    "JoinHow",
    "JoinKeyNormalizationPolicy",
    "JoinKeyResolverService",
    "JoinPlannerService",
    "JoinPreparationCollaborators",
    "KeyExtractorService",
    "MergeCollaboratorGroup",
    "MergeService",
    "PipelineRunner",
    "create_chained_key_resolver",
    "create_seed_key_resolver",
    "parse_pipeline_name",
    "resolve_field_aliases_from_registry",
    "stringify_join_key_value",
    "validate_join_key_normalization_policies",
]
