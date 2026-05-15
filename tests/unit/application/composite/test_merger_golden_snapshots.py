"""Golden snapshot checks for MergeService risk-prone semantics."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import polars as pl

from bioetl.application.composite.merger import MergeService
from bioetl.domain.composite.config import MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from tests.helpers.golden_files import load_json_fixture
from tests.unit.application.composite.merge_test_support import build_merge_service


FIXTURES_DIR = Path("tests/fixtures/golden/composite")


def _build_merge_service() -> MergeService:
    """Create MergeService with deterministic config for golden checks."""
    merge_config = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/composite/golden",
        output_gold_path="gold/composite/golden",
    )
    return build_merge_service(
        merge_config=merge_config,
        logger=MagicMock(),
        storage=MagicMock(),
    )


def test_conflict_resolution_seed_priority_golden_snapshot() -> None:
    """Seed-priority coalesce semantics stay stable on golden dataset."""
    fixture_path = FIXTURES_DIR / "conflict_resolution_seed_priority.json"
    fixture = load_json_fixture(fixture_path)

    merge_service = _build_merge_service()
    df = pl.DataFrame(fixture["input_rows"])

    result = merge_service._conflict_resolver.resolve_conflicts(
        df=df,
        _enricher_dfs={},
        enrichers=[],
        seed_pipeline=fixture["seed_pipeline"],
    )

    assert result.columns == ["doi", "chembl.publication.title"]
    assert result.to_dicts() == fixture["expected_rows"]


def test_column_order_golden_snapshot() -> None:
    """Column ordering remains stable for composite output snapshot."""
    fixture_path = FIXTURES_DIR / "column_order_snapshot.json"
    fixture = load_json_fixture(fixture_path)

    merge_service = _build_merge_service()
    ordered_columns = merge_service._orderer.get_ordered_columns(
        fixture["input_columns"]
    )

    assert ordered_columns == fixture["expected_order"]
