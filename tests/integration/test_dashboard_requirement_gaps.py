# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
"""Fail-closed pytest for incomplete DASH-* rules (#9204 / #9203)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.integration._dashboard_layout_budgets import (
    FIRST_WINDOW_Y,
    SYNTHETIC_ZERO_ALLOWLIST,
    answer_panels,
    trust_gate_keys,
)
from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration

_SEVEN_UIDS = frozenset({
    "bioetl-control-plane-v1",
    "bioetl-overview-v2",
    "bioetl-runtime",
    "bioetl-provider-health-v2",
    "bioetl-dq-v2",
    "bioetl-incident-v1",
    "bioetl-run-explorer-v1",
})
_COVERAGE_PATH = Path("docs/03-guides/dashboards/contracts/requirement-test-coverage.yaml")
_REQUIREMENTS_PATH = Path("docs/01-requirements/DASHBOARD_REQUIREMENTS.md")
_DASH_ID_RE = re.compile(r"`(DASH-[A-Z]+-[0-9]{3})`")
_EMPTY_TOKENS = (
    "valid empty",
    "select run",
    "unknown",
    "query error",
    "unavailable",
    "incomplete",
)
_WRITE_URL_RE = re.compile(
    r"/api/admin(?:/|)|[?&]method=POST|[?&]method=PUT|[?&]method=PATCH",
    re.I,
)
_FIRST_WINDOW_INSPECT_ALLOWLIST = frozenset({
    ("bioetl-incident-v1.json", 2010),
    ("bioetl-provider-health-v2.json", 9107),
    ("bioetl-run-explorer-v1.json", 3010),
})
_CTA_ALLOWLIST = frozenset({("bioetl-overview-v2.json", 215), ("bioetl-incident-v1.json", 2010)})


def _first_window_root(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for panel in dashboard.get("panels") or []:
        if not isinstance(panel, dict):
            continue
        y = (panel.get("gridPos") or {}).get("y")
        if isinstance(y, int) and y < FIRST_WINDOW_Y:
            out.append(panel)
    return out


def _exprs(panel: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for target in panel.get("targets") or []:
        if not isinstance(target, dict) or target.get("hide") is True:
            continue
        expr = target.get("expr")
        if isinstance(expr, str) and expr.strip():
            out.append(expr)
    return out


def _http_targets(panel: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for target in panel.get("targets") or []:
        if not isinstance(target, dict) or target.get("hide") is True:
            continue
        url = target.get("url")
        if isinstance(url, str) and url.strip():
            out.append(target)
    return out


def _panel_links(panel: dict[str, Any]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    raw = panel.get("links")
    if isinstance(raw, list):
        links.extend(item for item in raw if isinstance(item, dict))
    defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
    if isinstance(defaults, dict):
        field_links = defaults.get("links")
        if isinstance(field_links, list):
            links.extend(item for item in field_links if isinstance(item, dict))
    return links


def _synthetic_zero_hits(dashboard_name: str, panel: dict[str, Any]) -> list[str]:
    if panel.get("type") != "stat":
        return []
    if (panel.get("options") or {}).get("colorMode") != "background":
        return []
    if (dashboard_name, panel.get("id")) in SYNTHETIC_ZERO_ALLOWLIST:
        return []
    hits: list[str] = []
    for expr in _exprs(panel):
        if "or vector(0)" in expr or "* 0" in expr:
            hits.append(f"{dashboard_name}:{panel.get('id')} {expr[:80]}")
    return hits


def test_requirement_coverage_matrix_lists_every_dash_id() -> None:
    req_ids = set(_DASH_ID_RE.findall(_REQUIREMENTS_PATH.read_text(encoding="utf-8")))
    payload = yaml.safe_load(_COVERAGE_PATH.read_text(encoding="utf-8"))
    rows = payload["requirements"]
    covered = {str(row["id"]) for row in rows}
    missing = sorted(req_ids - covered)
    extra = sorted(covered - req_ids)
    assert not missing, f"coverage matrix missing {missing}"
    assert not extra, f"coverage matrix extra {extra}"
    for row in rows:
        gate = str(row.get("gate") or "")
        tests = row.get("tests") or []
        prompt = row.get("prompt")
        if "manual" in gate:
            assert isinstance(prompt, str) and prompt.startswith("prompt.")
        else:
            assert tests, f"{row['id']} needs tests"


def test_default_compose_does_not_require_grafana() -> None:
    text = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "name: bioetl-main" in text
    assert "image: grafana" not in text.lower()
    assert "grafana/grafana" not in text.lower()
    monitoring = Path("docker-compose.monitoring.yml")
    assert monitoring.is_file()
    mon = monitoring.read_text(encoding="utf-8").lower()
    assert "grafana" in mon


def test_dashboard_links_are_read_only() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        if _WRITE_URL_RE.search(json.dumps(load_dashboard(path))):
            offenders.append(path.name)
    assert not offenders, f"write/admin Grafana API URLs: {offenders}"


def test_ops_http_allowlist_covers_all_seven_uids() -> None:
    names = {path.stem for path in get_dashboard_files()}
    assert names == _SEVEN_UIDS
    seen: set[str] = set()
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in get_dashboard_panels(dashboard):
            if _http_targets(panel):
                seen.add(path.stem)
    assert seen == _SEVEN_UIDS, f"Ops HTTP missing on {sorted(_SEVEN_UIDS - seen)}"


def test_first_window_verdict_stats_reject_synthetic_zero() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in _first_window_root(dashboard):
            offenders.extend(_synthetic_zero_hits(path.name, panel))
    assert not offenders, "synthetic zero on first-window verdict stats:\n" + "\n".join(
        offenders
    )


def test_synthetic_zero_fails_closed_on_mutated_fixture() -> None:
    path = next(p for p in get_dashboard_files() if p.name == "bioetl-runtime.json")
    dashboard = copy.deepcopy(load_dashboard(path))
    panel = next(item for item in dashboard["panels"] if item.get("id") == 9401)
    panel["targets"][0]["expr"] = "max(bioetl_runtime_current_status_trusted) or vector(0)"
    assert _synthetic_zero_hits(path.name, panel)


def test_synthetic_zero_allowlist_is_governed() -> None:
    key = ("bioetl-provider-health-v2.json", 9104)
    assert key in SYNTHETIC_ZERO_ALLOWLIST
    meta = SYNTHETIC_ZERO_ALLOWLIST[key]
    assert meta["owner"].startswith("@")
    assert meta["rationale"].strip()
    assert meta["retire_when"].strip()


def test_trust_gate_keeps_processing_and_trust_distinct() -> None:
    gates = trust_gate_keys()
    assert gates
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in dashboard.get("panels") or []:
            if (path.name, panel.get("id")) not in gates:
                continue
            desc = str(panel.get("description") or "").lower()
            blob = desc + " " + " ".join(_exprs(panel)).lower()
            assert "incomplete" in desc or "unknown" in desc
            assert "replay" in desc or "pipeline health" in desc or "trust" in desc
            if "processing_status" in blob:
                assert "trust_status" in desc


def test_answer_panels_carry_basis_copy() -> None:
    mapping = answer_panels()
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        by_id = {panel.get("id"): panel for panel in dashboard.get("panels") or []}
        for spec in mapping[path.name]:
            panel = by_id[spec["id"]]
            y = int((panel.get("gridPos") or {}).get("y") or 999)
            assert y < FIRST_WINDOW_Y
            assert str(panel.get("description") or "").strip()


def test_first_window_forensic_tables_are_allowlisted() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in _first_window_root(dashboard):
            if panel.get("type") != "table":
                continue
            title = str(panel.get("title") or "")
            if not title.startswith("Inspect "):
                continue
            if (path.name, panel.get("id")) not in _FIRST_WINDOW_INSPECT_ALLOWLIST:
                offenders.append(f"{path.name}:{panel.get('id')} {title}")
    assert not offenders, "unallowlisted first-window Inspect tables:\n" + "\n".join(
        offenders
    )


def test_first_window_rows_ship_collapsed() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in _first_window_root(dashboard):
            if panel.get("type") != "row":
                continue
            if panel.get("collapsed") is not True:
                offenders.append(f"{path.name}:{panel.get('id')}")
    assert not offenders, "first-window rows must ship collapsed:\n" + "\n".join(
        offenders
    )


def test_answer_panels_do_not_split_primary_cta() -> None:
    mapping = answer_panels()
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        by_id = {panel.get("id"): panel for panel in dashboard.get("panels") or []}
        for spec in mapping[path.name]:
            if (path.name, spec["id"]) in _CTA_ALLOWLIST:
                continue
            panel = by_id[spec["id"]]
            uids: set[str] = set()
            for link in _panel_links(panel):
                url = str(link.get("url") or "")
                if not url.startswith("/d/"):
                    continue
                parts = url.split("/")
                if len(parts) >= 3:
                    uids.add(parts[2].split("?")[0])
            if len(uids) > 1:
                offenders.append(f"{path.name}:{spec['id']} {sorted(uids)}")
    assert not offenders, "split primary CTA:\n" + "\n".join(offenders)


def test_http_tables_name_empty_versus_backend_failure() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "table" or not _http_targets(panel):
                continue
            blob = (
                str(panel.get("description") or "")
                + " "
                + str(
                    ((panel.get("fieldConfig") or {}).get("defaults") or {}).get(
                        "noValue"
                    )
                    or ""
                )
            ).lower()
            if not any(token in blob for token in _EMPTY_TOKENS):
                offenders.append(f"{path.name}:{panel.get('id')}")
    assert not offenders, "HTTP tables missing empty/error copy:\n" + "\n".join(
        offenders
    )


def test_ops_http_row_tables_use_backend_parser() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in get_dashboard_panels(dashboard):
            for target in _http_targets(panel):
                if str(target.get("root_selector") or "") != "rows":
                    continue
                if target.get("parser") != "backend":
                    offenders.append(f"{path.name}:{panel.get('id')}")
    assert not offenders, "rows tables must use parser=backend:\n" + "\n".join(
        offenders
    )


def test_http_parser_fails_closed_on_mutated_fixture() -> None:
    path = next(p for p in get_dashboard_files() if p.name == "bioetl-run-explorer-v1.json")
    dashboard = copy.deepcopy(load_dashboard(path))
    panel = next(
        item for item in get_dashboard_panels(dashboard) if item.get("id") == 3022
    )
    _http_targets(panel)[0]["parser"] = "simple"
    offenders = [
        panel.get("id")
        for target in _http_targets(panel)
        if target.get("root_selector") == "rows" and target.get("parser") != "backend"
    ]
    assert offenders
