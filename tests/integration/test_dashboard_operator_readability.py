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
"""Required operator-readability gates for shipped Grafana dashboards.

Covers:
1. Inline copy roles (dashboard / panel / status / field) — DASH-COPY-008
2. Operator clock YYYY-MM-DD HH:MM via Grafana unit time:YYYY-MM-DD HH:mm — DASH-TIME-001
3. First-window panels must not declare internal scroll — DASH-FIT-004 static half

These tests are the required check whenever grafana/dashboards/*.json changes
(CI Tests → Dashboard semantic release policy gate, plus pre-push hook).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.integration._dashboard_layout_budgets import (
    FIRST_WINDOW_Y,
    is_first_window_panel,
    select_first_window_panels,
)
from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
    panel_display_title,
)
from tests.integration.test_dashboard_units_decimals import DASHBOARD_DATETIME_UNIT


pytestmark = pytest.mark.integration

DESIGN_SYSTEM = Path("docs/03-guides/dashboards/design-system.md")
MONITORING_COMPOSE = Path("docker-compose.monitoring.yml")
COPY_ROLE_ENFORCED_DASHBOARDS = frozenset({"bioetl-control-plane-v1.json"})

NUMBERED_DASHBOARDS = (
    "0. Trust",
    "1. Overview",
    "2. Pipeline Diagnostics",
    "3. Provider Health",
    "4. Data Quality",
    "5. Incident Workspace",
    "6. Run Explorer",
)
STATUS_SCOPE_TOKENS = (
    "INCOMPLETE",
    "UNKNOWN",
    "SELECTED RUN",
    "TIME RANGE",
    "SELECTED PROVIDER",
    "VALID EMPTY",
    "TELEMETRY ABSENT",
    "EMPTY DOMAIN",
    "FULL PATHS",
)
STATUS_SCOPE_AND_VERDICT_TOKENS = (
    *STATUS_SCOPE_TOKENS,
    "CURRENT",
    "OK",
    "WARN",
    "CRIT",
)
FIELD_IDENTIFIERS = (
    "processing_status",
    "trust_status",
    "evidence_observed_at",
    "completed_at",
    "scope_kind",
    "evidence_freshness",
    "payload_hash",
    "manifest_id",
    "risk_type",
    "run_id",
)
TIMESTAMP_FIELD_RE = re.compile(r"(?:^|_)((?:completed|created|updated|saved|observed)_at|evidence_observed_at)$")
FORBIDDEN_DATETIME_UNITS = frozenset(
    {
        "dateTimeAsIso",
        "dateTimeAsISO",
        "dateTimeFromNow",
        "dateTimeAsUS",
        "dateTimeAsLocal",
        "time:YYYY-MM-DD HH:MM",
    }
)
_OVERFLOW_RE = re.compile(r"overflow(?:-[xy])?\s*:\s*(auto|scroll|hidden)", re.I)
_STRIP_HREF_RE = re.compile(r"\b(?:href|url)\s*=\s*\"[^\"]*\"", re.I)
_NAV_MARKERS = ("bioetl-nav", "Navigate Dashboards")
_MIN_PANEL_TITLE_LEN = 16


def _html_content(panel: dict[str, Any]) -> str:
    options = panel.get("options")
    if not isinstance(options, dict):
        return ""
    content = options.get("content")
    return content if isinstance(content, str) else ""


def _is_nav_panel(panel: dict[str, Any]) -> bool:
    content = _html_content(panel)
    title = panel_display_title(panel)
    return any(marker in content for marker in _NAV_MARKERS) or title == "Navigate Dashboards"


def _inside_tag(html: str, start: int, tag: str) -> bool:
    before = html[:start]
    pattern = re.compile(rf"<{tag}\b|</{tag}>", re.I)
    last_open = -1
    depth = 0
    for match in pattern.finditer(before):
        token = match.group(0).lower()
        if token.startswith(f"</{tag}"):
            depth = max(0, depth - 1)
            if depth == 0:
                last_open = -1
        else:
            depth += 1
            last_open = match.start()
    return last_open >= 0


def _inside_any(html: str, start: int, tags: tuple[str, ...]) -> bool:
    return any(_inside_tag(html, start, tag) for tag in tags)


def _iter_field_units(panel: dict[str, Any]) -> list[tuple[str, str | None]]:
    found: list[tuple[str, str | None]] = []
    defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
    default_unit = defaults.get("unit")
    if isinstance(default_unit, str) and default_unit:
        found.append((default_unit, None))
    for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
        if not isinstance(override, dict):
            continue
        matcher = override.get("matcher") or {}
        matcher_options = matcher.get("options") if isinstance(matcher, dict) else None
        label = matcher_options if isinstance(matcher_options, str) else None
        for prop in override.get("properties") or []:
            if isinstance(prop, dict) and prop.get("id") == "unit":
                value = prop.get("value")
                if isinstance(value, str) and value:
                    found.append((value, label))
    return found


def _converted_time_fields(panel: dict[str, Any]) -> set[str]:
    fields: set[str] = set()
    for transform in panel.get("transformations") or []:
        if not isinstance(transform, dict) or transform.get("id") != "convertFieldType":
            continue
        conversions = (transform.get("options") or {}).get("conversions") or []
        for conversion in conversions:
            if not isinstance(conversion, dict):
                continue
            if conversion.get("destinationType") != "time":
                continue
            target = conversion.get("targetField")
            if isinstance(target, str) and target:
                fields.add(target)
    return fields


def _timestamp_names_from_matcher(label: str | None) -> list[str]:
    if not label:
        return []
    names = re.findall(r"[A-Za-z][A-Za-z0-9_]*", label)
    return [name for name in names if TIMESTAMP_FIELD_RE.search(name)]


def _root_panels(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    return [panel for panel in dashboard.get("panels") or [] if isinstance(panel, dict)]


def _long_panel_titles(dashboard: dict[str, Any]) -> list[str]:
    titles: list[str] = []
    for panel in get_dashboard_panels(dashboard):
        title = panel_display_title(panel)
        if len(title) < _MIN_PANEL_TITLE_LEN:
            continue
        if title == "Navigate Dashboards":
            continue
        titles.append(title)
    titles.sort(key=len, reverse=True)
    return titles


def test_design_system_documents_inline_copy_roles() -> None:
    text = DESIGN_SYSTEM.read_text(encoding="utf-8")
    assert "### 9.1 Inline copy roles in authored HTML" in text
    assert "<b>0. Trust</b>" in text
    assert "<em>Review Selected-Run Trust</em>" in text
    assert "plain `INCOMPLETE`" in text
    assert '<code style="font-size:16px">trust_status</code>' in text
    assert "regular `16px`" in text


def test_enforced_dashboards_apply_inline_copy_roles() -> None:
    """DASH-COPY-008: opted-in authored HTML uses the five inline roles."""
    violations: list[str] = []
    by_name = {path.name: path for path in get_dashboard_files()}
    missing = sorted(COPY_ROLE_ENFORCED_DASHBOARDS - set(by_name))
    assert not missing, f"enforced dashboards missing from grafana/dashboards: {missing}"

    for name in sorted(COPY_ROLE_ENFORCED_DASHBOARDS):
        dashboard = load_dashboard(by_name[name])
        panel_titles = _long_panel_titles(dashboard)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "text" or _is_nav_panel(panel):
                continue
            html = _html_content(panel)
            if not html:
                continue
            loc = f"{name}:id={panel.get('id')}"
            own_title = panel_display_title(panel)

            for dashboard_name in NUMBERED_DASHBOARDS:
                for match in re.finditer(re.escape(dashboard_name), html):
                    if not _inside_tag(html, match.start(), "b"):
                        violations.append(
                            f"{loc} dashboard name {dashboard_name!r} must be <b>…</b>"
                        )

            consumed: set[tuple[int, int]] = set()
            for title in panel_titles:
                if title == own_title:
                    continue
                for variant in (title, title.replace("&", "&amp;")):
                    start = 0
                    while True:
                        idx = html.find(variant, start)
                        if idx < 0:
                            break
                        span = (idx, idx + len(variant))
                        start = idx + 1
                        if any(
                            other[0] <= span[0] and span[1] <= other[1]
                            for other in consumed
                        ):
                            continue
                        consumed.add(span)
                        if not _inside_tag(html, idx, "em"):
                            violations.append(
                                f"{loc} panel title {title!r} must be <em>…</em>"
                            )
                        if _inside_any(html, idx, ("b", "strong", "code")):
                            violations.append(
                                f"{loc} panel title {title!r} must not be bold or <code>"
                            )

            for token in STATUS_SCOPE_AND_VERDICT_TOKENS:
                for match in re.finditer(re.escape(token), html):
                    if _inside_any(html, match.start(), ("b", "strong")):
                        violations.append(
                            f"{loc} status/scope {token!r} must be CAPS without bold"
                        )

            stripped = _STRIP_HREF_RE.sub("", html)
            for field in FIELD_IDENTIFIERS:
                for match in re.finditer(rf"\b{re.escape(field)}\b", stripped):
                    if not _inside_tag(stripped, match.start(), "code"):
                        violations.append(
                            f"{loc} field {field!r} must be <code> 16px"
                        )

    assert not violations, "inline copy-role violations:\n" + "\n".join(violations)


def test_status_scope_tokens_keep_canonical_caps_in_authored_html() -> None:
    """Bold/strong status-scope labels must use the canonical CAPS token."""
    label_re = re.compile(r"<(?P<tag>b|strong)\b[^>]*>(?P<body>.*?)</(?P=tag)>", re.I | re.S)
    canon = {token.casefold(): token for token in STATUS_SCOPE_TOKENS}
    violations: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") != "text" or _is_nav_panel(panel):
                continue
            html = _html_content(panel)
            if not html:
                continue
            for match in label_re.finditer(html):
                body = re.sub(r"<[^>]+>", "", match.group("body")).strip()
                expected = canon.get(body.casefold())
                if expected and body != expected:
                    violations.append(
                        f"{path.name}:id={panel.get('id')} {body!r} must be {expected!r}"
                    )
    assert not violations, "status/scope capitalization:\n" + "\n".join(violations)


def test_datetime_units_are_yyyy_mm_dd_hh_mm() -> None:
    """DASH-TIME-001: operator clock is YYYY-MM-DD HH:MM (Grafana mm = minutes)."""
    violations: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in get_dashboard_panels(dashboard):
            for unit, label in _iter_field_units(panel):
                loc = f"{path.name}:id={panel.get('id')} field={label!r}"
                if unit in FORBIDDEN_DATETIME_UNITS:
                    violations.append(f"{loc} forbids {unit!r}")
                    continue
                if unit.startswith("time:") or unit.startswith("dateTime"):
                    if unit != DASHBOARD_DATETIME_UNIT:
                        violations.append(
                            f"{loc} datetime unit must be {DASHBOARD_DATETIME_UNIT}, "
                            f"got {unit!r}"
                        )
    assert not violations, "datetime unit violations:\n" + "\n".join(violations)


def test_http_iso_timestamp_fields_convert_to_time() -> None:
    """ISO HTTP strings need convertFieldType or the unit prints raw 8601."""
    violations: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in get_dashboard_panels(dashboard):
            datasource = panel.get("datasource")
            is_ops_http = datasource == "BioETL Ops HTTP" or (
                isinstance(datasource, dict)
                and "ops" in str(datasource.get("type", "")).lower()
            )
            if not is_ops_http and panel.get("type") != "table":
                continue
            converted = _converted_time_fields(panel)
            for unit, label in _iter_field_units(panel):
                if unit != DASHBOARD_DATETIME_UNIT:
                    continue
                for field in _timestamp_names_from_matcher(label):
                    if field not in converted:
                        violations.append(
                            f"{path.name}:id={panel.get('id')} {field} uses "
                            f"{DASHBOARD_DATETIME_UNIT} but has no convertFieldType→time"
                        )
    assert not violations, "timestamp convertFieldType gaps:\n" + "\n".join(violations)


def test_grafana_compose_date_formats_use_yyyy_mm_dd_hh_mm() -> None:
    payload = yaml.safe_load(MONITORING_COMPOSE.read_text(encoding="utf-8"))
    environment = [
        str(item)
        for item in payload["services"]["grafana"]["environment"]
    ]
    required = {
        "GF_DATE_FORMATS_FULL_DATE=YYYY-MM-DD HH:mm",
        "GF_DATE_FORMATS_INTERVAL_MINUTE=YYYY-MM-DD HH:mm",
        "GF_DATE_FORMATS_INTERVAL_HOUR=YYYY-MM-DD HH:mm",
        "GF_DATE_FORMATS_INTERVAL_DAY=YYYY-MM-DD",
        "GF_DATE_FORMATS_USE_BROWSER_LOCALE=false",
    }
    missing = sorted(required.difference(environment))
    assert not missing, f"compose date formats missing: {missing}"
    assert not any("HH:MM" in item for item in environment if item.startswith("GF_DATE_FORMATS_")), (
        "Grafana date tokens must use mm for minutes; MM is months"
    )


def test_first_window_panels_do_not_declare_internal_scroll() -> None:
    """DASH-FIT-004 static half: first-window JSON must not opt into scroll/clip."""
    violations: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        first_window = select_first_window_panels(_root_panels(dashboard))
        assert first_window, f"{path.name} has no first-window panels"
        for panel in first_window:
            assert is_first_window_panel(panel)
            grid = panel.get("gridPos") or {}
            bottom = int(grid.get("y", 0)) + int(grid.get("h", 0))
            if bottom > FIRST_WINDOW_Y:
                violations.append(
                    f"{path.name}:id={panel.get('id')} first-window bottom "
                    f"{bottom} > FIRST_WINDOW_Y={FIRST_WINDOW_Y}"
                )
            html = _html_content(panel)
            if not html:
                continue
            for match in _OVERFLOW_RE.finditer(html):
                kind = match.group(1).lower()
                window = html[max(0, match.start() - 120) : match.end() + 80]
                compact = re.sub(r"\s+", "", window)
                spacer = kind == "hidden" and "height:0" in compact and (
                    "aria-hidden" in window or "flex:11 100%" in compact
                )
                if spacer:

                    continue
                violations.append(
                    f"{path.name}:id={panel.get('id')} first-window overflow:{kind} "
                    f"at {match.start()}"
                )
            if "white-space:nowrap" in html and not _is_nav_panel(panel):
                violations.append(
                    f"{path.name}:id={panel.get('id')} first-window nowrap risks scroll"
                )
    assert not violations, "first-window scroll declarations:\n" + "\n".join(violations)


def test_operator_readability_gate_is_wired_as_required_dashboard_check() -> None:
    """The gate must stay in CI and the pre-push hook when dashboards change."""
    tests_workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    pre_commit = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    skill = Path(".codex/skills/observability-dashboard/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "test_dashboard_operator_readability.py" in tests_workflow
    assert "check-dashboard-operator-readability" in pre_commit
    assert "test_dashboard_operator_readability.py" in pre_commit
    assert "test_dashboard_operator_readability.py" in skill
