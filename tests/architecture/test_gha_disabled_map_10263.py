# pyright: reportArgumentType=false
"""Architecture guards for the disabled canonical GitHub Actions map (#10263)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
INVENTORY = ROOT / "docs" / "04-reference" / "github-actions-workflows.md"
POLICY = ROOT / "docs" / "00-project" / "governance" / "05-github-policy.md"
CI_MAP = ROOT / "docs" / "05-operations" / "ci-workflow-map.md"
HYGIENE = ROOT / ".github" / "PULL_REQUEST_HYGIENE.md"

ALLOWED_STATES = {"active", "disabled_manually"}
ALLOWED_DECISIONS = {"active", "keep-disabled"}
RE_ENABLED_OWNERS = {"docs.yml", "compiled-artifacts-block.yml"}
MUST_STAY_DISABLED = {
    "stale.yml",
    "pr-hygiene.yml",
    "reusable-setup.yml",
    "reusable-mermaid-setup.yml",
    "labeler.yml",
    "mutation-testing.yml",
    "vacuum.yml",
    "release.yml",
    "coderabbit.yml",
}


def _inventory_decision_rows(text: str) -> dict[str, tuple[str, str]]:
    """Parse File / GitHub live state / Decision from inventory tables."""
    rows: dict[str, tuple[str, str]] = {}
    in_keep_disabled_reasons = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## Keep-disabled reasons"):
            in_keep_disabled_reasons = True
            continue
        if in_keep_disabled_reasons and line.startswith("## "):
            in_keep_disabled_reasons = False
        if in_keep_disabled_reasons or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        file_cell = cells[0]
        if not (file_cell.startswith("`") and file_cell.endswith("`")):
            continue
        filename = file_cell[1:-1]
        if not filename.endswith(".yml"):
            continue
        state = cells[3].strip("`")
        decision = cells[4].strip("`")
        rows[filename] = (state, decision)
    return rows


def _table_first_column_yml(section: str) -> set[str]:
    found: set[str] = set()
    for raw in section.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        file_cell = cells[0] if cells else ""
        if file_cell.startswith("`") and file_cell.endswith(".yml`"):
            found.add(file_cell[1:-1])
    return found


def test_every_canonical_workflow_has_keep_disabled_or_active_decision() -> None:
    live = {path.name for path in WORKFLOWS_DIR.glob("*.yml")}
    rows = _inventory_decision_rows(INVENTORY.read_text(encoding="utf-8"))

    assert live == set(rows), (
        f"inventory decision rows != tracked workflows: "
        f"missing={sorted(live - set(rows))} extra={sorted(set(rows) - live)}"
    )
    for filename, (state, decision) in sorted(rows.items()):
        assert state in ALLOWED_STATES, filename
        assert decision in ALLOWED_DECISIONS, filename
        if decision == "active":
            assert state == "active", filename
        else:
            assert state == "disabled_manually", filename


def test_pr_gate_owners_are_active_and_deprecated_helpers_stay_disabled() -> None:
    rows = _inventory_decision_rows(INVENTORY.read_text(encoding="utf-8"))
    for filename in RE_ENABLED_OWNERS:
        assert rows[filename] == ("active", "active")
    for filename in MUST_STAY_DISABLED:
        assert rows[filename][1] == "keep-disabled", filename
        assert rows[filename][0] == "disabled_manually", filename


def test_keep_disabled_reasons_cover_every_keep_disabled_file() -> None:
    inventory = INVENTORY.read_text(encoding="utf-8")
    rows = _inventory_decision_rows(inventory)
    keep_disabled = {
        name for name, (_, decision) in rows.items() if decision == "keep-disabled"
    }
    reasons_section = inventory.split("## Keep-disabled reasons (#10263)", maxsplit=1)[
        1
    ].split("## Quick Routing", maxsplit=1)[0]
    documented_reasons = _table_first_column_yml(reasons_section)
    assert keep_disabled == documented_reasons


def test_ci_map_routes_only_active_lanes() -> None:
    ci_map = CI_MAP.read_text(encoding="utf-8")
    rows = _inventory_decision_rows(INVENTORY.read_text(encoding="utf-8"))
    active_section = ci_map.split("## Active workflow catalog", maxsplit=1)[1].split(
        "## Keep-disabled catalog", maxsplit=1
    )[0]
    disabled_section = ci_map.split("## Keep-disabled catalog (#10263)", maxsplit=1)[
        1
    ].split("## Docs-critical path", maxsplit=1)[0]
    active_files = {
        name for name, (_, decision) in rows.items() if decision == "active"
    }
    disabled_files = {
        name for name, (_, decision) in rows.items() if decision == "keep-disabled"
    }
    assert _table_first_column_yml(active_section) == active_files
    assert _table_first_column_yml(disabled_section) == disabled_files
    assert "stale.yml" not in active_section
    assert "`pr-hygiene.yml`" not in active_section


def test_scheduled_policy_does_not_claim_disabled_lanes_run() -> None:
    policy = POLICY.read_text(encoding="utf-8")
    section = policy.split("### 2.5 Scheduled & On-Demand", maxsplit=1)[1].split(
        "______________________________________________________________________",
        maxsplit=1,
    )[0]
    assert "keep-disabled" in section
    assert "**not** run" in section
    assert "Lane class" in section
    assert "YAML cadence" in section
    assert "currently executing" in section


def test_stale_and_pr_hygiene_are_aligned_as_keep_disabled() -> None:
    hygiene = HYGIENE.read_text(encoding="utf-8")
    stale = (WORKFLOWS_DIR / "stale.yml").read_text(encoding="utf-8")
    pr_hygiene = (WORKFLOWS_DIR / "pr-hygiene.yml").read_text(encoding="utf-8")

    assert "keep-disabled" in hygiene
    assert "#10263" in hygiene
    assert "21" in hygiene
    assert "14 days" in hygiene
    assert "KEEP-DISABLED (#10263)" in stale
    assert "KEEP-DISABLED (#10263)" in pr_hygiene
    assert "days-before-pr-stale: 14" in stale
    assert "AUTO_CLOSE_INACTIVE_DAYS = 21" in pr_hygiene


def test_deprecated_reusables_keep_disabled_comment() -> None:
    for name in ("reusable-setup.yml", "reusable-mermaid-setup.yml"):
        text = (WORKFLOWS_DIR / name).read_text(encoding="utf-8")
        assert "DEPRECATED" in text
        assert "KEEP-DISABLED (#10263)" in text
