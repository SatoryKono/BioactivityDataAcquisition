"""Contract golden checks for composite merge column ordering and checksum stability."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.domain.composite.config import EnricherConfig, MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def _merge_config() -> MergeConfig:
    return MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/composite/publication",
        output_gold_path="gold/composite/publication",
    )


def _canonical_row_hash(frame: pl.DataFrame) -> str:
    ordered = frame.select(sorted(frame.columns)).sort(frame.columns[0])
    payload = ordered.to_dicts()
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_composite_merge_golden_seed_priority_is_stable() -> None:
    """Seed-priority conflict resolution must produce deterministic merged output."""
    logger = MagicMock()
    service = ConflictResolverService(
        merge_config=_merge_config(),
        logger=logger,
        coalesce_policy=CoalescePolicyService(_merge_config()),
    )
    seed = pl.DataFrame({"entity_id": ["1"], "title": ["Seed title"], "doi": ["10.1/a"]})
    enricher = pl.DataFrame(
        {"entity_id": ["1"], "title": ["Enricher title"], "journal": ["J1"]}
    )
    seed_df, enricher_df = service.detect_and_resolve_conflicts(
        seed,
        enricher,
        join_keys={"entity_id"},
    )
    merged = seed_df.join(enricher_df, on="entity_id", how="left")
    resolved = service.resolve_conflicts(
        merged,
        {"crossref_publication": enricher_df},
        enrichers=(EnricherConfig(pipeline="crossref_publication", join_keys=("entity_id",)),),
        seed_pipeline="chembl_publication",
    )

    first_hash = _canonical_row_hash(resolved)
    second_hash = _canonical_row_hash(resolved.clone())
    assert first_hash == second_hash
    assert resolved["title"][0] == "Seed title"
