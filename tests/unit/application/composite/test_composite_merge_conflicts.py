"""Unit tests for composite merge conflict detection and resolution policies."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.domain.composite.config_merge import MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

pytestmark = pytest.mark.unit


def _service() -> ConflictResolverService:
    merge_config = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/composite/publication",
        output_gold_path="gold/composite/publication",
    )
    return ConflictResolverService(
        merge_config=merge_config,
        logger=MagicMock(),
        coalesce_policy=CoalescePolicyService(merge_config),
    )


def test_detect_and_resolve_conflicts_renames_enricher_columns() -> None:
    """Overlapping non-key columns must be suffixed on the enricher side only."""
    service = _service()
    seed = pl.DataFrame({"entity_id": ["1"], "title": ["seed"]})
    enricher = pl.DataFrame({"entity_id": ["1"], "title": ["enricher"]})

    _, renamed = service.detect_and_resolve_conflicts(
        seed,
        enricher,
        join_keys={"entity_id"},
    )

    assert "title" in seed.columns
    assert "title.A" in renamed.columns
    assert renamed["title.A"][0] == "enricher"


def test_find_next_suffix_skips_existing_columns() -> None:
    """Suffix allocation must skip occupied column names deterministically."""
    service = _service()
    existing = {"title", "title.A", "title.B"}

    assert service.find_next_suffix("title", existing) == "C"
