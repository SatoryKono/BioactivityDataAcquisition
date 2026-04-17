"""Merge-dependency builders for composite runtime composition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from bioetl.application.composite.helpers.resolver_helper import ResolverHelper
from bioetl.application.composite.join_execution import JoinExecutorService
from bioetl.application.composite.runtime_wiring_api import (
    CoalescePolicyService,
    ColumnOrderService,
    ColumnRenamer,
    ConflictResolverService,
    DependencyJoinerService,
    EnricherAggregator,
    EnricherDeduplicatorService,
    JoinHow,
    JoinKeyNormalizationPolicy,
    JoinKeyResolverService,
    JoinPlannerService,
    JoinPreparationCollaborators,
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
    order_service = ColumnOrderService(
        logger,
        column_groups=merge_column_groups if merge_column_groups else None,
    )
    coalesce_policy = CoalescePolicyService(logger, order_service=order_service)
    conflict_resolver = ConflictResolverService(
        config.merge,
        logger,
        coalesce_policy,
    )
    resolver_helper = ResolverHelper(
        logger=logger,
        normalization_policies=normalization_policies,
    )
    join_key_resolver = JoinKeyResolverService(
        resolver_helper=resolver_helper,
        parse_pipeline_name=parse_pipeline_name,
    )
    # Create the actual JoinExecutorService first
    join_service = JoinExecutorService(
        logger=logger,
        join_type_resolver=lambda: resolve_join_how(config.merge.strategy),
    )
    # Wrap it with the real adapter
    join_executor = PolarsJoinAdapter(join_service)
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
        orderer=order_service,
        priority_orderer=None,
        order_service=order_service,
        coalesce_policy=coalesce_policy,
        conflict_resolver=conflict_resolver,
        join_planner=join_planner,
    )


__all__ = ["build_merge_dependencies"]
