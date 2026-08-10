"""Unit tests for config-surface duplication projection filtering."""

from __future__ import annotations

import pytest

from scripts.engineering.qa.report_config_surface_backlog import (
    _is_composite_layer_projection_cluster,
    _is_composite_runtime_contract_mirror,
)

pytestmark = pytest.mark.unit


def test_composite_runtime_contract_mirror_requires_matching_entity() -> None:
    cluster = {
        "block_path": "composite.merge.column_groups",
        "occurrences": [
            {
                "path": "configs/composites/activity.yaml",
                "surface_kind": "composite_config",
                "block_path": "composite.merge.column_groups",
            },
            {
                "path": "configs/entities/composite/activity.yaml",
                "surface_kind": "entity_config",
                "block_path": "schema.column_groups",
            },
        ],
    }

    assert _is_composite_runtime_contract_mirror(cluster) is True
    cluster["occurrences"][1]["path"] = "configs/entities/composite/target.yaml"
    assert _is_composite_runtime_contract_mirror(cluster) is False


def test_composite_layer_projection_requires_silver_gold_pair() -> None:
    cluster = {
        "block_path": "schema.gold.include_groups",
        "occurrences": [
            {
                "path": "configs/entities/composite/activity.yaml",
                "surface_kind": "entity_config",
                "block_path": "schema.silver.include_groups",
            },
            {
                "path": "configs/entities/composite/activity.yaml",
                "surface_kind": "entity_config",
                "block_path": "schema.gold.include_groups",
            },
        ],
    }

    assert _is_composite_layer_projection_cluster(cluster) is True
    cluster["occurrences"][1]["block_path"] = "schema.bronze.include_groups"
    assert _is_composite_layer_projection_cluster(cluster) is False
