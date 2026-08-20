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
"""Loaders and fail-closed assertions for DASH-* requirement coverage (#9204)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from tests.integration._dashboard_layout_budgets import (
    FIRST_WINDOW_Y,
    answer_panels,
    is_first_window_verdict_card,
    mapping_texts,
    trust_gate_keys,
)
from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    _unknown_metrics_for_query,
    get_all_valid_metric_names,
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

CONTRACT_PATH = Path("docs/03-guides/dashboards/contracts/requirement-coverage.yaml")
SYNTHETIC_ZERO_POLICY_PATH = Path(
    "docs/03-guides/dashboards/contracts/synthetic-zero-policy.yaml"
)
REQUIREMENTS_PATH = Path("docs/01-requirements/DASHBOARD_REQUIREMENTS.md")
INVENTORY_PATH = Path("docs/03-guides/dashboards/contracts/dashboard-inventory.yaml")
MAIN_COMPOSE_PATH = Path("docker-compose.yml")
TESTS_WORKFLOW_PATH = Path(".github/workflows/tests.yml")

_REQUIRED_ALLOWLIST_KEYS = ("owner", "rationale", "retire_when")
_OPS_PATH_PREFIXES = (
    "/ops/control-plane/",
    "/ops/observability/",
    "/ops/quarantine/",
)
_HTTP_DATASOURCE_TYPES = {
    "yesoreyeram-infinity-datasource",
    "grafana-infinity-datasource",
    "marcusolsson-json-datasource",
}
_ROWS_SELECTORS = {"rows", "$.rows"}
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_FORBIDDEN_URL_RE = re.compile(
    r"/api/admin(?:/|$)|/api/org(?:/|$)|/api/user(?:/|$)|/api/playlists"
    r"|/api/dashboards/db|/api/datasources(?!/proxy/)"
)
_DASHBOARD_UID_RE = re.compile(r"^/d/([^/?]+)")
_SECTION_7_ROW_RE = re.compile(r"\| `([^`]+)` \| ([^|]+) \|")
_CONFLATION_RE = re.compile(
    r"processing_status\s*=\s*success.{0,80}"
    r"(trust_status\s*=\s*OK|replay[- ]ready|lineage closure)",
    re.IGNORECASE | re.DOTALL,
)
_STATUS_TRUST_TITLE_RE = re.compile(
    r"status|cause|freshness|latency|\btrust\b", re.IGNORECASE
)
_EMPTY_TOKENS = (
    "empty",
    "select run",
    "no selected",
    "valid empty",
    "valid_empty",
    "no matching",
)
_UNAVAILABLE_TOKENS = (
    "unavailable",
    "backend",
    "query error",
    "datasource error",
    "timeout",
    "504",
    "deadline_exceeded",
    "tree_missing",
    "layout_unhealthy",
    "identity_unhealthy",
    "bind or origin failure",
)
_PALETTE_TOKENS = ("OK", "WARN", "CRIT", "UNKNOWN")
_FORBIDDEN_MAIN_COMPOSE_SERVICES = {
    "grafana",
    "prometheus",
    "alertmanager",
    "renderer",
    "loki",
    "tempo",
    "pushgateway",
}
_MONITORING_STACK_START_RE = re.compile(
    r"docker(?:\s+|-)compose[^\n]*docker-compose\.monitoring\.yml[^\n]*\b(?:up|start)\b"
    r"|docker-compose\.monitoring\.yml[^\n]*\b(?:up|start)\b",
    re.IGNORECASE,
)


def _fail(violations: list[str], header: str) -> None:
    if violations:
        raise AssertionError(header + "\n" + "\n".join(violations))


def _require_allowlist_meta(entry: dict[str, Any], *, where: str) -> dict[str, str]:
    meta = {key: str(entry.get(key) or "") for key in _REQUIRED_ALLOWLIST_KEYS}
    missing = [key for key, value in meta.items() if not value.strip()]
    if missing:
        raise AssertionError(f"{where} missing {missing}")
    return meta


def _allowlist_index(
    entries: object, *, where: str
) -> dict[tuple[str, int], dict[str, str]]:
    if not isinstance(entries, list):
        raise AssertionError(f"{where} must be a list")
    out: dict[tuple[str, int], dict[str, str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise AssertionError(f"{where} entries must be maps")
        dashboard = entry.get("dashboard")
        panel_id = entry.get("id")
        if not isinstance(dashboard, str) or not isinstance(panel_id, int):
            raise AssertionError(f"{where} needs dashboard+int id")
        out[(dashboard, panel_id)] = _require_allowlist_meta(
            entry, where=f"{where} {dashboard}:{panel_id}"
        )
    return out


@lru_cache(maxsize=1)
def load_requirement_coverage() -> dict[str, Any]:
    payload = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{CONTRACT_PATH} must be a mapping")
    return payload


@lru_cache(maxsize=1)
def load_synthetic_zero_allowlist() -> dict[tuple[str, int], dict[str, str]]:
    payload = yaml.safe_load(SYNTHETIC_ZERO_POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{SYNTHETIC_ZERO_POLICY_PATH} must be a mapping")
    return _allowlist_index(
        payload.get("allowed_or_vector_zero"),
        where=f"{SYNTHETIC_ZERO_POLICY_PATH}:allowed_or_vector_zero",
    )


def coverage_allowlist(key: str) -> dict[tuple[str, int], dict[str, str]]:
    payload = load_requirement_coverage()
    allowlists = payload.get("allowlists")
    if not isinstance(allowlists, dict):
        raise AssertionError(f"{CONTRACT_PATH}:allowlists must be a mapping")
    return _allowlist_index(
        allowlists.get(key), where=f"{CONTRACT_PATH}:allowlists.{key}"
    )


def allowed_grafana_proxy_paths() -> frozenset[str]:
    payload = load_requirement_coverage()
    paths = payload.get("allowed_grafana_proxy_paths")
    if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
        raise AssertionError(
            f"{CONTRACT_PATH}:allowed_grafana_proxy_paths must be a list of strings"
        )
    return frozenset(paths)


def coverage_dashboards() -> dict[str, dict[str, Any]]:
    payload = load_requirement_coverage()
    dashboards = payload.get("dashboards")
    if not isinstance(dashboards, dict):
        raise AssertionError(f"{CONTRACT_PATH}:dashboards must be a mapping")
    return dashboards


def inventory_uids() -> tuple[str, ...]:
    payload = yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{INVENTORY_PATH} must be a mapping")
    rows = payload.get("dashboards")
    if not isinstance(rows, list):
        raise AssertionError(f"{INVENTORY_PATH}:dashboards must be a list")
    uids: list[str] = []
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("uid"), str):
            uids.append(row["uid"])
    return tuple(uids)


def section_7_questions() -> dict[str, str]:
    text = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    start = text.index("## 7. Per-dashboard responsibility")
    end = text.index("### 7.1")
    questions: dict[str, str] = {}
    for match in _SECTION_7_ROW_RE.finditer(text[start:end]):
        questions[match.group(1).strip()] = match.group(2).strip()
    return questions


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


def is_ops_http_source(*, typ: str, uid: str) -> bool:
    if typ in _HTTP_DATASOURCE_TYPES:
        return True
    blob = f"{typ} {uid}".lower()
    return "ops-http" in blob or "bioetl-ops" in blob or "ops http" in blob


def target_url(target: dict[str, Any]) -> str | None:
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


def target_method(target: dict[str, Any]) -> str:
    options = target.get("url_options")
    if isinstance(options, dict):
        method = options.get("method")
        if isinstance(method, str) and method.strip():
            return method.strip().upper()
    method = target.get("method")
    if isinstance(method, str) and method.strip():
        return method.strip().upper()
    return "GET"


def panel_is_ops_http(panel: dict[str, Any], target: dict[str, Any]) -> bool:
    typ = _datasource_type(target.get("datasource")) or _datasource_type(
        panel.get("datasource")
    )
    uid = _datasource_uid(target.get("datasource")) or _datasource_uid(
        panel.get("datasource")
    )
    return is_ops_http_source(typ=typ, uid=uid)


def uses_synthetic_zero(expr: str) -> bool:
    lowered = expr.lower()
    return "vector(0)" in lowered or "* 0 + 0" in lowered or "*0+0" in lowered.replace(
        " ", ""
    )


def first_window_copy(dashboard: dict[str, Any]) -> str:
    chunks: list[str] = []
    for panel in dashboard.get("panels") or []:
        if not isinstance(panel, dict) or panel.get("type") == "row":
            continue
        y = (panel.get("gridPos") or {}).get("y")
        if not isinstance(y, int) or y >= FIRST_WINDOW_Y:
            continue
        chunks.append(str(panel.get("title") or ""))
        chunks.append(str(panel.get("description") or ""))
        defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
        if isinstance(defaults, dict):
            chunks.append(str(defaults.get("noValue") or ""))
            for link in defaults.get("links") or []:
                if isinstance(link, dict):
                    chunks.append(str(link.get("title") or ""))
        options = panel.get("options") or {}
        if isinstance(options, dict):
            for link in options.get("dataLinks") or []:
                if isinstance(link, dict):
                    chunks.append(str(link.get("title") or ""))
        for link in panel.get("links") or []:
            if isinstance(link, dict):
                chunks.append(str(link.get("title") or ""))
    return "\n".join(chunks)


def panel_copy_blob(panel: dict[str, Any]) -> str:
    defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
    no_value = ""
    if isinstance(defaults, dict):
        no_value = str(defaults.get("noValue") or "")
    return f"{panel.get('description') or ''}\n{no_value}"


def extract_dashboard_uid(url: str) -> str | None:
    match = _DASHBOARD_UID_RE.match(url)
    if match is None:
        return None
    return match.group(1)


def _ops_path_allowed(url: str) -> bool:
    path = urlparse(url).path or url.split("?", 1)[0]
    return any(path.startswith(prefix) for prefix in _OPS_PATH_PREFIXES)


def assert_grafana_optional_on_default_runtime() -> None:
    payload = yaml.safe_load(MAIN_COMPOSE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{MAIN_COMPOSE_PATH} must be a mapping"
    services = payload.get("services")
    assert isinstance(services, dict), f"{MAIN_COMPOSE_PATH}:services must be a mapping"
    forbidden = sorted(
        name
        for name in services
        if str(name).lower() in _FORBIDDEN_MAIN_COMPOSE_SERVICES
    )
    _fail(
        [f"{MAIN_COMPOSE_PATH} service {name}" for name in forbidden],
        "DASH-ARCH-001: default compose must not require Grafana/monitoring services:",
    )
    compose_text = MAIN_COMPOSE_PATH.read_text(encoding="utf-8")
    assert "MONITORING=true" not in compose_text, (
        "DASH-ARCH-001: docker-compose.yml must not default MONITORING=true"
    )
    workflow = TESTS_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert _MONITORING_STACK_START_RE.search(workflow) is None, (
        "DASH-ARCH-001: default CI must not start docker-compose.monitoring.yml "
        "(syntax-only `compose config` remains allowed)"
    )


def write_url_violations(dashboard_name: str, dashboard: dict[str, Any]) -> list[str]:
    allowed_proxy = allowed_grafana_proxy_paths()
    violations: list[str] = []
    for link in _collect_dashboard_links(dashboard):
        if not isinstance(link, dict):
            continue
        url = str(link.get("url") or "")
        path = urlparse(url).path or url.split("?", 1)[0]
        if path in allowed_proxy:
            continue
        if _FORBIDDEN_URL_RE.search(url):
            violations.append(
                f"{dashboard_name}:{link.get('title')!r} write/admin url={url}"
            )
    for panel in get_dashboard_panels(dashboard):
        for target in panel.get("targets") or []:
            if not isinstance(target, dict):
                continue
            method = target_method(target)
            if method in _WRITE_METHODS:
                violations.append(
                    f"{dashboard_name}:id={panel.get('id')} HTTP {method} target"
                )
            url = target_url(target) or ""
            path = urlparse(url).path or url.split("?", 1)[0]
            if path in allowed_proxy:
                continue
            if url and _FORBIDDEN_URL_RE.search(url):
                violations.append(
                    f"{dashboard_name}:id={panel.get('id')} write/admin url={url}"
                )
    return violations


def assert_no_write_urls(dashboard_name: str, dashboard: dict[str, Any]) -> None:
    _fail(
        write_url_violations(dashboard_name, dashboard),
        "DASH-ARCH-001: shipped JSON must not expose Grafana write/admin APIs:",
    )


def assert_shipped_json_is_read_only() -> None:
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(write_url_violations(path.name, load_dashboard(path)))
    _fail(
        violations,
        "DASH-ARCH-001: shipped JSON must not expose Grafana write/admin APIs:",
    )


def ops_http_path_violations(dashboard_name: str, dashboard: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for panel in get_dashboard_panels(dashboard):
        for target in panel.get("targets") or []:
            if not isinstance(target, dict) or not panel_is_ops_http(panel, target):
                continue
            url = target_url(target)
            if url is None:
                violations.append(f"{dashboard_name}:id={panel.get('id')} missing url")
                continue
            if not _ops_path_allowed(url):
                violations.append(
                    f"{dashboard_name}:id={panel.get('id')} url={url}"
                )
    return violations


def assert_ops_http_paths_allowlisted() -> None:
    files = get_dashboard_files()
    uids = {str(load_dashboard(path).get("uid") or "") for path in files}
    expected = set(inventory_uids())
    assert uids == expected, (
        f"DASH-DATA-001: expected UIDs {sorted(expected)}, got {sorted(uids)}"
    )
    violations: list[str] = []
    for path in files:
        violations.extend(ops_http_path_violations(path.name, load_dashboard(path)))
    _fail(
        violations,
        "DASH-DATA-001: Ops HTTP targets must stay on /ops/ allowlisted paths:",
    )


def invented_metric_violations(
    dashboard_name: str, dashboard: dict[str, Any], valid: set[str]
) -> list[str]:
    violations: list[str] = []
    for panel in get_dashboard_panels(dashboard):
        for target in panel.get("targets") or []:
            if not isinstance(target, dict):
                continue
            expr = target.get("expr")
            if not isinstance(expr, str) or not expr.strip():
                continue
            for metric in _unknown_metrics_for_query(expr, valid):
                violations.append(
                    f"{dashboard_name}:id={panel.get('id')} invented series {metric}"
                )
    return violations


def assert_promql_uses_shipped_series() -> None:
    valid = get_all_valid_metric_names()
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(
            invented_metric_violations(path.name, load_dashboard(path), valid)
        )
    _fail(
        violations,
        "DASH-DATA-001: PromQL must use shipped metrics or recording rules:",
    )


def synthetic_zero_violations(
    dashboard_name: str, dashboard: dict[str, Any]
) -> list[str]:
    allowed = load_synthetic_zero_allowlist()
    violations: list[str] = []
    for panel in get_dashboard_panels(dashboard):
        exprs = [
            str(target.get("expr"))
            for target in panel.get("targets") or []
            if isinstance(target, dict) and target.get("expr")
        ]
        if not any(uses_synthetic_zero(expr) for expr in exprs):
            continue
        panel_id = panel.get("id")
        key = (dashboard_name, panel_id if isinstance(panel_id, int) else -1)
        title = str(panel.get("title") or "")
        if is_first_window_verdict_card(panel):
            violations.append(
                f"{dashboard_name}:id={panel_id} verdict card uses synthetic zero"
            )
            continue
        if _STATUS_TRUST_TITLE_RE.search(title):
            violations.append(
                f"{dashboard_name}:id={panel_id} {title!r} uses synthetic zero"
            )
            continue
        if key not in allowed:
            violations.append(
                f"{dashboard_name}:id={panel_id} {title!r} synthetic zero is not allowlisted"
            )
    return violations


def assert_synthetic_zero_policy() -> None:
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(synthetic_zero_violations(path.name, load_dashboard(path)))
    _fail(
        violations,
        "DASH-STATE-001/DASH-ZERO-001: synthetic zero is forbidden outside the allowlist:",
    )


def processing_trust_violations(
    dashboard_name: str, dashboard: dict[str, Any]
) -> list[str]:
    violations: list[str] = []
    required_split = {
        ("bioetl-control-plane-v1.json", 9401),
        ("bioetl-control-plane-v1.json", 9418),
    }
    for panel in get_dashboard_panels(dashboard):
        panel_id = panel.get("id")
        key = (dashboard_name, panel_id if isinstance(panel_id, int) else -1)
        blob = panel_copy_blob(panel)
        if _CONFLATION_RE.search(blob):
            violations.append(
                f"{dashboard_name}:id={panel_id} conflates processing success with trust OK"
            )
        if key in required_split:
            lowered = blob.lower()
            missing = [
                token
                for token in ("processing_status", "trust_status")
                if token not in lowered
            ]
            if missing:
                violations.append(
                    f"{dashboard_name}:id={panel_id} missing ontology tokens {missing}"
                )
    return violations


def assert_processing_status_distinct_from_trust() -> None:
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(processing_trust_violations(path.name, load_dashboard(path)))
    _fail(
        violations,
        "DASH-STATE-004: processing_status must stay distinct from trust_status:",
    )


def trust_display_state(payload: dict[str, Any]) -> str:
    """Map an exact-run HTTP trust payload to the operator-facing state."""
    trust = str(payload.get("trust_status") or "").strip().upper()
    if trust:
        return trust
    return "UNKNOWN"


def first_screen_decision_violations(
    dashboard_name: str, dashboard: dict[str, Any]
) -> list[str]:
    uid = str(dashboard.get("uid") or "")
    spec = coverage_dashboards().get(uid)
    if not isinstance(spec, dict):
        return [f"{dashboard_name}: missing requirement-coverage.yaml row"]
    violations: list[str] = []
    expected_ids = spec.get("answer_panel_ids")
    if not isinstance(expected_ids, list) or not expected_ids:
        return [f"{dashboard_name}: answer_panel_ids must be a non-empty list"]
    layout_ids = {
        int(entry["id"])
        for entry in answer_panels().get(dashboard_name, [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), int)
    }
    if set(expected_ids) != layout_ids:
        violations.append(
            f"{dashboard_name}: coverage answer ids {expected_ids} != layout-budgets {sorted(layout_ids)}"
        )
    root_by_id = {
        panel.get("id"): panel
        for panel in dashboard.get("panels") or []
        if isinstance(panel, dict)
    }
    for panel_id in expected_ids:
        panel = root_by_id.get(panel_id)
        if not isinstance(panel, dict):
            violations.append(f"{dashboard_name}: answer panel id={panel_id} missing")
            continue
        y = (panel.get("gridPos") or {}).get("y")
        if not isinstance(y, int) or y >= FIRST_WINDOW_Y:
            violations.append(
                f"{dashboard_name}:id={panel_id} answer panel is not in the first window"
            )
    copy_blob = first_window_copy(dashboard)
    for token in spec.get("next_action_tokens") or []:
        if str(token) not in copy_blob:
            violations.append(
                f"{dashboard_name}: first window missing next_action token {token!r}"
            )
    for token in spec.get("basis_tokens") or []:
        if str(token) not in copy_blob:
            violations.append(
                f"{dashboard_name}: first window missing basis token {token!r}"
            )
    return violations


def assert_first_screen_decision_contract() -> None:
    expected_questions = section_7_questions()
    coverage = coverage_dashboards()
    assert set(coverage) == set(expected_questions), (
        "DASH-FIRST-001: coverage UIDs must match DASHBOARD_REQUIREMENTS.md §7: "
        f"coverage={sorted(coverage)} section7={sorted(expected_questions)}"
    )
    question_drift = [
        f"{uid}: {coverage[uid].get('question')!r} != {expected_questions[uid]!r}"
        for uid in expected_questions
        if str(coverage[uid].get("question") or "") != expected_questions[uid]
    ]
    _fail(question_drift, "DASH-FIRST-001: first_screen.question must equal §7:")
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(
            first_screen_decision_violations(path.name, load_dashboard(path))
        )
    _fail(violations, "DASH-FIRST-001: first-window decision contract drift:")


def forensic_first_window_violations(
    dashboard_name: str, dashboard: dict[str, Any]
) -> list[str]:
    allowed = coverage_allowlist("first_window_inspect_tables")
    violations: list[str] = []
    for panel in dashboard.get("panels") or []:
        if not isinstance(panel, dict):
            continue
        if panel.get("type") == "row":
            collapsed = panel.get("collapsed")
            if collapsed is not True:
                violations.append(
                    f"{dashboard_name}:id={panel.get('id')} row {panel.get('title')!r} "
                    f"must ship collapsed, got {collapsed!r}"
                )
            continue
        y = (panel.get("gridPos") or {}).get("y")
        if not isinstance(y, int) or y >= FIRST_WINDOW_Y:
            continue
        title = str(panel.get("title") or "")
        if panel.get("type") != "table" or not title.startswith("Inspect"):
            continue
        panel_id = panel.get("id")
        key = (dashboard_name, panel_id if isinstance(panel_id, int) else -1)
        if key not in allowed:
            violations.append(
                f"{dashboard_name}:id={panel_id} first-window Inspect table {title!r} "
                "is not allowlisted"
            )
    return violations


def assert_forensic_rows_collapsed_and_below_fold() -> None:
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(
            forensic_first_window_violations(path.name, load_dashboard(path))
        )
    _fail(
        violations,
        "DASH-FIRST-002: forensic Inspect tables/rows must stay collapsed or allowlisted:",
    )


def palette_violations(dashboard_name: str, dashboard: dict[str, Any]) -> list[str]:
    gates = trust_gate_keys()
    violations: list[str] = []
    for panel in dashboard.get("panels") or []:
        if not isinstance(panel, dict):
            continue
        y = (panel.get("gridPos") or {}).get("y")
        if not isinstance(y, int) or y >= FIRST_WINDOW_Y:
            continue
        if not is_first_window_verdict_card(panel):
            continue
        mapping_blob = " ".join(mapping_texts(panel)).upper()
        description = str(panel.get("description") or "").upper()
        missing_map = [token for token in ("OK", "UNKNOWN") if token not in mapping_blob]
        missing_copy = [token for token in _PALETTE_TOKENS if token not in description]
        panel_id = panel.get("id")
        if (dashboard_name, panel_id) in gates and "INCOMPLETE" not in description:
            missing_copy.append("INCOMPLETE")
        if missing_map or missing_copy:
            violations.append(
                f"{dashboard_name}:id={panel_id} mappings missing {missing_map} "
                f"description missing {missing_copy}"
            )
    return violations


def assert_verdict_mappings_and_palette_text() -> None:
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(palette_violations(path.name, load_dashboard(path)))
    _fail(
        violations,
        "DASH-STATE-002: verdict cards need mappings plus palette text:",
    )


def cta_violations(dashboard_name: str, dashboard: dict[str, Any]) -> list[str]:
    no_cta = coverage_allowlist("answer_panels_without_cta")
    layout = answer_panels().get(dashboard_name) or []
    root_by_id = {
        panel.get("id"): panel
        for panel in dashboard.get("panels") or []
        if isinstance(panel, dict)
    }
    violations: list[str] = []
    for entry in layout:
        if not isinstance(entry, dict):
            continue
        panel_id = entry.get("id")
        panel = root_by_id.get(panel_id)
        if not isinstance(panel, dict):
            violations.append(f"{dashboard_name}: answer panel id={panel_id} missing")
            continue
        links = [
            link
            for link in _collect_dashboard_links({"panels": [panel], "links": []})
            if isinstance(link, dict)
        ]
        by_title: dict[str, set[str]] = {}
        dashboard_uids: set[str] = set()
        for link in links:
            title = str(link.get("title") or "").strip()
            url = str(link.get("url") or "")
            uid = extract_dashboard_uid(url)
            if uid is None:
                continue
            dashboard_uids.add(uid)
            if title:
                by_title.setdefault(title, set()).add(uid)
        for title, uids in by_title.items():
            if len(uids) > 1:
                violations.append(
                    f"{dashboard_name}:id={panel_id} CTA {title!r} targets {sorted(uids)}"
                )
        key = (dashboard_name, panel_id if isinstance(panel_id, int) else -1)
        if not dashboard_uids and not any(
            "runbook" in str(link.get("title") or "").lower()
            or "github.com/SatoryKono/BioactivityDataAcquisition" in str(link.get("url") or "")
            for link in links
        ):
            if key not in no_cta:
                violations.append(
                    f"{dashboard_name}:id={panel_id} has no primary dashboard/runbook CTA"
                )
    return violations


def assert_unique_primary_cta() -> None:
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(cta_violations(path.name, load_dashboard(path)))
    _fail(
        violations,
        "DASH-ACTION-001: critical panels must expose a unique primary CTA:",
    )


def http_empty_state_violations(
    dashboard_name: str, dashboard: dict[str, Any]
) -> list[str]:
    violations: list[str] = []
    for panel in get_dashboard_panels(dashboard):
        if panel.get("type") != "table":
            continue
        ops_targets = [
            target
            for target in panel.get("targets") or []
            if isinstance(target, dict) and panel_is_ops_http(panel, target)
        ]
        if not ops_targets:
            continue
        blob = panel_copy_blob(panel).lower()
        has_empty = any(token in blob for token in _EMPTY_TOKENS)
        has_unavailable = any(token in blob for token in _UNAVAILABLE_TOKENS)
        if not has_empty or not has_unavailable:
            violations.append(
                f"{dashboard_name}:id={panel.get('id')} {panel.get('title')!r} "
                f"empty={has_empty} unavailable={has_unavailable}"
            )
    return violations


def assert_http_empty_state_copy() -> None:
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(http_empty_state_violations(path.name, load_dashboard(path)))
    _fail(
        violations,
        "DASH-COPY-001: Ops HTTP tables must distinguish empty from backend unavailable:",
    )


_DATA_EMPTY_TOKENS = (*_EMPTY_TOKENS, "unknown", "incomplete")


def _panel_has_live_target(panel: dict[str, Any]) -> bool:
    for target in panel.get("targets") or []:
        if not isinstance(target, dict) or target.get("hide") is True:
            continue
        expr = target.get("expr")
        url = target.get("url")
        if isinstance(expr, str) and expr.strip():
            return True
        if isinstance(url, str) and url.strip():
            return True
    return False


def data_panel_empty_state_violations(
    dashboard_name: str, dashboard: dict[str, Any]
) -> list[str]:
    """DASH-COPY-001: data-bearing panels must name empty-state behavior."""
    violations: list[str] = []
    for panel in get_dashboard_panels(dashboard):
        if panel.get("type") == "row":
            continue
        if not _panel_has_live_target(panel):
            continue
        blob = panel_copy_blob(panel).lower()
        if not any(token in blob for token in _DATA_EMPTY_TOKENS):
            violations.append(
                f"{dashboard_name}:id={panel.get('id')} {panel.get('title')!r}"
            )
    return violations


def assert_data_panels_name_empty_state() -> None:
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(
            data_panel_empty_state_violations(path.name, load_dashboard(path))
        )
    _fail(
        violations,
        "DASH-COPY-001: data-bearing panels must name empty / UNKNOWN / SELECT RUN:",
    )


def infinity_parser_violations(
    dashboard_name: str, dashboard: dict[str, Any]
) -> list[str]:
    violations: list[str] = []
    for panel in get_dashboard_panels(dashboard):
        for target in panel.get("targets") or []:
            if not isinstance(target, dict) or not panel_is_ops_http(panel, target):
                continue
            root = str(target.get("root_selector") or "").strip()
            if root not in _ROWS_SELECTORS:
                continue
            parser = target.get("parser")
            if parser != "backend":
                violations.append(
                    f"{dashboard_name}:id={panel.get('id')} {panel.get('title')!r} "
                    f"root_selector={root!r} parser={parser!r}"
                )
    return violations


def assert_infinity_parser_backend_for_rows() -> None:
    violations: list[str] = []
    for path in get_dashboard_files():
        violations.extend(infinity_parser_violations(path.name, load_dashboard(path)))
    _fail(
        violations,
        "DASH-DATA-001: Ops HTTP rows tables must use parser=backend:",
    )
