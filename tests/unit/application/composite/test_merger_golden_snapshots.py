"""Golden snapshot checks for MergeService risk-prone semantics."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import polars as pl

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
    return MergeService(merge_config=merge_config, storage=storage, logger=logger)


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
