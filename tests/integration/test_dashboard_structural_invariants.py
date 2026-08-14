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
"""Structural and integrity invariants for shipped Grafana dashboards.

These tests lock in JSON-structural, datasource, link, visualization, and
fail-closed invariants that are cheap to verify statically and were previously
uncovered by the existing dashboard test surface. See the normative section
"Структурные и целостностные инварианты" in
``docs/03-guides/dashboards/design-system.md``.

Scope note: assertions are calibrated against the currently shipped dashboards
so they encode known-good behaviour and act as regression guards (not
aspirational rewrites).
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


# --- Allowlists calibrated from the shipped surface -------------------------

# Canonical modern panel plugin types used by the shipped suite. Legacy `graph`
# and unknown/typo plugin types are intentionally rejected.
ALLOWED_PANEL_TYPES = frozenset(
    {
        "text",
        "row",
        "stat",
        "gauge",
        "bargauge",
        "table",
        "timeseries",
        "state-timeline",
        "heatmap",
    }
)

# Datasource identities the suite is allowed to reference. Loki/Tempo and any
# other datasource families are rejected (ADR-010 monitoring-surface reduction).
ALLOWED_DATASOURCE_STRINGS = frozenset(
    {"Prometheus", "BioETL Ops HTTP", "-- Grafana --", "Grafana"}
)
ALLOWED_DATASOURCE_TYPES = frozenset(
    {"prometheus", "grafana", "datasource", "yesoreyeram-infinity-datasource"}
)

# Deterministic single/aggregate reducers permitted for stat/gauge panels.
ALLOWED_REDUCER_CALCS = frozenset(
    {
        "lastNotNull",
        "last",
        "first",
        "firstNotNull",
        "min",
        "max",
        "mean",
        "sum",
        "count",
        "range",
        "delta",
        "diff",
    }
)

# Link URL schemes allowed anywhere in a shipped dashboard. The single absolute
# HTTP exception is the local Prometheus targets UI (BioETL is local-only).
_ALLOWED_URL_PREFIXES = (
    "/",
    "https://github.com/SatoryKono/BioactivityDataAcquisition/",
    "data:text/plain,",
    "http://localhost:9090/",
)

# HTML text panels must not carry executable or embedding vectors.
_FORBIDDEN_HTML_PATTERNS = (
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
    re.compile(r"<\s*object", re.IGNORECASE),
    re.compile(r"<\s*embed", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"\son[a-z]+\s*=", re.IGNORECASE),
)

_D_UID_RE = re.compile(r"/d/([^/?&#]+)")
_MAX_DATA_POINTS_CEILING = 5000
_GRID_COLUMNS = 24


def _panel_datasources(panel: dict[str, Any]):
    """Yield the panel-level datasource and every target-level datasource."""
    if "datasource" in panel:
        yield panel.get("datasource")
    for target in panel.get("targets", []) or []:
        if isinstance(target, dict) and "datasource" in target:
            yield target.get("datasource")


def _datasource_token(datasource: Any) -> tuple[str, str]:
    """Return (kind, value) describing a datasource for allowlist checks."""
    if datasource is None:
        return ("none", "")
    if isinstance(datasource, str):
        return ("string", datasource)
    if isinstance(datasource, dict):
        return ("type", str(datasource.get("type") or ""))
    return ("other", repr(datasource))


def _shipped_uids() -> set[str]:
    uids: set[str] = set()
    for dashboard_path in get_dashboard_files():
        uid = load_dashboard(dashboard_path).get("uid")
        if isinstance(uid, str) and uid:
            uids.add(uid)
    return uids


def _is_background_verdict_stat(panel: dict[str, Any]) -> bool:
    """Designated first-screen current-status severity card (design §2.1)."""
    return panel.get("type") == "stat" and (
        (panel.get("options") or {}).get("colorMode") == "background"
    )


# --- 1. Unique panel ids ----------------------------------------------------


def test_panel_ids_are_unique_within_each_dashboard() -> None:
    """Duplicate panel ids break data links, repeats, and row expansion."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        seen: dict[int, str] = {}
        for panel in get_dashboard_panels(dashboard):
            panel_id = panel.get("id")
            if panel_id is None:
                continue
            assert panel_id not in seen, (
                f"{dashboard_path.name} has duplicate panel id={panel_id} "
                f"({seen.get(panel_id)!r} and {panel.get('title')!r})"
            )
            seen[panel_id] = str(panel.get("title"))


# --- 2. Root id must be null (provisioning-safe) ----------------------------


def test_dashboard_root_id_is_null() -> None:
    """Provisioned JSON must not carry a numeric root id (import collisions)."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        assert dashboard.get("id") is None, (
            f"{dashboard_path.name} root 'id' must be null, got {dashboard.get('id')!r}"
        )


# --- 3. Panels fit inside the 24-column grid --------------------------------


def test_panels_fit_within_grid_columns() -> None:
    """gridPos must stay within the 24-column grid with positive extents."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            grid = panel.get("gridPos")
            if not isinstance(grid, dict):
                continue
            x = int(grid.get("x", 0))
            y = int(grid.get("y", 0))
            w = int(grid.get("w", 0))
            h = int(grid.get("h", 0))
            ident = f"{dashboard_path.name}:id={panel.get('id')} {panel.get('title')!r}"
            assert x >= 0 and y >= 0, f"{ident} gridPos x/y must be non-negative"
            assert w >= 1 and h >= 1, f"{ident} gridPos w/h must be positive"
            assert x + w <= _GRID_COLUMNS, (
                f"{ident} exceeds the {_GRID_COLUMNS}-column grid (x={x}, w={w})"
            )


# --- 4. Datasource allowlist ------------------------------------------------


def test_panel_datasources_use_allowed_identities() -> None:
    """Every panel/target datasource must be a known shipped datasource."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            for datasource in _panel_datasources(panel):
                kind, value = _datasource_token(datasource)
                ident = (
                    f"{dashboard_path.name}:id={panel.get('id')} "
                    f"{panel.get('title')!r} datasource={datasource!r}"
                )
                if kind == "none":
                    continue
                if kind == "string":
                    assert value in ALLOWED_DATASOURCE_STRINGS, (
                        f"{ident} uses an unknown datasource string"
                    )
                elif kind == "type":
                    assert value in ALLOWED_DATASOURCE_TYPES, (
                        f"{ident} uses an unknown datasource type"
                    )
                else:
                    pytest.fail(f"{ident} has a malformed datasource reference")


# --- 5. Removed Loki/Tempo/quarantine-explorer datasources stay gone --------


def test_no_removed_loki_tempo_or_quarantine_datasources() -> None:
    """ADR-010: Loki/Tempo and the :8081 quarantine explorer were removed."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            for datasource in _panel_datasources(panel):
                kind, value = _datasource_token(datasource)
                lowered = value.lower()
                assert "loki" not in lowered and "tempo" not in lowered, (
                    f"{dashboard_path.name}:id={panel.get('id')} references removed "
                    f"datasource {datasource!r}"
                )
            for target in panel.get("targets", []) or []:
                if not isinstance(target, dict):
                    continue
                url = str(target.get("url") or "")
                assert ":8081" not in url, (
                    f"{dashboard_path.name}:id={panel.get('id')} references removed "
                    f"quarantine-explorer endpoint {url!r}"
                )


# --- 6. HTML text panels are sanitizer-safe ---------------------------------


def test_html_text_panels_have_no_executable_or_embed_vectors() -> None:
    """HTML panels must not carry <script>/<iframe>/js:/on*= vectors."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            options = panel.get("options") or {}
            if options.get("mode") != "html":
                continue
            content = str(options.get("content") or "")
            for pattern in _FORBIDDEN_HTML_PATTERNS:
                assert not pattern.search(content), (
                    f"{dashboard_path.name}:id={panel.get('id')} HTML content matches "
                    f"forbidden pattern {pattern.pattern!r}"
                )


# --- 7. Link URLs are relative, canonical GitHub, or allowlisted ------------


def test_link_urls_use_allowlisted_schemes() -> None:
    """All dashboard/panel/data links must use safe, non-arbitrary URLs."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for link in _collect_dashboard_links(dashboard):
            url = str(link.get("url") or "")
            if not url:
                continue
            assert url.startswith(_ALLOWED_URL_PREFIXES), (
                f"{dashboard_path.name} link {link.get('title')!r} uses a "
                f"non-allowlisted URL: {url!r}"
            )


# --- 8. Internal /d/<uid> links resolve to a shipped dashboard --------------


def test_internal_dashboard_links_resolve_to_shipped_uids() -> None:
    """Every /d/<uid> handoff must point to an actually shipped dashboard."""
    shipped = _shipped_uids()
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for link in _collect_dashboard_links(dashboard):
            url = str(link.get("url") or "")
            match = _D_UID_RE.search(url)
            if not match:
                continue
            target_uid = match.group(1)
            assert target_uid in shipped, (
                f"{dashboard_path.name} link {link.get('title')!r} points to "
                f"unknown dashboard uid {target_uid!r} (dangling handoff)"
            )


# --- 9. reduceOptions.calcs use deterministic reducers ----------------------


def test_reduce_option_calcs_are_deterministic() -> None:
    """stat/gauge reducers must be a known deterministic reducer set."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            reduce_options = (panel.get("options") or {}).get("reduceOptions") or {}
            calcs = reduce_options.get("calcs")
            if calcs is None:
                continue
            assert isinstance(calcs, list) and calcs, (
                f"{dashboard_path.name}:id={panel.get('id')} reduceOptions.calcs "
                "must be a non-empty list when present"
            )
            for calc in calcs:
                assert calc in ALLOWED_REDUCER_CALCS, (
                    f"{dashboard_path.name}:id={panel.get('id')} uses non-deterministic "
                    f"reducer {calc!r}"
                )


# --- 10. maxDataPoints stays bounded when set -------------------------------


def test_max_data_points_are_bounded_when_present() -> None:
    """A set maxDataPoints must be a sane positive bound (performance guard)."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            mdp = panel.get("maxDataPoints")
            if mdp is None:
                continue
            assert isinstance(mdp, int) and not isinstance(mdp, bool), (
                f"{dashboard_path.name}:id={panel.get('id')} maxDataPoints must be int"
            )
            assert 1 <= mdp <= _MAX_DATA_POINTS_CEILING, (
                f"{dashboard_path.name}:id={panel.get('id')} maxDataPoints={mdp} "
                f"out of bounds [1, {_MAX_DATA_POINTS_CEILING}]"
            )


# --- 11. Panel type allowlist (ban legacy graph / unknown plugins) ----------


def test_panel_types_are_allowlisted() -> None:
    """Panels must use canonical modern plugin types; legacy graph is banned."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            panel_type = panel.get("type")
            assert panel_type in ALLOWED_PANEL_TYPES, (
                f"{dashboard_path.name}:id={panel.get('id')} uses non-allowlisted "
                f"panel type {panel_type!r}"
            )


# --- 12. Current-status verdict cards fail closed (noValue) ------------------


def test_current_status_cards_fail_closed_no_value() -> None:
    """Background severity cards must render missing data as UNKNOWN."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if not _is_background_verdict_stat(panel):
                continue
            defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
            no_value = defaults.get("noValue")
            ident = f"{dashboard_path.name}:id={panel.get('id')} {panel.get('title')!r}"
            assert no_value is not None, (
                f"{ident} background verdict card must set fieldConfig.defaults.noValue"
            )
            assert str(no_value).startswith("UNKNOWN"), (
                f"{ident} verdict noValue must fail closed to UNKNOWN, got {no_value!r}"
            )


# --- 13. Current-status verdict cards carry interpretation guidance ---------


def test_current_status_cards_have_guidance_and_state_mappings() -> None:
    """Background severity cards need a description and explicit state mappings."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if not _is_background_verdict_stat(panel):
                continue
            ident = f"{dashboard_path.name}:id={panel.get('id')} {panel.get('title')!r}"
            description = str(panel.get("description") or "").strip()
            assert description, (
                f"{ident} verdict card must document operator interpretation"
            )
            mappings = (panel.get("fieldConfig") or {}).get("defaults", {}).get(
                "mappings"
            )
            assert isinstance(mappings, list) and mappings, (
                f"{ident} verdict card must define explicit value mappings "
                "(no bare numbers)"
            )
