"""Architecture guardrails for Stream B entity config-surface residual plateau."""

from __future__ import annotations

import pytest

import json
from pathlib import Path
from typing import Any

import yaml

from scripts.engineering.qa.config_surface_governance import INTENTIONAL_PREFIXES
from scripts.engineering.qa.report_config_surface_backlog import (
    BACKLOG_PATH,
    build_backlog,
)
from scripts.schema.generate_config_matrix import (
    _collect_family_configs,
    _family_metrics,
)

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = PROJECT_ROOT / "reports/quality/config-discrepancy-baseline.json"
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"

RESIDUAL_CATEGORIES = frozenset(
    {
        "extraction_params_entity_specific",
        "filter_metadata_entity_specific",
        "gold_filter_entity_specific",
        "pipeline_overrides",
        "quality_metadata_entity_specific",
        "schema_field_aliases_entity_specific",
        "silver_filter_entity_specific",
        "quality_thresholds",
    }
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_scorecard() -> dict[str, Any]:
    payload = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_hash_policy_is_common_across_entity_effective_family() -> None:
    """All governed entity configs must expose root hash_policy after Stream B."""
    family = _collect_family_configs()["entity_effective"]
    all_keys = {key for values in family.values() for key in values}
    common = set.intersection(*(set(values.keys()) for values in family.values()))
    required = {
        "hash_policy",
        "hash_policy.provider",
        "hash_policy.entity",
        "hash_policy.hash_policy.algorithm",
        "hash_policy.hash_policy.include_fields",
    }
    missing = sorted(required - common)
    assert not missing, f"hash_policy keys must be common across entities: {missing}"
    assert "hash_policy" in all_keys


def test_entity_residual_backlog_matches_live_metrics_and_scorecard() -> None:
    """Committed backlog artifact must mirror live residual metrics and scorecard."""
    backlog = build_backlog()
    baseline = _load_json(BASELINE_PATH)
    scorecard = _load_scorecard()

    live_entity = _family_metrics(_collect_family_configs()["entity_effective"])
    baseline_entity = baseline["families"]["entity_effective"]
    scorecard_entity = scorecard["config_surface_ratchet"]["families"]["entity_effective"][
        "metrics"
    ]

    assert backlog["entity_effective"]["partial_key_count"] == live_entity[
        "raw_inconsistent_parameter_count"
    ]
    assert baseline_entity == live_entity
    assert live_entity["inconsistent_parameter_count"] == 0
    assert (
        scorecard_entity["inconsistent_parameter_count"]["current_count"]
        == live_entity["inconsistent_parameter_count"]
    )
    assert backlog["entity_effective"]["actionable_partial_key_count"] == 0


def test_entity_residual_partial_keys_are_intentional_only() -> None:
    """Residual entity drift must fall into documented intentional categories."""
    backlog = _load_json(BACKLOG_PATH)
    entity = backlog["entity_effective"]
    categories = entity["categories"]

    assert set(categories) <= RESIDUAL_CATEGORIES
    assert entity["partial_key_count"] == sum(
        block["key_count"] for block in categories.values()
    )

    for block in categories.values():
        for entry in block["keys"]:
            key = entry["key"]
            assert any(
                key == prefix
                or key.startswith(f"{prefix}.")
                or key.startswith(prefix)
                for prefix in INTENTIONAL_PREFIXES
            ), f"Unexpected residual key outside intentional prefixes: {key}"


def test_composite_runtime_config_surface_is_fully_aligned() -> None:
    """Composite runtime family must remain at zero inconsistent keys."""
    metrics = _family_metrics(_collect_family_configs()["composite_runtime"])
    assert metrics["inconsistent_parameter_count"] == 0
