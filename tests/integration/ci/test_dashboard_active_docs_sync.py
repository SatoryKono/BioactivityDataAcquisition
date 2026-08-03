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


def _dashboard_panel_by_title(
    dashboard_path: Path, panel_title: str
) -> dict[str, object]:
    payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
    panels = _iter_dashboard_panels(list(payload.get("panels", [])))
    return next(panel for panel in panels if panel.get("title") == panel_title)


def _dashboard_panel_by_id(dashboard_path: Path, panel_id: int) -> dict[str, object]:
    payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
    panels = _iter_dashboard_panels(list(payload.get("panels", [])))
    return next(panel for panel in panels if panel.get("id") == panel_id)


def _documented_panel_section(doc_text: str, panel_title: str) -> str:
    match = re.search(
        rf"^###\s+(?:\d+\.\s+)?{re.escape(panel_title)}[ \t]*\r?\n"
        r"(?P<body>.*?)(?=^#{1,3}[ \t]+|\Z)",
        doc_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"Missing panel documentation section: {panel_title}"
    return match.group(0)


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
    # bioetl-workflow-overview.json was retired (#6570/#6647); workflow-band
    # evidence now ships on bioetl-runtime (see panel-title-inventory).
    assert "bioetl-workflow-overview.json" not in panel_inventory
    assert "| bioetl-runtime.json |" in panel_inventory
    assert "Track Failed Workflow Runs" in panel_inventory

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
        "Metrics Evidence",
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


@pytest.mark.parametrize(
    (
        "dashboard_name",
        "identity_title",
        "processed_title",
        "identity_panel_id",
        "processed_panel_id",
    ),
    (
        (
            "bioetl-dq-v2",
            "Inspect Run Identity",
            "Inspect Processed Records",
            9402,
            9403,
        ),
        (
            "bioetl-overview-v2",
            "Review Run Identity",
            "Review Processed Records",
            9300,
            9301,
        ),
        (
            "bioetl-provider-health-v2",
            "Inspect Run Identity",
            "Inspect Processed Records",
            9402,
            9403,
        ),
        (
            "bioetl-runtime",
            "Inspect Pipeline Identity",
            "Inspect Processed Records",
            9402,
            9403,
        ),
    ),
)
def test_http_identity_panel_docs_match_shipped_datasource_contract(
    dashboard_name: str,
    identity_title: str,
    processed_title: str,
    identity_panel_id: int,
    processed_panel_id: int,
) -> None:
    """HTTP-backed identity panels must not drift back to Prometheus docs."""
    dashboard_path = DASHBOARD_DIR / f"{dashboard_name}.json"
    doc_text = (PANEL_DOCS_DIR / f"{dashboard_name}-panels.md").read_text(
        encoding="utf-8"
    )
    identity_section = _documented_panel_section(doc_text, identity_title)
    processed_section = _documented_panel_section(doc_text, processed_title)

    identity_panel = _dashboard_panel_by_id(dashboard_path, identity_panel_id)
    processed_panel = _dashboard_panel_by_id(dashboard_path, processed_panel_id)
    identity_target = identity_panel["targets"][0]
    processed_target = processed_panel["targets"][0]

    for panel in (identity_panel, processed_panel):
        assert panel["datasource"] == "BioETL Ops HTTP"
    assert str(identity_target["url"]).startswith("/ops/control-plane/identity-table")
    assert str(processed_target["url"]).startswith(
        "/ops/observability/processed-records"
    )

    for token in (
        "BioETL Ops HTTP control-plane identity endpoint",
        "/ops/control-plane/identity-table",
        "this is not a Prometheus panel",
    ):
        assert token in identity_section
    for token in (
        "BioETL Ops HTTP",
        "/ops/observability/processed-records",
        "this is not a Prometheus panel",
    ):
        assert token in processed_section
