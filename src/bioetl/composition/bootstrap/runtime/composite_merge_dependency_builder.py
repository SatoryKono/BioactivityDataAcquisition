"""Merge-dependency builders for composite runtime composition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from bioetl.application.composite.aggregator import EnricherAggregator
from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrderer,
)
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.dependency_joiner import DependencyJoinerService
from bioetl.application.composite.join_execution import JoinHow
from bioetl.application.composite.join_key_normalization import (
    JoinKeyNormalizationPolicy,
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
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    MergeDependenciesBundle,
)
from bioetl.composition.factories.services.polars_join_adapter import PolarsJoinAdapter
from bioetl.domain.composite.strategy import MergeStrategy

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import LoggerPort


def build_merge_dependencies(
    *,
    config: CompositeConfig,
    logger: LoggerPort,
    resolve_join_how: Callable[[MergeStrategy], JoinHow],
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy],
    system_columns_to_drop: frozenset[str],
) -> MergeDependenciesBundle:
    """Assemble merge-specific collaborators used by MergeService."""
    merge_column_groups = getattr(config.merge, "column_groups", None)
    deduplicator = EnricherDeduplicatorService(logger)
    aggregator = EnricherAggregator(logger)
    renamer = ColumnRenamer(logger)
    orderer = ColumnOrderer(
        logger,
        column_groups=merge_column_groups if merge_column_groups else None,
    )
    priority_orderer = ColumnPriorityOrderer(logger)
    coalesce_policy = CoalescePolicyService(logger, priority_orderer)
    conflict_resolver = ConflictResolverService(
        config.merge,
        logger,
        coalesce_policy,
    )
    join_key_resolver = JoinKeyResolverService(
        normalization_policies=normalization_policies,
        parse_pipeline_name=parse_pipeline_name,
    )
    join_executor = PolarsJoinAdapter(
        logger=logger,
        join_type_resolver=lambda: resolve_join_how(config.merge.strategy),
    )
    dependency_joiner = DependencyJoinerService(
        logger=logger,
        deduplicator=deduplicator,
        renamer=renamer,
        conflict_resolver=conflict_resolver,
        field_alias_resolver=resolve_field_aliases_from_registry,
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        system_columns_to_drop=system_columns_to_drop,
    )
    join_planner = JoinPlannerService(
        merge_config=config.merge,
        logger=logger,
        preparation=JoinPreparationCollaborators(
            deduplicator=deduplicator,
            aggregator=aggregator,
            renamer=renamer,
            conflict_resolver=conflict_resolver,
        ),
        field_alias_resolver=resolve_field_aliases_from_registry,
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        dependency_joiner=dependency_joiner,
    )
    return MergeDependenciesBundle(
        deduplicator=deduplicator,
        aggregator=aggregator,
        renamer=renamer,
        orderer=orderer,
        priority_orderer=priority_orderer,
        coalesce_policy=coalesce_policy,
        conflict_resolver=conflict_resolver,
        join_planner=join_planner,
    )


__all__ = ["build_merge_dependencies"]
