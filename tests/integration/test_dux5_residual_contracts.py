"""DUX5 residual contracts (copy safety, nav integrity, governance docs)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
DASH = ROOT / "grafana" / "dashboards"
DOCS = ROOT / "docs" / "03-guides" / "dashboards"
AUDIT_PROTOCOLS = DOCS / "archive" / "audit-protocols"

pytestmark = pytest.mark.integration


def _walk(panels: list[dict[str, Any]] | None):
    for panel in panels or []:
        yield panel
        yield from _walk(panel.get("panels"))


def _dashboards() -> list[Path]:
    return sorted(DASH.glob("*.json"))


def test_dux5_governance_docs_exist() -> None:
    assert (AUDIT_PROTOCOLS / "dux5-copy-dictionary.md").is_file()
    assert (AUDIT_PROTOCOLS / "dux5-screenshot-regression-protocol.md").is_file()
    design = (DOCS / "design-system.md").read_text(encoding="utf-8")
    assert "dux5-copy-dictionary.md" in design
    assert "archive/audit-protocols/dux5-copy-dictionary.md" in design


def test_nav_bus_complete_without_truncation() -> None:
    for path in _dashboards():
        data = json.loads(path.read_text(encoding="utf-8"))
        nav = next((p for p in data.get("panels") or [] if p.get("id") == 1000), None)
        assert nav is not None, f"{path.name} missing Navigation id=1000"
        content = (nav.get("options") or {}).get("content") or ""
        assert "DUX4-22: truncated" not in content
        assert "bioetl-nav" in content
        for chip in (
            "0. Trust",
            "1. Overview",
            "2. Pipeline Diagnostics",
            "3. Provider Health",
            "4. Data Quality",
            "5. Incident Workspace",
            "6. Run Explorer",
        ):
            assert chip in content, f"{path.name} missing chip {chip}"
        assert "aria-current" in content


def test_no_raw_endpoints_or_valid_empty_tokens_in_text_bodies() -> None:
    endpoint_re = re.compile(r"GET\s+/ops/", re.I)
    for path in _dashboards():
        data = json.loads(path.read_text(encoding="utf-8"))
        for panel in _walk(data.get("panels")):
            if panel.get("type") != "text" or panel.get("id") == 1000:
                continue
            content = (panel.get("options") or {}).get("content") or ""
            if not isinstance(content, str):
                continue
            assert not endpoint_re.search(content), (
                f"{path.name} panel {panel.get('id')} exposes raw endpoint syntax"
            )
            assert "VALID_EMPTY" not in content, (
                f"{path.name} panel {panel.get('id')} still exposes VALID_EMPTY token"
            )
            assert "### " not in content and not content.lstrip().startswith("###"), (
                f"{path.name} panel {panel.get('id')} still has literal ### markdown chrome"
            )


def test_value_columns_have_operator_display_names_on_suspect_tables() -> None:
    incident = json.loads(
        (DASH / "bioetl-incident-v1.json").read_text(encoding="utf-8")
    )
    suspects = next(
        p
        for p in _walk(incident.get("panels"))
        if p.get("title") == "Inspect Ranked Suspects"
    )
    overrides = (suspects.get("fieldConfig") or {}).get("overrides") or []
    display_names = [
        prop.get("value")
        for ov in overrides
        for prop in (ov.get("properties") or [])
        if prop.get("id") == "displayName"
    ]
    assert display_names, "Inspect Ranked Suspects must label Value columns"
    assert any(
        "Signal" in str(v) or "Count" in str(v) or "Severity" in str(v)
        for v in display_names
    )


def test_percent_scores_use_integer_precision() -> None:
    dq = json.loads((DASH / "bioetl-dq-v2.json").read_text(encoding="utf-8"))
    for panel in _walk(dq.get("panels")):
        title = panel.get("title") or ""
        if "Data Quality Score" not in title and "Worst-Entity DQ Score" not in title:
            continue
        defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
        if defaults.get("unit") in {"percent", "percentunit"}:
            assert int(defaults.get("decimals") or 0) == 0, title


def test_dux5_run_context_collapsed_outside_explorer() -> None:
    expected_by_uid = {
        "bioetl-runtime": True,
        "bioetl-overview-v2": True,
    }
    for path in _dashboards():
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = expected_by_uid.get(data.get("uid"))
        if expected is None:
            continue
        for panel in _walk(data.get("panels")):
            if panel.get("type") != "row":
                continue
            title = (panel.get("title") or "").lower()
            if "run context" in title:
                assert panel.get("collapsed") is expected, (
                    f"{path.name} Run context row violates its disclosure policy"
                )


def test_status_card_provenance_is_compact_html() -> None:
    for path in _dashboards():
        data = json.loads(path.read_text(encoding="utf-8"))
        for panel in _walk(data.get("panels")):
            if panel.get("title") != "Provenance" and panel.get("id") != 9400:
                continue
            if panel.get("title") != "Provenance":
                continue
            opts = panel.get("options") or {}
            content = opts.get("content") or ""
            assert opts.get("mode") == "html"
            assert (
                "Status" in content
                or "status" in content.lower()
                or "trust" in content.lower()
            )
            assert len(content) < 1200
            assert "GET /ops" not in content
