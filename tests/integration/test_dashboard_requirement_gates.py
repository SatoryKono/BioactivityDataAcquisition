# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Fail-closed DASHBOARD_REQUIREMENTS gates (#9212–#9218)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
import yaml

from tests.integration._grafana_test_support import (
    get_all_valid_metric_names,
    get_dashboard_files,
    get_dashboard_panels,
    get_dashboard_prometheus_queries,
    load_dashboard,
)

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
GATES_PATH = (
    ROOT / "docs" / "03-guides" / "dashboards" / "contracts" / "requirement-gates.yaml"
)
LAYOUT_PATH = (
    ROOT / "docs" / "03-guides" / "dashboards" / "contracts" / "layout-budgets.yaml"
)
MAIN_COMPOSE = ROOT / "docker-compose.yml"
MONITORING_COMPOSE = ROOT / "docker-compose.monitoring.yml"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
TRUST_SPLIT_FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "grafana"
    / "trust_status"
    / "processing_success_incomplete.json"
)
_BIOETL_METRIC_RE = re.compile(r"\b(bioetl_[a-z0-9_]+)\b")
_WRITE_URL_RE = re.compile(
    r"(?i)(/api/admin(?:/|$)|/api/dashboards/db(?:/|$)|/api/annotations(?:/|$)"
    r"|/apis/.*/write|/write\?)"
)
_DASHBOARD_UID_RE = re.compile(r"/d/([^/?]+)")
_HTTP_DATASOURCE_TYPES = {
    "yesoreyeram-infinity-datasource",
    "grafana-infinity-datasource",
    "marcusolsson-json-datasource",
}


def _gates() -> dict[str, Any]:
    payload = yaml.safe_load(GATES_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _first_window_y() -> int:
    payload = yaml.safe_load(LAYOUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    value = payload["first_window_y"]
    assert isinstance(value, int)
    return value


def _shipped_by_uid() -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        uid = dashboard.get("uid")
        assert isinstance(uid, str) and uid, f"{path.name}: missing uid"
        mapping[uid] = path
    return mapping


def _datasource_type(obj: object) -> str:
    if isinstance(obj, dict):
        return str(obj.get("type") or "")
    return ""


def _datasource_uid(obj: object) -> str:
    if isinstance(obj, dict):
        return str(obj.get("uid") or "")
    if isinstance(obj, str):
        return obj
    return ""


def _is_ops_http(*, typ: str, uid: str) -> bool:
    if typ in _HTTP_DATASOURCE_TYPES:
        return True
    blob = f"{typ} {uid}".lower()
    return "ops-http" in blob or "bioetl-ops" in blob or "ops http" in blob


def _target_url(target: dict[str, object]) -> str | None:
    for key in ("url", "urlPath"):
        value = target.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    options = target.get("url_options")
    if isinstance(options, dict):
        value = options.get("url")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _panel_links(panel: dict[str, object]) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    options = panel.get("options")
    if isinstance(options, dict):
        links = options.get("dataLinks")
        if isinstance(links, list):
            found.extend(link for link in links if isinstance(link, dict))
    defaults = (panel.get("fieldConfig") or {}).get("defaults")
    if isinstance(defaults, dict):
        links = defaults.get("links")
        if isinstance(links, list):
            found.extend(link for link in links if isinstance(link, dict))
    links = panel.get("links")
    if isinstance(links, list):
        found.extend(link for link in links if isinstance(link, dict))
    return found


def _panel_copy(panel: dict[str, object]) -> str:
    options = panel.get("options")
    content = ""
    display_title = ""
    if isinstance(options, dict):
        content = str(options.get("content") or "")
        display_title = str(options.get("bioetlDisplayTitle") or "")
    no_value = str(
        ((panel.get("fieldConfig") or {}).get("defaults") or {}).get("noValue") or ""
    )
    titles = " ".join(str(link.get("title") or "") for link in _panel_links(panel))
    return " ".join(
        (
            str(panel.get("title") or ""),
            display_title,
            str(panel.get("description") or ""),
            content,
            no_value,
            titles,
        )
    )


def _allowlist_ids(entries: list[object], dashboard_name: str) -> set[int]:
    ids: set[int] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("dashboard") != dashboard_name:
            continue
        panel_id = entry.get("id")
        if isinstance(panel_id, int):
            ids.add(panel_id)
        owner = entry.get("owner")
        rationale = entry.get("rationale")
        retire_when = entry.get("retire_when")
        assert isinstance(owner, str) and owner, (
            f"{dashboard_name}:{panel_id} missing owner"
        )
        assert isinstance(rationale, str) and rationale.strip(), (
            f"{dashboard_name}:{panel_id} missing rationale"
        )
        assert isinstance(retire_when, str) and retire_when.strip(), (
            f"{dashboard_name}:{panel_id} missing retire_when"
        )
    return ids


def test_seven_shipped_uids_match_requirement_gates() -> None:
    """#9218: gates YAML and shipped JSON must name the same seven UIDs."""
    expected = _gates()["shipped_uids"]
    assert isinstance(expected, list)
    shipped = _shipped_by_uid()
    assert set(expected) == set(shipped)
    assert len(shipped) == 7


def test_grafana_is_optional_readonly_presentation_adapter() -> None:
    """#9216 DASH-ARCH-001: Grafana is not the default runtime and cannot write."""
    main = yaml.safe_load(MAIN_COMPOSE.read_text(encoding="utf-8"))
    assert isinstance(main, dict)
    services = main.get("services")
    assert isinstance(services, dict)
    assert set(services) == {"bioetl"}
    assert "grafana" not in services
    monitoring = yaml.safe_load(MONITORING_COMPOSE.read_text(encoding="utf-8"))
    assert isinstance(monitoring, dict)
    monitoring_services = monitoring.get("services")
    assert isinstance(monitoring_services, dict)
    assert "grafana" in monitoring_services

    for workflow in WORKFLOWS_DIR.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        if "docker-compose.monitoring.yml" not in text:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if "docker-compose.monitoring.yml" not in stripped:
                continue
            if "docker compose" not in stripped and not stripped.startswith("run:"):
                continue
            assert " up " not in f" {stripped} ", (
                f"{workflow.name} must not start the optional monitoring stack: {stripped}"
            )

    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in get_dashboard_panels(dashboard):
            for target in panel.get("targets") or []:
                if not isinstance(target, dict):
                    continue
                options = target.get("url_options")
                method = ""
                if isinstance(options, dict):
                    method = str(options.get("method") or "")
                if method and method.upper() not in {"", "GET"}:
                    offenders.append(
                        f"{path.name}:id={panel.get('id')} method={method}"
                    )
                url = _target_url(target) or ""
                if _WRITE_URL_RE.search(url):
                    offenders.append(f"{path.name}:id={panel.get('id')} url={url}")
            for link in _panel_links(panel):
                url = str(link.get("url") or "")
                if _WRITE_URL_RE.search(url):
                    offenders.append(f"{path.name}:id={panel.get('id')} link={url}")
    assert not offenders, "shipped dashboards must stay read-only:\n" + "\n".join(
        offenders
    )


def test_ops_http_and_recording_rules_cover_all_seven_uids() -> None:
    """#9218 DASH-DATA-001: Ops HTTP allowlist + no invented bioetl_* series."""
    gates = _gates()
    prefixes = tuple(str(item) for item in gates["ops_http_path_prefixes"])
    valid = get_all_valid_metric_names()
    http_offenders: list[str] = []
    metric_offenders: list[str] = []
    scanned_http = 0
    scanned_promql = 0
    uids_with_http: set[str] = set()
    uids_with_promql: set[str] = set()

    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        uid = str(dashboard.get("uid"))
        for panel in get_dashboard_panels(dashboard):
            panel_type = _datasource_type(panel.get("datasource"))
            panel_uid = _datasource_uid(panel.get("datasource"))
            for target in panel.get("targets") or []:
                if not isinstance(target, dict):
                    continue
                typ = _datasource_type(target.get("datasource")) or panel_type
                ds_uid = _datasource_uid(target.get("datasource")) or panel_uid
                if _is_ops_http(typ=typ, uid=ds_uid):
                    url = _target_url(target)
                    scanned_http += 1
                    uids_with_http.add(uid)
                    if url is None:
                        http_offenders.append(
                            f"{path.name}:id={panel.get('id')} missing url"
                        )
                        continue
                    parsed = urlparse(url).path or url.split("?", 1)[0]
                    if not any(parsed.startswith(prefix) for prefix in prefixes):
                        http_offenders.append(
                            f"{path.name}:id={panel.get('id')} url={url}"
                        )
        for query in get_dashboard_prometheus_queries(dashboard):
            scanned_promql += 1
            uids_with_promql.add(uid)
            for token in _BIOETL_METRIC_RE.findall(query):
                if token in valid:
                    continue
                base = re.sub(r"(_total|_bucket|_sum|_count|_created)$", "", token)
                if base not in valid:
                    metric_offenders.append(f"{path.name}:{token} query={query[:160]}")

    assert scanned_http > 0
    assert scanned_promql > 0
    assert not http_offenders, "Ops HTTP URLs off allowlist:\n" + "\n".join(
        http_offenders
    )
    assert not metric_offenders, "invented bioetl_* series:\n" + "\n".join(
        metric_offenders
    )
    assert len(uids_with_http) >= 5
    assert "bioetl-run-explorer-v1" in uids_with_http


def test_infinity_rows_tables_use_parser_backend() -> None:
    """#9212: Ops HTTP root_selector rows/$.rows must use parser=backend."""
    offenders: list[str] = []
    scanned = 0
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in get_dashboard_panels(dashboard):
            for target in panel.get("targets") or []:
                if not isinstance(target, dict):
                    continue
                selector = str(target.get("root_selector") or "")
                if selector not in {"rows", "$.rows"} and not selector.endswith(
                    ".rows"
                ):
                    continue
                scanned += 1
                parser = str(target.get("parser") or "")
                if parser != "backend":
                    offenders.append(
                        f"{path.name}:id={panel.get('id')} parser={parser!r} "
                        f"root_selector={selector!r}"
                    )
    assert scanned > 0
    assert not offenders, "rows tables must use parser=backend:\n" + "\n".join(
        offenders
    )


def test_synthetic_zero_is_allowlisted_and_absent_from_verdicts() -> None:
    """#9215 DASH-STATE-001 / DASH-ZERO-001."""
    gates = _gates()
    first_window_y = _first_window_y()
    allowlist = gates["synthetic_zero_allowlist"]
    assert isinstance(allowlist, list)
    offenders: list[str] = []
    for path in get_dashboard_files():
        allowed = _allowlist_ids(allowlist, path.name)
        dashboard = load_dashboard(path)
        root_ids = {
            panel.get("id")
            for panel in dashboard.get("panels") or []
            if isinstance(panel, dict)
        }
        for panel in get_dashboard_panels(dashboard):
            panel_id = panel.get("id")
            y = (panel.get("gridPos") or {}).get("y")
            title = str(panel.get("title") or "")
            for target in panel.get("targets") or []:
                if not isinstance(target, dict):
                    continue
                expr = str(target.get("expr") or "")
                if "vector(0)" not in expr and "* 0 + 0" not in expr:
                    continue
                if panel_id in allowed:
                    continue
                compact = f"{title} {panel.get('description') or ''}".lower()
                is_verdict = panel.get("type") == "stat" and (
                    "status" in compact
                    or "trust" in compact
                    or "freshness" in compact
                    or "latency" in compact
                    or "cause" in compact
                )
                in_first_window = (
                    panel_id in root_ids
                    and isinstance(y, int)
                    and y < first_window_y
                    and panel.get("type") == "stat"
                )
                if is_verdict or in_first_window:
                    offenders.append(f"{path.name}:id={panel_id} title={title!r}")
                else:
                    offenders.append(
                        f"{path.name}:id={panel_id} title={title!r} "
                        "synthetic zero needs allowlist"
                    )
    assert not offenders, "synthetic zero policy:\n" + "\n".join(offenders)


def test_http_tables_distinguish_empty_from_backend_unavailable() -> None:
    """#9215 / #9213: HTTP empty-state copy vs backend unavailable."""
    first_window_y = _first_window_y()
    offenders: list[str] = []
    scanned = 0
    empty_tokens = ("valid empty", "select run", "no matching")
    unavailable_tokens = ("backend", "query error", "unavailable", "504")
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in dashboard.get("panels") or []:
            if not isinstance(panel, dict):
                continue
            y = (panel.get("gridPos") or {}).get("y")
            if not isinstance(y, int) or y >= first_window_y:
                continue
            http = False
            for target in panel.get("targets") or []:
                if isinstance(target, dict) and "/ops/" in str(target.get("url") or ""):
                    http = True
            if not http:
                continue
            scanned += 1
            copy = _panel_copy(panel).lower()
            if not any(token in copy for token in empty_tokens):
                offenders.append(
                    f"{path.name}:id={panel.get('id')} missing empty-state copy"
                )
            if not any(token in copy for token in unavailable_tokens):
                offenders.append(
                    f"{path.name}:id={panel.get('id')} missing backend-unavailable copy"
                )
    assert scanned > 0
    assert not offenders, "HTTP empty vs unavailable:\n" + "\n".join(offenders)


def test_processing_status_stays_distinct_from_trust_status() -> None:
    """#9217 DASH-STATE-004."""
    gates = _gates()
    entries = gates["trust_split_panels"]
    assert isinstance(entries, list)
    by_uid = _shipped_by_uid()
    for entry in entries:
        assert isinstance(entry, dict)
        dashboard_name = str(entry["dashboard"])
        panel_id = entry["id"]
        assert isinstance(panel_id, int)
        path = ROOT / "grafana" / "dashboards" / dashboard_name
        dashboard = load_dashboard(path)
        panel = next(
            (
                item
                for item in get_dashboard_panels(dashboard)
                if item.get("id") == panel_id
            ),
            None,
        )
        assert panel is not None, f"{dashboard_name}: missing panel {panel_id}"
        copy = _panel_copy(panel).lower()
        assert "processing_status" in copy, (
            f"{dashboard_name}:id={panel_id} must name processing_status"
        )
        assert "trust_status" in copy, (
            f"{dashboard_name}:id={panel_id} must name trust_status"
        )
        for query in get_panel_exprs(panel):
            assert "run_id" not in query

    fixture = json.loads(TRUST_SPLIT_FIXTURE.read_text(encoding="utf-8"))
    assert fixture["processing_status"] == "success"
    assert fixture["trust_status"] == "INCOMPLETE"
    assert fixture["classification"] == "INCOMPLETE"
    assert fixture["classification"] != "OK"
    assert fixture["processing_status"] != fixture["trust_status"]
    assert by_uid  # shipped dashboards still exist


def get_panel_exprs(panel: dict[str, object]) -> list[str]:
    exprs: list[str] = []
    for target in panel.get("targets") or []:
        if isinstance(target, dict) and isinstance(target.get("expr"), str):
            exprs.append(str(target["expr"]))
    return exprs


def test_operator_question_and_collapsed_forensics() -> None:
    """#9214 DASH-FIRST-001 / DASH-FIRST-002."""
    gates = _gates()
    first_window_y = _first_window_y()
    questions = gates["operator_question"]
    inspect_allowlist = gates["first_window_inspect_tables"]
    assert isinstance(questions, dict)
    assert isinstance(inspect_allowlist, list)
    assert set(questions) == {path.name for path in get_dashboard_files()}

    inspect_offenders: list[str] = []
    row_offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        allowed = _allowlist_ids(inspect_allowlist, path.name)
        spec = questions[path.name]
        assert isinstance(spec, dict)
        root_panels = [
            panel for panel in dashboard.get("panels") or [] if isinstance(panel, dict)
        ]
        root_by_id = {panel.get("id"): panel for panel in root_panels}
        for panel_id in spec["answer_ids"]:
            panel = root_by_id.get(panel_id)
            assert panel is not None, f"{path.name}: missing answer id={panel_id}"
            y = (panel.get("gridPos") or {}).get("y")
            assert isinstance(y, int) and y < first_window_y
        next_panel = root_by_id.get(spec["next_action_id"])
        assert next_panel is not None, (
            f"{path.name}: missing next_action id={spec['next_action_id']}"
        )
        answer_copy = " ".join(
            _panel_copy(root_by_id[panel_id])
            for panel_id in spec["answer_ids"]
            if panel_id in root_by_id
        )
        combined = answer_copy + " " + _panel_copy(next_panel)
        for token in spec["basis_tokens"]:
            assert str(token) in combined, f"{path.name}: missing basis token {token!r}"
        for token in spec["next_action_tokens"]:
            assert str(token) in combined, (
                f"{path.name}: missing next-action token {token!r}"
            )

        for panel in root_panels:
            y = (panel.get("gridPos") or {}).get("y")
            title = str(panel.get("title") or "")
            if (
                panel.get("type") == "table"
                and isinstance(y, int)
                and y < first_window_y
                and title.startswith("Inspect")
                and panel.get("id") not in allowed
            ):
                inspect_offenders.append(
                    f"{path.name}:id={panel.get('id')} title={title!r} y={y}"
                )
            if panel.get("type") == "row" and panel.get("collapsed") is not True:
                row_offenders.append(
                    f"{path.name}:id={panel.get('id')} title={title!r}"
                )

        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") == "row" and panel.get("collapsed") is not True:
                row_offenders.append(
                    f"{path.name}:nested id={panel.get('id')} title={panel.get('title')!r}"
                )

    assert not inspect_offenders, (
        "unallowlisted first-window Inspect tables:\n" + "\n".join(inspect_offenders)
    )
    assert not row_offenders, "uncollapsed forensic rows:\n" + "\n".join(row_offenders)


def test_unique_cta_empty_copy_and_palette_text() -> None:
    """#9213 DASH-ACTION-001 / DASH-COPY-001 / DASH-STATE-002 (static)."""
    first_window_y = _first_window_y()
    handoff_offenders: list[str] = []
    palette_offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in dashboard.get("panels") or []:
            if not isinstance(panel, dict):
                continue
            if panel.get("id") == 1000:
                continue
            y = (panel.get("gridPos") or {}).get("y")
            if not isinstance(y, int) or y >= first_window_y:
                continue
            by_title: dict[str, set[str]] = {}
            for link in _panel_links(panel):
                title = str(link.get("title") or "").strip()
                url = str(link.get("url") or "")
                match = _DASHBOARD_UID_RE.search(url)
                if not title or match is None:
                    continue
                by_title.setdefault(title, set()).add(match.group(1))
            for title, uids in by_title.items():
                if len(uids) > 1:
                    handoff_offenders.append(
                        f"{path.name}:id={panel.get('id')} title={title!r} uids={sorted(uids)}"
                    )
            if panel.get("type") != "stat":
                continue
            copy = _panel_copy(panel).lower().replace(" ", "")
            mappings = ((panel.get("fieldConfig") or {}).get("defaults") or {}).get(
                "mappings"
            )
            if not mappings:
                continue
            if "0=ok" not in copy and "ok/warn/crit" not in copy:
                # Coverage/age cards are not verdict palettes.
                title = str(panel.get("title") or "").lower()
                if any(
                    token in title
                    for token in ("status", "readiness", "severity", "health", "dq")
                ):
                    palette_offenders.append(
                        f"{path.name}:id={panel.get('id')} title={panel.get('title')!r}"
                    )
    assert not handoff_offenders, "conflicting CTA handoffs:\n" + "\n".join(
        handoff_offenders
    )
    assert not palette_offenders, "verdict cards missing palette text:\n" + "\n".join(
        palette_offenders
    )


def test_requirement_gate_helpers_fail_closed() -> None:
    assert _is_ops_http(typ="", uid="BioETL Ops HTTP")
    assert not _is_ops_http(typ="prometheus", uid="prometheus")
    assert _WRITE_URL_RE.search("/api/admin/users")
    assert _WRITE_URL_RE.search("/api/dashboards/db")
    assert not _WRITE_URL_RE.search("/ops/control-plane/identity-table")
    assert _DASHBOARD_UID_RE.search("/d/bioetl-runtime/x").group(1) == "bioetl-runtime"
