"""Regression snapshots for CompositeConfig serialization."""

from __future__ import annotations

import pytest

from bioetl.domain.composite.config import (
    CompositeConfig,
    DependencyConfig,
    EnricherConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


pytestmark = pytest.mark.unit


def _build_composite_config() -> CompositeConfig:
    return CompositeConfig(
        name="composite_publication",
        version="1.0.0",
        seed=SeedConfig(
            pipeline="chembl_publication",
            output_keys=("doi", "pmid"),
            silver_table="silver/chembl/publication",
        ),
        dependencies=(
            DependencyConfig(
                pipeline="chembl_document",
                join_keys=("doi",),
                required=False,
                timeout_seconds=600,
                silver_table="silver/chembl/document",
                filter_fields=("doi",),
            ),
        ),
        enrichers=(
            EnricherConfig(
                pipeline="crossref_publication",
                join_keys=("doi",),
                required=True,
                timeout_seconds=900,
            ),
        ),
        merge=MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver/composite/publication",
            output_gold_path="gold/composite/publication",
            sort_by_silver=("doi",),
            sort_by_gold=("doi",),
        ),
    )


def test_composite_config_to_dict_snapshot() -> None:
    config = _build_composite_config()

    assert config.to_dict() == {
        "name": "composite_publication",
        "version": "1.0.0",
        "seed": {
            "pipeline": "chembl_publication",
            "output_keys": ["doi", "pmid"],
            "silver_table": "silver/chembl/publication",
        },
        "dependencies": [
            {
                "pipeline": "chembl_document",
                "join_keys": ["doi"],
                "required": False,
                "timeout_seconds": 600,
                "silver_table": "silver/chembl/document",
                "filter_fields": ["doi"],
            }
        ],
        "enrichers": [
            {
                "pipeline": "crossref_publication",
                "join_keys": ["doi"],
                "required": True,
                "timeout_seconds": 900,
            }
        ],
        "merge": {
            "strategy": "left_outer",
            "conflict_resolution": "seed_priority",
            "output_silver_path": "silver/composite/publication",
            "output_gold_path": "gold/composite/publication",
            "sort_by_silver": ["doi"],
            "sort_by_gold": ["doi"],
        },
    }


def test_composite_config_from_dict_roundtrip_snapshot() -> None:
    original = _build_composite_config()
    serialized = original.to_dict()

    restored = CompositeConfig.from_dict(serialized)

    assert restored.to_dict() == serialized
    assert restored.name == original.name
    assert restored.version == original.version
    assert restored.seed.output_keys == original.seed.output_keys
    assert restored.merge.strategy == original.merge.strategy
    assert restored.merge.conflict_resolution == original.merge.conflict_resolution
