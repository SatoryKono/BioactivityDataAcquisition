"""Golden snapshot checks for MergeService risk-prone semantics."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import polars as pl

from bioetl.application.composite.aggregator import EnricherAggregatorService
from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_orderer import ColumnOrdererService
from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrdererService,
)
from bioetl.application.composite.column_renamer import ColumnRenamerService
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.dependency_joiner import DependencyJoinerService
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.join_execution import JoinExecutorService
from bioetl.application.composite.join_key_resolution import JoinKeyResolverService
from bioetl.application.composite.join_planner import JoinPlannerService
from bioetl.application.composite.merger import MergeService
from bioetl.domain.composite.config import MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


FIXTURES_DIR = Path("tests/fixtures/golden/composite")


def _build_merge_service() -> MergeService:
    """Create MergeService with deterministic config for golden checks."""
    merge_config = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/composite/golden",
        output_gold_path="gold/composite/golden",
    )
    storage = MagicMock()
    logger = MagicMock()
    deduplicator = EnricherDeduplicatorService(logger)
    aggregator = EnricherAggregatorService(logger)
    renamer = ColumnRenamerService(logger)
    orderer = ColumnOrdererService(logger)
    priority_orderer = ColumnPriorityOrdererService(logger)
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
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        dependency_joiner=dependency_joiner,
    )
    return MergeService(
        merge_config=merge_config,
        storage=storage,
        logger=logger,
        deduplicator=deduplicator,
        aggregator=aggregator,
        renamer=renamer,
        orderer=orderer,
        priority_orderer=priority_orderer,
        coalesce_policy=coalesce_policy,
        conflict_resolver=conflict_resolver,
        join_planner=join_planner,
    )


def test_conflict_resolution_seed_priority_golden_snapshot() -> None:
    """Seed-priority coalesce semantics stay stable on golden dataset."""
    fixture_path = FIXTURES_DIR / "conflict_resolution_seed_priority.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    merge_service = _build_merge_service()
    df = pl.DataFrame(fixture["input_rows"])

    result = merge_service._resolve_conflicts(
        df=df,
        enricher_dfs={},
        enrichers=[],
        seed_pipeline=fixture["seed_pipeline"],
    )

    assert result.columns == ["doi", "chembl.publication.title"]
    assert result.to_dicts() == fixture["expected_rows"]


def test_column_order_golden_snapshot() -> None:
    """Column ordering remains stable for composite output snapshot."""
    fixture_path = FIXTURES_DIR / "column_order_snapshot.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    merge_service = _build_merge_service()
    ordered_columns = merge_service._orderer.order_column_names(
        fixture["input_columns"]
    )

    assert ordered_columns == fixture["expected_order"]
