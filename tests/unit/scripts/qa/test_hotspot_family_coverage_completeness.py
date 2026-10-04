"""Coverage completeness must follow the actual family, not a historic count."""

from __future__ import annotations

import pytest

from scripts.engineering.qa.report_module_coverage_inventory import (
    _build_one_hotspot_family_coverage,
)

pytestmark = pytest.mark.unit


def _row(index: int, status: str = "fully_covered") -> dict[str, object]:
    measured = status != "unmeasured"
    return {
        "module": f"example.module_{index}",
        "path": f"src/example/module_{index}.py",
        "coverage_status": status,
        "coverage_percent": (0 if status == "uncovered" else 100) if measured else None,
        "executable_lines": 100 if measured else None,
        "covered_lines": 100 if status == "fully_covered" else 0,
    }


@pytest.mark.parametrize("count", [0, 51, 55, 56])
def test_complete_family_tracks_actual_members(count: int) -> None:
    result = _build_one_hotspot_family_coverage(
        [_row(index) for index in range(count)],
        {"require_all_modules_covered": True, "min_covered_line_percent": 94.9},
    )
    assert result["threshold_status"] == ("pass" if count else "fail")


@pytest.mark.parametrize("status", ["unmeasured", "uncovered"])
def test_new_uncovered_member_fails_even_above_historical_floor(status: str) -> None:
    rows = [_row(index) for index in range(55)] + [_row(55, status)]
    result = _build_one_hotspot_family_coverage(
        rows,
        {
            "require_all_modules_covered": True,
            "min_covered_line_percent": 94.9,
            "allowlisted_unmeasured_paths": ["src/example/module_55.py"],
        },
    )
    assert result["threshold_status"] == "fail"


def test_completeness_preserves_line_coverage_threshold() -> None:
    row = _row(0, "partially_covered")
    row.update(coverage_percent=94, covered_lines=94)
    result = _build_one_hotspot_family_coverage(
        [row],
        {"require_all_modules_covered": True, "min_covered_line_percent": 94.9},
    )
    assert result["threshold_status"] == "fail"


def test_completeness_does_not_override_explicit_count_floor() -> None:
    result = _build_one_hotspot_family_coverage(
        [_row(0)],
        {"require_all_modules_covered": True, "min_measured_module_count": 2},
    )
    assert result["threshold_status"] == "fail"
