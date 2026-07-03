"""Governance checks for normalization evidence surfaces."""

from __future__ import annotations

import pytest

from pathlib import Path

from bioetl.domain.normalization.profiles.registry import (
    NORMALIZATION_PROFILE_REGISTRY,
)

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NORMALIZATION_PLAN_PATH = (
    PROJECT_ROOT / "docs/05-engineering/normalization_plan_P0_P6.md"
)
NORMALIZATION_PLAN_REDIRECT_PATH = (
    PROJECT_ROOT / "docs/05-engineering/normalization-plan-P0-P6.md"
)
CONFIG_MATRIX_PATH = PROJECT_ROOT / "docs/04-reference/config_comparison_matrix.csv"
LEGACY_CONFIG_MATRIX_PATH = PROJECT_ROOT / "docs/config_comparison_matrix.csv"


def test_normalization_plan_mentions_all_shipped_profile_coordinates() -> None:
    plan_text = NORMALIZATION_PLAN_PATH.read_text(encoding="utf-8")

    for provider, entity in sorted(NORMALIZATION_PROFILE_REGISTRY):
        assert f"`{provider}.{entity}`" in plan_text


def test_normalization_plan_references_governed_evidence_surfaces() -> None:
    plan_text = NORMALIZATION_PLAN_PATH.read_text(encoding="utf-8")

    assert "report_normalization_fallback_inventory.py" in plan_text
    assert "pipeline_normalization_field_matrix.md" in plan_text
    assert "join_keys.py" in plan_text
    assert "join_key_normalization.py" in plan_text
    assert "chembl_json_ordering_policy.py" in plan_text
    assert "chembl_observed_values.yaml" in plan_text
    assert "non_chembl_identifier_cases.yaml" in plan_text
    assert "publication_structured_fields.py" in plan_text
    assert "explicit_profile_coverage_pct" in plan_text
    assert "composite_join_key_policy_coverage_pct" in plan_text
    assert "control_plane_normalization_coverage_pct" in plan_text


def test_normalization_plan_references_final_dq_schema_reconciliation() -> None:
    plan_text = NORMALIZATION_PLAN_PATH.read_text(encoding="utf-8")

    for matrix_column in (
        "controlled_vocabulary_source",
        "policy_scope",
        "hash_ordering",
        "strictness",
        "schema_coverage",
        "dq_coverage",
    ):
        assert matrix_column in plan_text

    assert "test_chembl_enum_normalization_policy.py" in plan_text
    assert "test_chembl_activity_flag_policy.py" in plan_text
    assert "test_normalization_cross_layer_contracts.py" in plan_text
    assert "test_normalization_surface_coverage_ratchet.py" in plan_text
    assert "test_chembl_observed_value_fixtures.py" in plan_text


def test_normalization_plan_compatibility_redirect_is_explicit() -> None:
    redirect_text = NORMALIZATION_PLAN_REDIRECT_PATH.read_text(encoding="utf-8")

    assert "Status: compatibility-redirect" in redirect_text
    assert "normalization_plan_P0_P6.md" in redirect_text


def test_config_comparison_matrix_has_single_canonical_owner() -> None:
    assert CONFIG_MATRIX_PATH.exists()
    assert not LEGACY_CONFIG_MATRIX_PATH.exists()
