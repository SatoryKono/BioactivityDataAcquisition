"""Architecture ratchet for normalization surface coverage reporting."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from bioetl.domain.normalization.profiles.chembl_json_ordering_policy import (
    CHEMBL_JSON_ORDERING_POLICY,
)
from scripts.docs.generate_pipeline_normalization_field_matrix import (
    PROFILE_META_PASSTHROUGH_KPI,
    PROFILE_NON_META_PASSTHROUGH_FREE_KPI,
    PROFILE_SET_LIKE_JSON_STRING_KPI,
    build_profile_semantic_invariants,
    build_field_matrix_rows,
    build_surface_coverage_kpis,
)

SURFACE_COVERAGE_BUDGETS: dict[str, float] = {
    "entity_record": 100.0,
    "composite_join_key": 100.0,
    "control_plane_reproducibility": 100.0,
}

PROFILE_SEMANTIC_BUDGETS: dict[str, float] = {
    PROFILE_META_PASSTHROUGH_KPI: 100.0,
    PROFILE_SET_LIKE_JSON_STRING_KPI: 100.0,
    PROFILE_NON_META_PASSTHROUGH_FREE_KPI: 100.0,
}


def _coverage_values_by_surface() -> dict[str, float]:
    return {
        str(kpi["surface"]): float(cast(float, kpi["value_pct"]))
        for kpi in build_surface_coverage_kpis(build_field_matrix_rows())
    }


def _assert_surface_coverage_budgets(values_by_surface: dict[str, float]) -> None:
    regressions = [
        (surface, values_by_surface.get(surface, 0.0), budget)
        for surface, budget in SURFACE_COVERAGE_BUDGETS.items()
        if values_by_surface.get(surface, 0.0) < budget
    ]
    assert not regressions, (
        "normalization surface coverage regressed: "
        + "; ".join(
            f"{surface}={actual:.2f}% below budget {budget:.2f}%"
            for surface, actual, budget in regressions
        )
        + ". Restore surface-specific normalization coverage or intentionally rebaseline the ratchet."
    )


def _semantic_invariant_values_by_name() -> dict[str, float]:
    return {
        str(kpi["name"]): float(cast(float, kpi["value_pct"]))
        for kpi in build_profile_semantic_invariants()
    }


def _assert_profile_semantic_budgets(values_by_name: dict[str, float]) -> None:
    regressions = [
        (name, values_by_name.get(name, 0.0), budget)
        for name, budget in PROFILE_SEMANTIC_BUDGETS.items()
        if values_by_name.get(name, 0.0) < budget
    ]
    assert not regressions, (
        "normalization profile semantic invariants regressed: "
        + "; ".join(
            f"{name}={actual:.2f}% below budget {budget:.2f}%"
            for name, actual, budget in regressions
        )
        + ". Restore shipped profile semantics or intentionally rebaseline the ratchet."
    )


def _field_matrix_rows_by_coordinate() -> dict[tuple[str, str], dict[str, object]]:
    return {
        (str(row["pipeline_name"]), str(row["field_name"])): row
        for row in build_field_matrix_rows()
    }


def _assert_chembl_json_ordering_policy_is_matrix_visible(
    rows_by_coordinate: dict[tuple[str, str], dict[str, object]],
) -> None:
    regressions: list[str] = []
    for policy in CHEMBL_JSON_ORDERING_POLICY:
        coordinate = (policy.pipeline_name, policy.field_name)
        row = rows_by_coordinate.get(coordinate)
        if row is None:
            regressions.append(f"{policy.pipeline_name}.{policy.field_name}=missing")
            continue

        expected_set_like = "true" if policy.is_set_like else "false"
        actual_set_like = str(row["set_like"])
        actual_hash_ordering = str(row["hash_ordering"])
        if (
            actual_set_like != expected_set_like
            or actual_hash_ordering != policy.order_semantics
        ):
            regressions.append(
                f"{policy.pipeline_name}.{policy.field_name}: "
                f"set_like={actual_set_like}, "
                f"hash_ordering={actual_hash_ordering}"
            )

    assert not regressions, (
        "ChEMBL JSON ordering matrix ratchet regressed: "
        + "; ".join(regressions)
        + ". Keep chembl_json_ordering_policy.py, profiles, and matrix output aligned."
    )


def _assert_chembl_json_ordering_policy_has_no_hash_config_mirrors() -> None:
    config_paths = {
        "chembl_activity": Path("configs/entities/chembl/activity.yaml"),
        "chembl_assay": Path("configs/entities/chembl/assay.yaml"),
        "chembl_molecule": Path("configs/entities/chembl/molecule.yaml"),
        "chembl_publication": Path("configs/entities/chembl/publication.yaml"),
        "chembl_target": Path("configs/entities/chembl/target.yaml"),
        "chembl_target_component": Path(
            "configs/entities/chembl/target_component.yaml"
        ),
    }
    regressions: list[str] = []
    for pipeline_name, config_path in sorted(config_paths.items()):
        config_text = config_path.read_text(encoding="utf-8")
        if "field_ordering:" in config_text:
            regressions.append(
                f"{pipeline_name}: remove hash_policy.hash_policy.field_ordering mirror"
            )

    assert not regressions, (
        "ChEMBL JSON ordering config mirrors must stay absent: "
        + "; ".join(regressions)
        + ". Keep JSON ordering semantics runtime-authoritative only via "
        + "chembl_json_ordering_policy.py and profile set_like_fields."
    )


def test_normalization_surface_coverage_does_not_regress_below_reviewed_budgets() -> (
    None
):
    _assert_surface_coverage_budgets(_coverage_values_by_surface())


def test_surface_coverage_ratchet_reports_surface_specific_regression() -> None:
    with pytest.raises(
        AssertionError,
        match=(
            r"normalization surface coverage regressed: "
            r"composite_join_key=75\.00% below budget 100\.00%"
        ),
    ):
        _assert_surface_coverage_budgets(
            {
                "entity_record": 100.0,
                "composite_join_key": 75.0,
                "control_plane_reproducibility": 100.0,
            }
        )


def test_profile_semantic_invariants_do_not_regress_below_reviewed_budgets() -> None:
    _assert_profile_semantic_budgets(_semantic_invariant_values_by_name())


def test_chembl_json_ordering_policy_does_not_drift_from_field_matrix() -> None:
    _assert_chembl_json_ordering_policy_is_matrix_visible(
        _field_matrix_rows_by_coordinate()
    )


def test_chembl_json_ordering_policy_does_not_reappear_in_hash_config_mirrors() -> None:
    _assert_chembl_json_ordering_policy_has_no_hash_config_mirrors()


def test_profile_semantic_ratchet_reports_named_regression() -> None:
    with pytest.raises(
        AssertionError,
        match=(
            r"normalization profile semantic invariants regressed: "
            r"shipped_profile_meta_passthrough_pct=95\.00% below budget 100\.00%"
        ),
    ):
        _assert_profile_semantic_budgets(
            {
                PROFILE_META_PASSTHROUGH_KPI: 95.0,
                PROFILE_SET_LIKE_JSON_STRING_KPI: 100.0,
                PROFILE_NON_META_PASSTHROUGH_FREE_KPI: 100.0,
            }
        )
