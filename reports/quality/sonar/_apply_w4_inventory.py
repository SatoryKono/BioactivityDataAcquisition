"""W4: extract helpers for dashboard + module-coverage inventory complexity."""
from __future__ import annotations

from pathlib import Path

DASH = Path("scripts/engineering/qa/report_dashboard_inventory.py")
COVERAGE = Path("scripts/engineering/qa/report_module_coverage_inventory.py")

DASH_HELPER = '''

def _dashboard_item_health_issues(
    item: DashboardInventoryItem,
    *,
    parity_issues: dict[str, list[str]],
    deployed_issues: dict[str, list[str]],
) -> list[str]:
    """Collect non-canonical / missing-field issues for one dashboard inventory row."""
    uid = str(item["uid"])
    issues: list[str] = []
    if not uid or uid == "None":
        issues.append("missing uid")
    if not item.get("title"):
        issues.append("missing title")
    if item.get("style") != "dark":
        issues.append(f"non-canonical style={item.get('style')!r}")
    if item.get("timezone") != "browser":
        issues.append(f"non-canonical timezone={item.get('timezone')!r}")
    if item.get("editable") is not True:
        issues.append(f"editable must be true, got {item.get('editable')!r}")
    if item.get("graphTooltip") != 1:
        issues.append(f"graphTooltip must be 1, got {item.get('graphTooltip')!r}")
    hide_controls = item.get("hideControls")
    if hide_controls != "<missing>" and hide_controls is not False:
        issues.append(
            f"hideControls, when exported, must be false, got {hide_controls!r}"
        )
    issues.extend(parity_issues.get(uid, []))
    issues.extend(deployed_issues.get(uid, []))
    return issues


'''

OLD_HEALTH_LOOP = '''    for item in inventory:
        uid = str(item["uid"])
        issues: list[str] = []
        if not uid or uid == "None":
            issues.append("missing uid")
        if not item.get("title"):
            issues.append("missing title")
        if item.get("style") != "dark":
            issues.append(f"non-canonical style={item.get('style')!r}")
        if item.get("timezone") != "browser":
            issues.append(f"non-canonical timezone={item.get('timezone')!r}")
        if item.get("editable") is not True:
            issues.append(f"editable must be true, got {item.get('editable')!r}")
        if item.get("graphTooltip") != 1:
            issues.append(f"graphTooltip must be 1, got {item.get('graphTooltip')!r}")
        hide_controls = item.get("hideControls")
        if hide_controls != "<missing>" and hide_controls is not False:
            issues.append(
                f"hideControls, when exported, must be false, got {hide_controls!r}"
            )
        issues.extend(parity_issues.get(uid, []))
        issues.extend(deployed_issues.get(uid, []))
        status = "healthy" if not issues else "degraded"
        if status == "healthy":
            healthy += 1
        else:
            degraded += 1
        dashboard_health: DashboardHealthItem = {
            **item,
            "status": status,
            "issues": issues,
        }
        dashboards.append(dashboard_health)
'''

NEW_HEALTH_LOOP = '''    for item in inventory:
        uid = str(item["uid"])
        issues = _dashboard_item_health_issues(
            item,
            parity_issues=parity_issues,
            deployed_issues=deployed_issues,
        )
        status = "healthy" if not issues else "degraded"
        if status == "healthy":
            healthy += 1
        else:
            degraded += 1
        dashboard_health: DashboardHealthItem = {
            **item,
            "status": status,
            "issues": issues,
        }
        dashboards.append(dashboard_health)
'''

COVERAGE_HELPER = '''

def _coverage_gate_modes(gates: dict[str, Any]) -> tuple[float, str, str, set[str]]:
    """Parse gate config into min_delta, tier modes, and ranked target paths."""
    regression_cfg = gates.get("regression", {})
    min_delta = 0.01
    if isinstance(regression_cfg, dict):
        raw_delta = regression_cfg.get("min_delta_points", min_delta)
        if isinstance(raw_delta, int | float):
            min_delta = float(raw_delta)

    enforcement_cfg = gates.get("enforcement", {})
    tier_mode = "warn"
    ranked_target_tier_mode = "warn"
    if isinstance(enforcement_cfg, dict):
        raw_tier_mode = enforcement_cfg.get("tier_violation_mode", tier_mode)
        if isinstance(raw_tier_mode, str):
            tier_mode = raw_tier_mode
        raw_ranked_target_tier_mode = enforcement_cfg.get(
            "ranked_target_tier_violation_mode",
            ranked_target_tier_mode,
        )
        if isinstance(raw_ranked_target_tier_mode, str):
            ranked_target_tier_mode = raw_ranked_target_tier_mode

    ranked_target_paths: set[str] = set()
    coverage_tail_cfg = gates.get("coverage_tail", {})
    if isinstance(coverage_tail_cfg, dict):
        ranked_targets = coverage_tail_cfg.get("ranked_targets", [])
        if isinstance(ranked_targets, list):
            for row in ranked_targets:
                if not isinstance(row, dict):
                    continue
                path = row.get("path")
                if isinstance(path, str) and path:
                    ranked_target_paths.add(path)
    return min_delta, tier_mode, ranked_target_tier_mode, ranked_target_paths


'''

OLD_CFG = '''    exempt = _exempt_paths(gates)
    regression_cfg = gates.get("regression", {})
    min_delta = 0.01
    if isinstance(regression_cfg, dict):
        raw_delta = regression_cfg.get("min_delta_points", min_delta)
        if isinstance(raw_delta, int | float):
            min_delta = float(raw_delta)

    enforcement_cfg = gates.get("enforcement", {})
    tier_mode = "warn"
    ranked_target_tier_mode = "warn"
    if isinstance(enforcement_cfg, dict):
        raw_tier_mode = enforcement_cfg.get("tier_violation_mode", tier_mode)
        if isinstance(raw_tier_mode, str):
            tier_mode = raw_tier_mode
        raw_ranked_target_tier_mode = enforcement_cfg.get(
            "ranked_target_tier_violation_mode",
            ranked_target_tier_mode,
        )
        if isinstance(raw_ranked_target_tier_mode, str):
            ranked_target_tier_mode = raw_ranked_target_tier_mode

    ranked_target_paths: set[str] = set()
    coverage_tail_cfg = gates.get("coverage_tail", {})
    if isinstance(coverage_tail_cfg, dict):
        ranked_targets = coverage_tail_cfg.get("ranked_targets", [])
        if isinstance(ranked_targets, list):
            for row in ranked_targets:
                if not isinstance(row, dict):
                    continue
                path = row.get("path")
                if isinstance(path, str) and path:
                    ranked_target_paths.add(path)

    baseline_by_path = _baseline_coverage_by_path(baseline_payload)
'''

NEW_CFG = '''    exempt = _exempt_paths(gates)
    min_delta, tier_mode, ranked_target_tier_mode, ranked_target_paths = (
        _coverage_gate_modes(gates)
    )
    baseline_by_path = _baseline_coverage_by_path(baseline_payload)
'''


def main() -> None:
    t = DASH.read_text(encoding="utf-8")
    if "_dashboard_item_health_issues(" not in t:
        t = t.replace(
            "def _build_health_summary(",
            DASH_HELPER + "def _build_health_summary(",
            1,
        )
    if OLD_HEALTH_LOOP not in t:
        if "issues = _dashboard_item_health_issues(" in t:
            print("dashboard loop already simplified")
        else:
            raise SystemExit("dashboard health loop missing")
    else:
        t = t.replace(OLD_HEALTH_LOOP, NEW_HEALTH_LOOP, 1)
        print("dashboard loop replaced")
    DASH.write_text(t, encoding="utf-8", newline="\n")

    t = COVERAGE.read_text(encoding="utf-8")
    if "_coverage_gate_modes(" not in t:
        t = t.replace(
            "def evaluate_module_coverage_gates(",
            COVERAGE_HELPER + "def evaluate_module_coverage_gates(",
            1,
        )
    if OLD_CFG not in t:
        if "_coverage_gate_modes(gates)" in t:
            print("coverage cfg already simplified")
        else:
            raise SystemExit("coverage cfg missing")
    else:
        t = t.replace(OLD_CFG, NEW_CFG, 1)
        print("coverage cfg replaced")
    COVERAGE.write_text(t, encoding="utf-8", newline="\n")
    print("inventory complexity extracts done")


if __name__ == "__main__":
    main()
