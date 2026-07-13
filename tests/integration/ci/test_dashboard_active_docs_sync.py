"""CI guard: active dashboard docs must stay aligned with shipped JSON contracts."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

import pytest

pytestmark = pytest.mark.integration

DASHBOARD_DIR = Path("grafana/dashboards")
PANEL_DOCS_DIR = Path("docs/03-guides/dashboards/panels")


def _iter_dashboard_panels(panels: list[object]) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        collected.append(panel)
        nested = panel.get("panels")
        if isinstance(nested, list):
            collected.extend(_iter_dashboard_panels(nested))
    return collected


def _dashboard_panel_titles(dashboard_path: Path) -> Counter[str]:
    payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
    panels = _iter_dashboard_panels(list(payload.get("panels", [])))
    return Counter(
        str(panel["title"]).strip()
        for panel in panels
        if isinstance(panel.get("title"), str) and str(panel["title"]).strip()
    )


def _documented_panel_titles(doc_path: Path) -> Counter[str]:
    text = doc_path.read_text(encoding="utf-8")
    titles = re.findall(r"^###\s+\d+\.\s+(.+?)\s*$", text, flags=re.MULTILINE)

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in {"ID", "---"}:
            continue
        if re.fullmatch(r"\d+", cells[0]):
            titles.append(cells[1])

    return Counter(title for title in titles if title)


def test_active_docs_capture_uniform_responsive_navigation_bus() -> None:
    readme = Path("docs/03-guides/dashboards/README.md").read_text(encoding="utf-8")
    usage = Path("docs/03-guides/dashboards/dashboard-v2-usage.md").read_text(
        encoding="utf-8"
    )

    for token in (
        "bioetl-control-plane-v1",
        "6. Alerts & SLO",
        "Explore Logs",
        "Explore Traces",
        "1024",
    ):
        assert token in readme
        assert token in usage
    assert "намеренным исключением" not in readme
    assert "intentional exception" not in usage


def test_active_docs_sync_workflow_selector_and_cta_titles() -> None:
    variable_reference = Path(
        "docs/03-guides/dashboards/variable-reference.md"
    ).read_text(encoding="utf-8")
    panel_inventory = Path(
        "docs/03-guides/dashboards/panel-title-inventory.md"
    ).read_text(encoding="utf-8")
    changelog = Path("docs/03-guides/dashboards/dashboard-v2-updates.md").read_text(
        encoding="utf-8"
    )

    assert "Single-select with Include All" in variable_reference
    assert "single-select with Include All across primary dashboards" in (
        variable_reference
    )
    assert "| bioetl-workflow-overview.json | 9 | First Action |" in panel_inventory
    assert "| bioetl-workflow-overview.json | 2 | Failed Workflow Runs / Range |" in (
        panel_inventory
    )

    for token in ("Next Diagnostic Surface", "Workflow Scope"):
        assert token not in panel_inventory
    assert "Переменные overview: `$pipeline`, `$run_type`." not in changelog


def test_active_dashboard_changelog_stays_current_to_shipped_surface() -> None:
    changelog = Path("docs/03-guides/dashboards/dashboard-v2-updates.md").read_text(
        encoding="utf-8"
    )

    required_tokens = (
        "Shipped Surface 2026-05-19",
        "docs/reports/dashboard-ux-checks/2026-05-19.md",
        "shared context shell",
        "$workflow",
        "$pipeline",
        "$run_type",
        "$run_id",
        "bioetl-control-plane-v1",
        "bioetl-workflow-overview",
        "Runtime Telemetry Gap",
        "First Action",
    )
    for token in required_tokens:
        assert token in changelog


def test_panel_docs_match_shipped_dashboard_panel_titles() -> None:
    """Panel prose docs must stay 1:1 with shipped dashboard JSON titles."""
    offenders: list[str] = []

    for dashboard_path in sorted(DASHBOARD_DIR.glob("*.json")):
        doc_path = PANEL_DOCS_DIR / f"{dashboard_path.stem}-panels.md"
        if not doc_path.exists():
            offenders.append(f"{dashboard_path.name}: missing {doc_path.as_posix()}")
            continue

        live_titles = _dashboard_panel_titles(dashboard_path)
        documented_titles = _documented_panel_titles(doc_path)
        missing = sorted((live_titles - documented_titles).elements())
        obsolete = sorted((documented_titles - live_titles).elements())

        if missing or obsolete:
            offenders.append(
                f"{dashboard_path.name}: "
                f"missing_in_docs={missing or []}; obsolete_in_docs={obsolete or []}"
            )

    assert not offenders, "\n".join(offenders)
