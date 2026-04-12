"""Architecture ratchet for normalization surface coverage reporting."""

from __future__ import annotations

from typing import cast

import pytest

from scripts.docs.generate_pipeline_normalization_field_matrix import (
    build_field_matrix_rows,
    build_surface_coverage_kpis,
)

SURFACE_COVERAGE_BUDGETS: dict[str, float] = {
    "entity_record": 100.0,
    "composite_join_key": 100.0,
    "control_plane_reproducibility": 100.0,
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


def test_normalization_surface_coverage_does_not_regress_below_reviewed_budgets() -> None:
    _assert_surface_coverage_budgets(_coverage_values_by_surface())


def test_surface_coverage_ratchet_reports_surface_specific_regression() -> None:
    with pytest.raises(
        AssertionError,
        match=(
            "normalization surface coverage regressed: "
            "composite_join_key=75.00% below budget 100.00%"
        ),
    ):
        _assert_surface_coverage_budgets(
            {
                "entity_record": 100.0,
                "composite_join_key": 75.0,
                "control_plane_reproducibility": 100.0,
            }
        )
