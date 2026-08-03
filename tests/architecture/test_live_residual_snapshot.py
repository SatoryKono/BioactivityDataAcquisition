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
"""Live residual snapshot freeze for architecture closeout non-growth (#6891)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from tests.architecture._live_residual import (
    LIVE_RESIDUAL_SNAPSHOT,
    assert_residual_not_grown,
    load_live_residual_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.architecture


def test_live_residual_snapshot_artifact_exists_and_has_policy_shape() -> None:
    payload = load_live_residual_snapshot()
    assert payload["linked_issue"] == "#6891"
    assert payload["parent_epic"] == "#6890"
    assert payload["policy"]["direction"] == "shrink_only"
    assert payload["policy"]["tech_debt_budget_growth"] == "forbidden"
    assert isinstance(payload["hotspot_families"], dict)
    assert payload["hotspot_families"]
    assert payload["dead_code"]["repo_wide_untriaged_zero_import_candidate_count"] == 0
    assert payload["module_coverage"]["uncovered_module_count"] == 0
    assert payload["module_coverage"]["unmeasured_module_count"] == 0


def test_live_residual_snapshot_is_not_regressed_by_live_hotspot_metrics() -> None:
    """Hotspot residual may only shrink relative to the committed live snapshot."""
    from scripts.engineering.qa.hotspot_family_metrics import (
        collect_hotspot_family_metrics,
    )

    committed = load_live_residual_snapshot()
    try:
        live_rows = collect_hotspot_family_metrics(active_only=True)
    except OSError as exc:
        pytest.skip(f"live hotspot scan blocked by OS I/O: {exc}")
    for row in live_rows:
        live = asdict(row)
        name = str(live["name"])
        committed_row = committed["hotspot_families"][name]
        for key in ("files_ge_250_loc", "max_internal_fan_in", "total_loc"):
            assert_residual_not_grown(
                metric_name=f"{name}.{key}",
                live_value=int(live[key]),
                baseline_value=int(committed_row[key]),
            )
        assert_residual_not_grown(
            metric_name=f"{name}.helper_function_ratio",
            live_value=float(live["helper_function_ratio"]),
            baseline_value=float(committed_row["helper_function_ratio"]),
            epsilon=1e-9,
        )


def test_live_residual_snapshot_dead_code_and_clusters_match_committed_artifacts() -> (
    None
):
    committed = load_live_residual_snapshot()
    dead = json.loads(
        (ROOT / "reports/quality/dead-code-inventory.json").read_text(encoding="utf-8")
    )
    summary = dead["summary"]
    for key in (
        "repo_wide_zero_import_candidate_count",
        "repo_wide_untriaged_zero_import_candidate_count",
        "repo_wide_candidates_without_owner_tests_count",
    ):
        assert_residual_not_grown(
            metric_name=f"dead_code.{key}",
            live_value=int(summary[key]),
            baseline_value=int(committed["dead_code"][key]),
        )

    backlog = json.loads(
        (ROOT / "reports/quality/config-surface-backlog.json").read_text(
            encoding="utf-8"
        )
    )
    clusters = backlog.get("duplication_audit", {}).get("clusters", [])
    live_clusters = (
        len(clusters)
        if isinstance(clusters, list)
        else int(
            backlog.get("duplication_audit", {})
            .get("summary", {})
            .get("duplicate_cluster_count", 0)
        )
    )
    assert_residual_not_grown(
        metric_name="config_surface.duplicate_cluster_count",
        live_value=live_clusters,
        baseline_value=int(committed["config_surface"]["duplicate_cluster_count"]),
    )


def test_historical_tech_debt_closeout_json_artifacts_remain_present() -> None:
    """Evidence of closed issue packs remains as reports, not thrashing freezes.

    ARCH-CR2-09: require parseable JSON objects (not mere path existence) so a
    truncated/corrupt closeout cannot satisfy the gate.
    """
    closeouts = sorted(
        (ROOT / "reports" / "quality").glob("tech-debt-issues-*-closeout.json")
    )
    assert closeouts, "expected historical tech-debt closeout JSON artifacts"
    assert len(closeouts) >= 1
    for path in closeouts:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert payload, f"closeout JSON must be a non-empty object: {path.name}"
        assert path.is_file()
    assert LIVE_RESIDUAL_SNAPSHOT.is_file()
    snapshot = json.loads(LIVE_RESIDUAL_SNAPSHOT.read_text(encoding="utf-8"))
    assert isinstance(snapshot, dict)
    assert snapshot, "live residual snapshot must be a non-empty object"
