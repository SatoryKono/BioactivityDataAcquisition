"""Shared test support for composite merge/join service wiring."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from bioetl.application.composite.column_service import ColumnOrderService

if TYPE_CHECKING:
    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.column_service import ColumnOrderService
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.application.composite.join_execution import JoinHow
    from bioetl.application.composite.join_planner import JoinPlannerService
    from bioetl.application.composite.merger import MergeService
    from bioetl.domain.composite.config import MergeConfig


def _default_field_alias_resolver(_pipeline: str) -> dict[str, str] | None:
    """Return no field aliases for default merge-test wiring."""
    return None


def _default_join_type_resolver() -> JoinHow:
    """Return the canonical default join type for merge-test wiring."""
    return "left"


def _default_field_alias_resolver_for_merge(_pipeline: str) -> dict[str, str] | None:
    return None


def _default_join_type_for_merge() -> JoinHow:
    return "left"


def build_join_planner_service(
    *,
    merge_config: MergeConfig,
    logger: MagicMock,
    deduplicator: EnricherDeduplicatorService | MagicMock,
    aggregator: EnricherAggregator | MagicMock,
    renamer: ColumnRenamer | MagicMock,
    conflict_resolver: ConflictResolverService | MagicMock,
    field_alias_resolver: Callable[[str], dict[str, str] | None] | None = None,
    join_type_resolver: Callable[[], JoinHow] | None = None,
) -> JoinPlannerService:
    """Create JoinPlannerService with canonical collaborator wiring for tests."""
    from bioetl.application.composite.dependency_joiner import DependencyJoinerService
    from bioetl.application.composite.join_execution import JoinExecutorService
    from bioetl.application.composite.join_key_normalization import (
        JOIN_KEY_NORMALIZATION_POLICIES,
    )
    from bioetl.application.composite.join_key_resolution import JoinKeyResolverService
    from bioetl.application.composite.join_planner import (
        JoinPlannerService,
        JoinPreparationCollaborators,
    )

    if field_alias_resolver is None:
        field_alias_resolver = _default_field_alias_resolver
    if join_type_resolver is None:
        join_type_resolver = _default_join_type_resolver

    # Create ResolverHelper with normalization policies (new API)
    from bioetl.application.composite.join_key_resolution import ResolverHelper

    resolver_helper = ResolverHelper(
        logger=logger,
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
    )

    join_key_resolver = JoinKeyResolverService(
        resolver_helper=resolver_helper,
        parse_pipeline_name=JoinPlannerService._parse_pipeline_name,
    )
    join_executor = JoinExecutorService(
        logger=logger,
        join_type_resolver=join_type_resolver,
    )
    dependency_joiner = DependencyJoinerService(
        logger=logger,
        deduplicator=deduplicator,
        renamer=renamer,
        conflict_resolver=conflict_resolver,
        field_alias_resolver=field_alias_resolver,
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        system_columns_to_drop=JoinPlannerService._SYSTEM_COLUMNS_TO_DROP,
    )
    return JoinPlannerService(
        merge_config=merge_config,
        logger=logger,
        preparation=JoinPreparationCollaborators(
            deduplicator=deduplicator,
            aggregator=aggregator,
            renamer=renamer,
            conflict_resolver=conflict_resolver,
        ),
        field_alias_resolver=field_alias_resolver,
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        dependency_joiner=dependency_joiner,
    )


def build_merge_service(
    *,
    merge_config: MergeConfig,
    logger: MagicMock,
    storage: MagicMock,
) -> MergeService:
    """Create a fully wired MergeService for composite unit tests."""
    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.application.composite.coalesce_policy import CoalescePolicyService
    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.application.composite.merger import (
        MergeCollaboratorGroup,
        MergeService,
    )

    deduplicator = EnricherDeduplicatorService(logger)
    aggregator = EnricherAggregator(logger)
    renamer = ColumnRenamer(logger)
    orderer = ColumnOrderService(logger)
    coalesce_policy = CoalescePolicyService(logger, order_service=orderer)
    conflict_resolver = ConflictResolverService(
        merge_config=merge_config,
        logger=logger,
        coalesce_policy=coalesce_policy,
    )
    join_planner = build_join_planner_service(
        merge_config=merge_config,
        logger=logger,
        deduplicator=deduplicator,
        aggregator=aggregator,
        renamer=renamer,
        conflict_resolver=conflict_resolver,
        field_alias_resolver=_default_field_alias_resolver_for_merge,
        join_type_resolver=_default_join_type_for_merge,
    )
    return MergeService(
        merge_config=merge_config,
        storage=storage,
        logger=logger,
        silver_reader=storage,
        collaborators=MergeCollaboratorGroup(
            deduplicator=deduplicator,
            aggregator=aggregator,
            renamer=renamer,
            order_service=orderer,  # New API: order_service is now required
            coalesce_policy=coalesce_policy,
            conflict_resolver=conflict_resolver,
            join_planner=join_planner,
            orderer=None,  # Old orderer parameter is now optional
            priority_orderer=None,  # Old priority_orderer parameter is now optional
        ),
    )
