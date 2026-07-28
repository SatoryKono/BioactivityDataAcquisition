"""Architecture guardrails for hotspot-family duplication ratchets."""

from __future__ import annotations

import pytest

import json
from pathlib import Path

import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"
ISSUE_BACKED_HOTSPOT_FAMILIES: dict[str, str] = {}
ACTIVE_ISSUE_BACKED_HOTSPOT_FAMILIES = {
    "application_services_control_plane": "#6818",
    "composition_bootstrap_runtime": "#4548",
    "composition_runtime_builders": "#6621",
}
ACTIVE_HOTSPOT_CLOSEOUT_FAMILIES = {
    "composition_factories_pipeline",
}


def _load_scorecard() -> dict[str, object]:
    payload = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all(isinstance(row, dict) for row in rows)
    return rows


def _match_family_targets(
    rows: list[dict[str, object]],
    *,
    path_prefixes: list[str],
) -> list[dict[str, object]]:
    normalized_prefixes = tuple(prefix.rstrip("/") for prefix in path_prefixes)
    matched: list[dict[str, object]] = []
    for row in rows:
        target = row.get("target")
        if not isinstance(target, str):
            continue
        if any(target.startswith(prefix) for prefix in normalized_prefixes):
            matched.append(row)
    return matched


def _family_is_clean(
    rows: list[dict[str, object]],
    *,
    path_prefixes: list[str],
) -> bool:
    matched = _match_family_targets(rows, path_prefixes=path_prefixes)
    return bool(matched) and all(row.get("duplicate_count") == 0 for row in matched)


def test_hotspot_family_duplication_budgets_hold_reviewed_baseline() -> None:
    """Hotspot-family duplication budgets must not grow past the reviewed baseline."""
    scorecard = _load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)
    assert hotspot_policy.get("mode") == "fail-fast"

    artifact_policy = hotspot_policy.get("artifact_policy", {})
    assert isinstance(artifact_policy, dict)
    assert artifact_policy.get("expected_direction") == "downward"
    baseline_artifact = artifact_policy.get("baseline_artifact")
    history_artifact = artifact_policy.get("history_artifact")
    latest_reviewed_snapshot = artifact_policy.get("latest_reviewed_snapshot")
    assert isinstance(baseline_artifact, str) and baseline_artifact
    assert isinstance(history_artifact, str) and history_artifact
    assert isinstance(latest_reviewed_snapshot, str) and latest_reviewed_snapshot

    baseline_payload = _load_json(PROJECT_ROOT / baseline_artifact)
    history_records = _load_jsonl(PROJECT_ROOT / history_artifact)
    assert any(
        record.get("snapshot_date") == latest_reviewed_snapshot
        for record in history_records
    ), "Hotspot duplication history must include the latest reviewed snapshot"

    baseline_summary = baseline_payload.get("summary", {})
    assert isinstance(baseline_summary, dict)
    assert baseline_summary.get("snapshot_date") == latest_reviewed_snapshot

    baseline_targets = baseline_payload.get("targets", [])
    assert isinstance(baseline_targets, list)
    baseline_target_rows = [row for row in baseline_targets if isinstance(row, dict)]

    families = hotspot_policy.get("families", [])
    assert isinstance(families, list) and families
    enforced_families = [
        family
        for family in families
        if isinstance(family, dict)
        and family.get("ratchet_stage") in {"active", "reviewed-baseline"}
    ]
    assert enforced_families, "Expected at least one enforced hotspot family ratchet"

    for family in enforced_families:
        assert "bounded-growth" in str(family.get("ratchet_scope"))
        metrics = family.get("metrics", {})
        assert isinstance(metrics, dict)
        duplication_budget = metrics.get("duplication_clusters")
        assert isinstance(duplication_budget, int) and duplication_budget >= 0

        expected_action = family.get("expected_action")
        assert isinstance(expected_action, str)
        assert "duplication" in expected_action
        assert "file-growth" in expected_action
        assert "fan-in" in expected_action

        path_prefixes = family.get("path_prefixes", [])
        assert isinstance(path_prefixes, list) and path_prefixes
        matched_rows = _match_family_targets(
            baseline_target_rows,
            path_prefixes=[
                prefix for prefix in path_prefixes if isinstance(prefix, str)
            ],
        )
        assert matched_rows, (
            f"Hotspot family {family.get('name')} must appear in the latest "
            "duplication baseline"
        )
        actual_duplicate_count = max(
            int(row["duplicate_count"])
            for row in matched_rows
            if isinstance(row.get("duplicate_count"), int)
        )
        assert actual_duplicate_count <= duplication_budget, (
            f"Hotspot family {family.get('name')} has {actual_duplicate_count} "
            f"duplicate clusters, exceeding reviewed budget {duplication_budget}."
        )

        if duplication_budget == 0:
            required_clean_snapshots = int(
                artifact_policy["confirming_clean_snapshots_required"]
            )
            clean_history = [
                record
                for record in history_records
                if isinstance(record.get("targets"), list)
                and _family_is_clean(
                    [row for row in record["targets"] if isinstance(row, dict)],
                    path_prefixes=[
                        prefix for prefix in path_prefixes if isinstance(prefix, str)
                    ],
                )
            ]
            assert len(clean_history) >= required_clean_snapshots, (
                f"Zero-budget family {family.get('name')} requires at least "
                f"{required_clean_snapshots} confirming clean snapshots"
            )
            assert all(
                record.get("snapshot_date") == latest_reviewed_snapshot
                for record in clean_history[-required_clean_snapshots:]
            ), (
                f"Zero-budget family {family.get('name')} must be confirmed by "
                "the latest reviewed clean snapshots"
            )


def test_reviewed_baseline_hotspot_families_match_reviewed_duplication_snapshot() -> (
    None
):
    """Reviewed-baseline families must stay aligned with the reviewed family baseline."""
    scorecard = _load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)

    family_baseline_path = PROJECT_ROOT / "reports/quality/hotspot-family-baseline.json"
    baseline_payload = _load_json(family_baseline_path)
    baseline_summary = baseline_payload.get("summary", {})
    assert isinstance(baseline_summary, dict)
    assert baseline_summary.get("snapshot_date") == hotspot_policy.get("snapshot_date")

    baseline_families = baseline_payload.get("families", [])
    assert isinstance(baseline_families, list)
    baseline_family_rows = [
        row
        for row in baseline_families
        if isinstance(row, dict) and row.get("ratchet_stage") == "reviewed-baseline"
    ]

    families = hotspot_policy.get("families", [])
    assert isinstance(families, list) and families
    reviewed_families = [
        family
        for family in families
        if isinstance(family, dict)
        and family.get("ratchet_stage") == "reviewed-baseline"
    ]
    assert {
        str(family.get("name")) for family in reviewed_families
    } == {
        str(row.get("name")) for row in baseline_family_rows
    }

    for family in reviewed_families:
        family_name = family.get("name")
        assert isinstance(family_name, str) and family_name
        metrics = family.get("metrics", {})
        assert isinstance(metrics, dict)
        matched_rows = [
            row for row in baseline_family_rows if row.get("name") == family_name
        ]
        assert matched_rows, (
            f"Reviewed-baseline family {family_name} must exist in the reviewed "
            "family baseline"
        )

        baseline_row = matched_rows[0]
        assert baseline_row.get("ratchet_scope") == family.get("ratchet_scope")
        assert baseline_row.get("files_ge_250_loc") == metrics.get("files_ge_250_loc")
        assert baseline_row.get("max_internal_fan_in") == metrics.get(
            "max_internal_fan_in"
        )
        assert baseline_row.get("bounded_growth_budgets") == family.get(
            "bounded_growth_budgets"
        ), (
            f"Reviewed-baseline family {family_name} must keep scorecard and family "
            "baseline budgets in sync."
        )


def test_current_hotspot_closeout_families_are_issue_linked() -> None:
    """Debt closeout hotspot families must stay traceable to their GitHub issues."""
    scorecard = _load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)
    families = hotspot_policy.get("families", [])
    assert isinstance(families, list)
    by_name = {
        str(family["name"]): family for family in families if isinstance(family, dict)
    }

    for family_name, issue in ISSUE_BACKED_HOTSPOT_FAMILIES.items():
        family = by_name[family_name]
        assert family["linked_issue"] == issue
        assert family["ratchet_stage"] == "reviewed-baseline"

    for family_name, issue in ACTIVE_ISSUE_BACKED_HOTSPOT_FAMILIES.items():
        family = by_name[family_name]
        assert family["linked_issue"] == issue
        assert family["ratchet_stage"] == "active"

    for family_name in ACTIVE_HOTSPOT_CLOSEOUT_FAMILIES:
        family = by_name[family_name]
        assert family["linked_issue"] == "#4477"
        assert family["ratchet_stage"] == "active"

    application_core = by_name["application_core"]
    assert application_core["linked_issue"] == "#4554"
    assert application_core["ratchet_stage"] == "active"


def test_issue_4477_records_active_family_duplication_reduction() -> None:
    """Issue #4477 must stay backed by an actual active-family reduction."""
    scorecard = _load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)
    families = hotspot_policy.get("families", [])
    assert isinstance(families, list)

    reduced_issue_families: list[dict[str, object]] = []
    for family in families:
        if not isinstance(family, dict) or family.get("linked_issue") != "#4477":
            continue
        trend = family.get("trend", {})
        if not isinstance(trend, dict):
            continue
        if str(trend.get("status", "")).startswith("reduced_"):
            reduced_issue_families.append(family)
    assert reduced_issue_families, (
        "Issue #4477 closeout must include at least one active hotspot family "
        "with an explicit reduced_* trend note."
    )
