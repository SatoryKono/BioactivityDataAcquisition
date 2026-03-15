"""Shared test support for composite merge/join service wiring."""

from __future__ import annotations

from unittest.mock import MagicMock

from bioetl.application.composite.aggregator import EnricherAggregator
from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrderer,
)
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.dependency_joiner import DependencyJoinerService
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.join_execution import JoinExecutorService
from bioetl.application.composite.join_key_resolution import JoinKeyResolverService
from bioetl.application.composite.join_planner import JoinPlannerService
from bioetl.application.composite.merger import MergeCollaboratorGroup, MergeService
from bioetl.domain.composite.config import MergeConfig


def build_merge_service(
    *,
    merge_config: MergeConfig,
    logger: MagicMock,
    storage: MagicMock,
) -> MergeService:
    """Create a fully wired MergeService for composite unit tests."""
    deduplicator = EnricherDeduplicatorService(logger)
    aggregator = EnricherAggregator(logger)
    renamer = ColumnRenamer(logger)
    orderer = ColumnOrderer(logger)
    priority_orderer = ColumnPriorityOrderer(logger)
    coalesce_policy = CoalescePolicyService(logger, priority_orderer)
    conflict_resolver = ConflictResolverService(
        merge_config=merge_config,
        logger=logger,
        coalesce_policy=coalesce_policy,
    )
    join_key_resolver = JoinKeyResolverService(
        normalize_join_keys=JoinPlannerService._NORMALIZE_JOIN_KEYS,
        parse_pipeline_name=JoinPlannerService._parse_pipeline_name,
    )
    join_executor = JoinExecutorService(
        logger=logger,
        join_type_resolver=lambda: "left",
    )
    dependency_joiner = DependencyJoinerService(
        logger=logger,
        deduplicator=deduplicator,
        renamer=renamer,
        conflict_resolver=conflict_resolver,
        field_alias_resolver=lambda _pipeline: None,
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        system_columns_to_drop=JoinPlannerService._SYSTEM_COLUMNS_TO_DROP,
    )
    join_planner = JoinPlannerService(
        merge_config=merge_config,
        logger=logger,
        deduplicator=deduplicator,
        aggregator=aggregator,
        renamer=renamer,
        conflict_resolver=conflict_resolver,
        field_alias_resolver=lambda _pipeline: None,
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        dependency_joiner=dependency_joiner,
    )
    return MergeService(
        merge_config=merge_config,
        storage=storage,
        logger=logger,
        collaborators=MergeCollaboratorGroup(
            deduplicator=deduplicator,
            aggregator=aggregator,
            renamer=renamer,
            orderer=orderer,
            priority_orderer=priority_orderer,
            coalesce_policy=coalesce_policy,
            conflict_resolver=conflict_resolver,
            join_planner=join_planner,
        ),
    )
