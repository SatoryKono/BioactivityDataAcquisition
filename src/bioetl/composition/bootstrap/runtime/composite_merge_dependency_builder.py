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
from bioetl.composition.bootstrap.runtime.composite_merge_dependencies_bundle import (
    MergeDependenciesBundle,
)
from bioetl.composition.factories.services.polars_join_adapter import PolarsJoinBridge
from bioetl.domain.composite.strategy import MergeStrategy
from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
    current_protein_class_target_type_mapping,
    is_protein_class_target_type_mapping_initialized,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.ports import LoggerPort


def build_merge_dependencies(
    *,
    config: CompositeConfig,
    logger: LoggerPort,
    resolve_join_how: Callable[[MergeStrategy], JoinHow],
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy],
    system_columns_to_drop: frozenset[str],
    target_type_mapping_data: ProteinClassTargetTypeMappingData | None = None,
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
    join_service = JoinExecutorService(
        logger=logger,
        join_type_resolver=_create_join_type_resolver(
            config.merge.strategy, resolve_join_how
        ),
    )
    join_executor = PolarsJoinBridge(join_service)
    resolved_mapping = target_type_mapping_data
    if resolved_mapping is None and is_protein_class_target_type_mapping_initialized():
        resolved_mapping = current_protein_class_target_type_mapping()
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
    dependency_joiner.bind_target_type_mapping(resolved_mapping)
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
        order_service=order_service,
        coalesce_policy=coalesce_policy,
        conflict_resolver=conflict_resolver,
        join_planner=join_planner,
    )


__all__ = ["build_merge_dependencies"]


def _create_join_type_resolver(
    merge_strategy: MergeStrategy,
    resolve_join_how: Callable[[MergeStrategy], JoinHow],
) -> Callable[[], JoinHow]:
    """Create a join type resolver function for the given merge strategy."""

    return lambda: resolve_join_how(merge_strategy)
