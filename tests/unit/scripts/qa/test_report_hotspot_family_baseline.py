# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.hotspot_family_metrics import (
    collect_internal_fan_in_census,
    count_internal_fan_in,
)
from scripts.engineering.qa.report_hotspot_family_baseline import (
    _at_budget_fan_in_views,
    _budget_review_notes_for_family,
    _budget_warnings_for_family,
    _compact_distribution,
    _merge_reviewed_baseline_metrics,
    _resolve_snapshot_date,
    _write_text,
)

pytestmark = pytest.mark.unit


def test_write_text_atomically_replaces_existing_file(tmp_path: Path) -> None:
    output_path = tmp_path / "hotspot-family-baseline.md"
    output_path.write_text("stale\n", encoding="utf-8")

    _write_text(output_path, "current\n")

    assert output_path.read_text(encoding="utf-8") == "current\n"
    assert list(tmp_path.glob(".hotspot-family-baseline.md.*.tmp")) == []


def test_resolve_snapshot_date_prefers_reviewed_scorecard_snapshot() -> None:
    scorecard = {
        "hotspot_family_ratchets": {
            "snapshot_date": "2026-03-24",
        }
    }

    assert _resolve_snapshot_date(scorecard) == "2026-03-24"


def test_resolve_snapshot_date_falls_back_when_reviewed_snapshot_missing() -> None:
    scorecard = {
        "hotspot_family_ratchets": {},
    }

    snapshot_date = _resolve_snapshot_date(scorecard)

    assert isinstance(snapshot_date, str)
    assert len(snapshot_date) == 10


def test_budget_warnings_report_only_exceeded_budget_metrics() -> None:
    family = {
        "files_ge_250_loc": 11,
        "max_internal_fan_in": 10,
        "bounded_growth_budgets": {
            "files_ge_250_loc": 10,
            "max_internal_fan_in": 10,
        },
    }

    assert _budget_warnings_for_family(family) == ["over_budget:files_ge_250_loc=11/10"]


def test_budget_warnings_ignore_metrics_at_or_below_budget() -> None:
    family = {
        "files_ge_250_loc": 10,
        "bounded_growth_budgets": {"files_ge_250_loc": 10},
    }

    assert _budget_warnings_for_family(family) == []


def test_budget_review_notes_report_near_and_at_budget_metrics() -> None:
    family = {
        "files_ge_250_loc": 8,
        "max_internal_fan_in": 10,
        "bounded_growth_budgets": {
            "files_ge_250_loc": 10,
            "max_internal_fan_in": 10,
        },
    }

    assert _budget_review_notes_for_family(family) == [
        "near_budget:files_ge_250_loc=8/10",
        "at_budget:max_internal_fan_in=10/10",
    ]


def test_merge_reviewed_baseline_metrics_preserves_live_measured_census() -> None:
    family = {
        "name": "application_services_control_plane",
        "ratchet_stage": "reviewed-baseline",
        "metrics": {
            "duplication_clusters": 17,
            "files": 66,
            "total_loc": 12998,
            "files_ge_250_loc": 22,
            "helper_function_ratio": 0.496,
            "max_internal_fan_in": 6,
            "max_internal_fan_in_module": "bioetl.application.services.control_plane.helpers",
        },
    }
    measured = {
        "name": "application_services_control_plane",
        "duplication_clusters": 17,
        "files": 71,
        "total_loc": 13453,
        "files_ge_250_loc": 21,
        "helper_function_ratio": 0.499,
        "max_internal_fan_in": 6,
        "max_internal_fan_in_module": "bioetl.application.services.control_plane.helpers",
    }

    merged = _merge_reviewed_baseline_metrics(family=family, measured=measured)

    assert merged["files"] == 71
    assert merged["total_loc"] == 13453
    assert merged["files_ge_250_loc"] == 21
    assert merged["helper_function_ratio"] == 0.499


def test_merge_reviewed_baseline_metrics_preserves_live_metrics_for_active_family() -> (
    None
):
    family = {
        "name": "composition_bootstrap_runtime",
        "ratchet_stage": "active",
        "metrics": {"files_ge_250_loc": 99},
    }
    measured = {
        "name": "composition_bootstrap_runtime",
        "files_ge_250_loc": 5,
    }

    merged = _merge_reviewed_baseline_metrics(family=family, measured=measured)

    assert merged["files_ge_250_loc"] == 5


def test_merge_reviewed_baseline_metrics_keeps_live_fan_in_census() -> None:
    census = {
        "distribution": {"0": 2, "1": 1},
        "modules": [
            {"module": "bioetl.fam.a", "fan_in": 0, "runtime_importers": []},
        ],
        "max_fan_in": 1,
        "max_modules": ["bioetl.fam.b"],
    }
    measured = {
        "name": "application_services_control_plane",
        "max_internal_fan_in": 1,
        "internal_fan_in_census": census,
    }

    merged = _merge_reviewed_baseline_metrics(
        family={"metrics": {"max_internal_fan_in": 9}},
        measured=measured,
    )

    assert merged["internal_fan_in_census"] == census
    assert merged["max_internal_fan_in"] == 1


def test_at_budget_fan_in_views_select_modules_at_current_cap() -> None:
    family = {
        "bounded_growth_budgets": {"max_internal_fan_in": 2},
        "internal_fan_in_census": {
            "modules": [
                {"module": "bioetl.fam.a", "fan_in": 1, "runtime_importers": ["bioetl.fam.b"]},
                {"module": "bioetl.fam.b", "fan_in": 2, "runtime_importers": ["bioetl.fam.a"]},
                {"module": "bioetl.fam.c", "fan_in": 2, "runtime_importers": ["bioetl.fam.d"]},
            ]
        },
    }

    views = _at_budget_fan_in_views(family)

    assert views["at_budget_module_count"] == 2
    assert [row["module"] for row in views["at_budget_modules"]] == [
        "bioetl.fam.b",
        "bioetl.fam.c",
    ]


def test_compact_distribution_orders_buckets_numerically() -> None:
    assert _compact_distribution({"2": 12, "0": 2, "1": 28}) == "0:2, 1:28, 2:12"


def _write_family_tree(tmp_path: Path, sources: dict[str, str]) -> tuple[Path, list[Path]]:
    src_root = tmp_path / "src" / "bioetl"
    family_root = src_root / "fam"
    family_root.mkdir(parents=True)
    written: list[Path] = []
    for relative, source in sources.items():
        path = family_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        written.append(path)
    return src_root, written


def test_internal_fan_in_census_is_deterministic_and_covers_runtime_edges(
    tmp_path: Path,
) -> None:
    src_root, files = _write_family_tree(
        tmp_path,
        {
            "__init__.py": "",
            "a.py": "from . import b\n",
            "b.py": "from . import c\nfrom . import c\n",
            "c.py": (
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    from . import a\n"
                "from . import d\n"
            ),
            "d.py": "def load() -> None:\n    from . import b\n",
            "e.py": "",
        },
    )

    census = collect_internal_fan_in_census(files=files, src_root=src_root)
    wrapper = count_internal_fan_in(files=files, src_root=src_root)
    by_module = {row.module: row for row in census.modules}

    assert census.distribution == {"0": 3, "1": 2, "2": 1}
    assert tuple(row.module for row in census.modules) == (
        "bioetl.fam",
        "bioetl.fam.a",
        "bioetl.fam.b",
        "bioetl.fam.c",
        "bioetl.fam.d",
        "bioetl.fam.e",
    )
    assert by_module["bioetl.fam.b"].fan_in == 2
    assert by_module["bioetl.fam.b"].runtime_importers == (
        "bioetl.fam.a",
        "bioetl.fam.d",
    )
    assert by_module["bioetl.fam.c"].runtime_importers == ("bioetl.fam.b",)
    assert by_module["bioetl.fam.a"].fan_in == 0
    assert by_module["bioetl.fam"].fan_in == 0
    assert by_module["bioetl.fam.e"].fan_in == 0
    assert census.max_fan_in == 2
    assert census.max_modules == ("bioetl.fam.b",)
    assert wrapper == (census.max_fan_in, census.max_modules[-1])


def test_internal_fan_in_census_wrapper_returns_none_when_all_fan_in_zero(
    tmp_path: Path,
) -> None:
    src_root, files = _write_family_tree(
        tmp_path,
        {
            "__init__.py": "",
            "leaf.py": "",
        },
    )

    census = collect_internal_fan_in_census(files=files, src_root=src_root)
    wrapper = count_internal_fan_in(files=files, src_root=src_root)

    assert census.max_fan_in == 0
    assert census.distribution == {"0": 2}
    assert wrapper == (0, None)
