"""Architecture guardrails for Gold reject taxonomy ownership."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SILVER_SURFACES = (
    ROOT / "src/bioetl/application/services/dq/silver_analyzer.py",
    ROOT / "src/bioetl/application/services/dq/silver_check_executor.py",
    ROOT / "src/bioetl/application/services/dq/silver_statistics.py",
    ROOT / "src/bioetl/application/services/dq/silver_statistics_helpers.py",
    ROOT / "src/bioetl/infrastructure/storage/silver",
    ROOT / "src/bioetl/infrastructure/storage/silver_writer.py",
)
FORBIDDEN_SILVER_MARKERS = (
    "gold_candidate_",
    "analysis_readiness",
    "analysis-readiness",
)
DQ_DASHBOARD = ROOT / "grafana" / "dashboards" / "bioetl-dq-v2.json"


def _iter_dashboard_panels(dashboard: dict) -> list[dict]:
    """Flatten root and row-nested Grafana panels."""
    flattened: list[dict] = []
    for panel in dashboard.get("panels", []):
        if not isinstance(panel, dict):
            continue
        flattened.append(panel)
        nested = panel.get("panels", [])
        if isinstance(nested, list):
            flattened.extend(
                nested_panel
                for nested_panel in nested
                if isinstance(nested_panel, dict)
            )
    return flattened


def _iter_python_files(path: Path) -> tuple[Path, ...]:
    if path.is_file():
        return (path,)
    return tuple(sorted(path.rglob("*.py")))


def test_silver_surfaces_do_not_emit_gold_candidate_or_readiness_flags() -> None:
    offenders: list[str] = []
    for surface in SILVER_SURFACES:
        for path in _iter_python_files(surface):
            text = path.read_text(encoding="utf-8")
            for marker in FORBIDDEN_SILVER_MARKERS:
                if marker in text:
                    offenders.append(f"{path.relative_to(ROOT)}:{marker}")

    assert offenders == []


def test_dq_dashboard_gold_reject_panel_is_not_silver_alias_surface() -> None:
    dashboard = json.loads(DQ_DASHBOARD.read_text(encoding="utf-8"))
    panel = next(
        (
            item
            for item in _iter_dashboard_panels(dashboard)
            if item.get("title") == "Inspect: Gold Reject Outcomes by Pipeline"
        ),
        None,
    )

    assert panel is not None
    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    joined = "\n".join(expressions)
    assert "bioetl_processed_records_gold_quarantined_current" in joined
    assert "bioetl_processed_records_gold_excluded_by_contract_current" in joined
    assert "bioetl_silver_filter_rejections_total" not in joined
    assert 'stage="filtered_out"' not in joined

    links = [
        *panel.get("links", []),
        *panel.get("options", {}).get("dataLinks", []),
    ]
    assert all(
        for link in links
    )
