#!/usr/bin/env python3
"""Phase-2 profile linter for provisioned BioETL Grafana dashboards (rev7 §4.5).

Checks (phase-2 profile only — not the full phase-4 set):
- viewPanel targets resolve to an existing panel id on the destination board
- navigation bus: five chips, width 19.5%, current chip is <span.bioetl-nav-current>
- indexByName values are unique within each organize transform
- text/stat threshold base step is not green (#73BF69 / green)
- link titles that name a dashboard destination match the URL uid when detectable
- no GitHub runbook URL carries Grafana query templates
- no ``/${action_path}&`` glue
- Phase 2.5 donor JSONata bracket balance (when the apply module is importable)

Exit 0 when clean; print findings and exit 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[4]
DASH_DIR = ROOT / "grafana" / "dashboards"
FILES = (
    "bioetl-overview-v2.json",
    "bioetl-dq-v2.json",
    "bioetl-incident-v1.json",
    "bioetl-control-plane-v1.json",
    "bioetl-run-explorer-v1.json",
)
UID_BY_FILE = {
    "bioetl-overview-v2.json": "bioetl-overview-v2",
    "bioetl-dq-v2.json": "bioetl-dq-v2",
    "bioetl-incident-v1.json": "bioetl-incident-v1",
    "bioetl-control-plane-v1.json": "bioetl-control-plane-v1",
    "bioetl-run-explorer-v1.json": "bioetl-run-explorer-v1",
}
GREEN = frozenset({"green", "#73BF69", "#73bf69", "#56A64B", "#56a64b"})
_AMP = "&"
_AMP_ENTITY = "&amp;"
_NAV_CHIP_TITLES = (
    "Run Explorer",
    "Replay Readiness",
    "Run Overview",
    "Data Quality",
    "6. Incident Workspace",
)
_STATUS_TOKENS = (
    "OK",
    "WARN",
    "CRIT",
    "ERROR",
    "UNKNOWN",
    "SELECT RUN",
    "INCOMPLETE",
)


def _walk(panels: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack = list(panels or [])
    while stack:
        panel = stack.pop(0)
        if not isinstance(panel, dict):
            continue
        out.append(panel)
        nested = panel.get("panels")
        if isinstance(nested, list):
            stack[0:0] = [item for item in nested if isinstance(item, dict)]
    return out


def _ids(panels: list[dict[str, Any]]) -> set[int]:
    return {
        panel_id for panel in panels if isinstance((panel_id := panel.get("id")), int)
    }


def _urls_from_html(value: str) -> list[tuple[str, str]]:
    if "href=" not in value and "/d/" not in value:
        return []
    return [
        ("", match.group(1).replace(_AMP_ENTITY, _AMP))
        for match in re.finditer(r'href="([^"]+)"', value)
    ]


def _iter_urls(value: Any) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        found: list[tuple[str, str]] = []
        url = value.get("url")
        if isinstance(url, str) and url:
            found.append((str(value.get("title") or ""), url))
        for item in value.values():
            found.extend(_iter_urls(item))
        return found
    if isinstance(value, list):
        found = []
        for item in value:
            found.extend(_iter_urls(item))
        return found
    if isinstance(value, str):
        return _urls_from_html(value)
    return []


def parse_dashboard_view_panel(url: str) -> tuple[str | None, int | None]:
    """Extract ``/d/{uid}/…`` destination uid and ``viewPanel`` from any query position."""
    cleaned = url.replace(_AMP_ENTITY, _AMP)
    parts = urlsplit(cleaned)
    path_match = re.match(r"/d/([^/?#]+)/", parts.path)
    if path_match is None:
        return None, None
    dest_uid = path_match.group(1)
    query = parse_qs(parts.query, keep_blank_values=True)
    raw = query.get("viewPanel") or query.get("var-viewPanel")
    if raw:
        try:
            return dest_uid, int(raw[0])
        except (TypeError, ValueError):
            return dest_uid, None
    # Grafana template fragments may leave viewPanel outside parse_qs keys.
    fallback = re.search(r"(?:^|&)viewPanel=(\d+)", parts.query)
    if fallback:
        return dest_uid, int(fallback.group(1))
    return dest_uid, None


_NAV_DESTINATIONS = {
    "Run Explorer": "bioetl-run-explorer-v1",
    "Replay Readiness": "bioetl-control-plane-v1",
    "Run Overview": "bioetl-overview-v2",
    "Data Quality": "bioetl-dq-v2",
    "6. Incident Workspace": "bioetl-incident-v1",
}
_NAV_CHIP_WIDTH_RE = re.compile(r"(?:^|;)\s*width:19\.5%\s*(?:;|$)")
_NAV_ELEMENT_RE = re.compile(
    r"<(a|span)\b([^>]*)>(.*?)</\1>",
    flags=re.IGNORECASE | re.DOTALL,
)


def _nav_chips(content: str) -> list[tuple[str, str, str]]:
    elements = [
        (
            match.group(1).lower(),
            match.group(2),
            re.sub(r"<[^>]+>", "", match.group(3)).strip(),
        )
        for match in _NAV_ELEMENT_RE.finditer(content)
    ]
    return [
        (tag, attrs, label)
        for tag, attrs, label in elements
        if "bioetl-nav-link" in attrs or "bioetl-nav-current" in attrs
    ]


def _nav_chip_width_findings(
    path_name: str, chips: list[tuple[str, str, str]], content: str
) -> list[str]:
    findings: list[str] = []
    if len(chips) != 5:
        findings.append(
            f"{path_name}: panel 1000 expected five navigation elements, found {len(chips)}"
        )
    for _, attrs, label in chips:
        style = re.search(r'\bstyle="([^"]*)"', attrs)
        if style is None or not _NAV_CHIP_WIDTH_RE.search(style.group(1)):
            findings.append(
                f"{path_name}: panel 1000 chip {label!r} must use width 19.5%"
            )
    if "16.5%" in content:
        findings.append(f"{path_name}: panel 1000 still uses legacy 16.5% chip width")
    return findings


def _nav_current_findings(
    path_name: str, chips: list[tuple[str, str, str]]
) -> list[str]:
    current = [chip for chip in chips if "bioetl-nav-current" in chip[1]]
    if len(current) == 1 and current[0][0] == "span":
        return []
    return [
        f"{path_name}: panel 1000 current chip must be "
        '<span class="bioetl-nav-current">'
    ]


def _nav_destination_findings(
    path_name: str, chips: list[tuple[str, str, str]]
) -> list[str]:
    findings: list[str] = []
    for title in _NAV_CHIP_TITLES:
        matches = [chip for chip in chips if chip[2] == title]
        if len(matches) != 1:
            findings.append(
                f"{path_name}: panel 1000 expected one navigation element for "
                f"{title!r}, found {len(matches)}"
            )
            continue
        tag, attrs, _ = matches[0]
        if "bioetl-nav-current" in attrs:
            continue
        href = re.search(r'\bhref="([^"]+)"', attrs)
        if tag != "a" or "bioetl-nav-link" not in attrs or href is None:
            findings.append(
                f"{path_name}: panel 1000 chip {title!r} must be a linked anchor"
            )
        elif f"/d/{_NAV_DESTINATIONS[title]}/" not in href.group(1):
            findings.append(
                f"{path_name}: panel 1000 chip {title!r} has the wrong destination"
            )
    return findings


def _nav_content_findings(path_name: str, content: str) -> list[str]:
    findings: list[str] = []
    if "bioetl-nav" not in content:
        findings.append(f"{path_name}: panel 1000 missing bioetl-nav markup")
    chips = _nav_chips(content)
    findings.extend(_nav_chip_width_findings(path_name, chips, content))
    findings.extend(_nav_current_findings(path_name, chips))
    findings.extend(_nav_destination_findings(path_name, chips))
    return findings


def _lint_nav(path: Path, panels: list[dict[str, Any]]) -> list[str]:
    nav = next((p for p in panels if p.get("id") == 1000), None)
    if nav is None:
        return [f"{path.name}: missing navigation panel id=1000"]
    content = str((nav.get("options") or {}).get("content") or "")
    return _nav_content_findings(path.name, content)


def _index_collisions(index: dict[Any, Any]) -> list[tuple[Any, list[str]]]:
    seen: dict[Any, list[str]] = {}
    for name, position in index.items():
        seen.setdefault(position, []).append(str(name))
    return [(position, names) for position, names in seen.items() if len(names) > 1]


def _organize_collisions(panel: dict[str, Any]) -> list[tuple[Any, list[str]]]:
    collisions: list[tuple[Any, list[str]]] = []
    for transform in panel.get("transformations") or []:
        if not isinstance(transform, dict) or transform.get("id") != "organize":
            continue
        index = (transform.get("options") or {}).get("indexByName") or {}
        if isinstance(index, dict):
            collisions.extend(_index_collisions(index))
    return collisions


def _lint_organize(path: Path, panels: list[dict[str, Any]]) -> list[str]:
    return [
        (
            f"{path.name}: panel {panel.get('id')} indexByName "
            f"collision at {position}: {names}"
        )
        for panel in panels
        for position, names in _organize_collisions(panel)
    ]


def _text_has_status_token(text: str) -> bool:
    return any(token in text for token in _STATUS_TOKENS)


def _mapping_option_texts(key: Any, meta: Any) -> tuple[str, str]:
    key_text = str(key)
    value_text = str(meta.get("text") or "") if isinstance(meta, dict) else ""
    return key_text, value_text


def _non_digit_mapping_is_status(key_text: str, value_text: str) -> bool:
    return (
        _text_has_status_token(key_text)
        or _text_has_status_token(value_text)
        or bool(key_text)
    )


def _accumulate_digit_mapping(
    key_text: str,
    value_text: str,
    *,
    status_hits: int,
    count_style_hits: int,
) -> tuple[int, int]:
    if _text_has_status_token(key_text) or _text_has_status_token(value_text):
        return status_hits + 1, count_style_hits
    if value_text and not value_text.isdigit():
        # e.g. "0 blockers" — numeric count panel, not an OK/CRIT palette.
        return status_hits, count_style_hits + 1
    return status_hits, count_style_hits


def _value_options_look_like_status(options: dict[Any, Any]) -> bool:
    status_hits = 0
    count_style_hits = 0
    for key, meta in options.items():
        key_text, value_text = _mapping_option_texts(key, meta)
        if not key_text.isdigit():
            return _non_digit_mapping_is_status(key_text, value_text)
        status_hits, count_style_hits = _accumulate_digit_mapping(
            key_text,
            value_text,
            status_hits=status_hits,
            count_style_hits=count_style_hits,
        )
    return status_hits > 0 and count_style_hits == 0


def _mapping_has_status_token(item: dict[str, Any]) -> bool:
    kind = item.get("type")
    options = item.get("options") or {}
    if kind == "regex":
        return _text_has_status_token(str(options.get("pattern") or ""))
    if kind != "value" or not isinstance(options, dict):
        return False
    return _value_options_look_like_status(options)


def _mappings_look_like_text_status(mappings: list[Any]) -> bool:
    """True when mappings encode OK/WARN/CRIT-style labels (not numeric counts)."""
    return any(
        isinstance(item, dict) and _mapping_has_status_token(item) for item in mappings
    )


def _base_threshold_color(defaults: dict[str, Any]) -> str | None:
    steps = (defaults.get("thresholds") or {}).get("steps") or []
    if not steps or not isinstance(steps[0], dict):
        return None
    color = str(steps[0].get("color") or "").strip()
    if color.lower() in GREEN or color == "green":
        return color
    return None


def _stat_green_base(panel: dict[str, Any]) -> str | None:
    if panel.get("type") != "stat":
        return None
    defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
    mappings = defaults.get("mappings") or []
    if not mappings or not _mappings_look_like_text_status(mappings):
        return None
    return _base_threshold_color(defaults)


def _lint_thresholds(path: Path, panels: list[dict[str, Any]]) -> list[str]:
    return [
        (
            f"{path.name}: panel {panel.get('id')} text-stat base threshold "
            f"is green ({color})"
        )
        for panel in panels
        if (color := _stat_green_base(panel)) is not None
    ]


def _url_transport_findings(path_name: str, title: str, url: str) -> list[str]:
    findings: list[str] = []
    glued = f"/${{__data.fields.action_path}}{_AMP}"
    if glued in url or glued.replace(_AMP, _AMP_ENTITY) in url:
        findings.append(f"{path_name}: action_path glued with & ({title or url[:60]})")
    grafana_on_github = "github.com/" in url and (
        "var-" in url or "${__url_time_range}" in url or "${pipeline" in url
    )
    if grafana_on_github:
        findings.append(f"{path_name}: GitHub URL carries Grafana params ({url[:80]})")
    if title and "Provider Health" in title and "bioetl-overview-v2" in url:
        findings.append(
            f"{path_name}: link title {title!r} points at Overview — "
            "prefer Run Overview wording (F-25)"
        )
    return findings


def _view_panel_findings(
    path_name: str,
    title: str,
    url: str,
    *,
    uid: str,
    id_set: set[int],
    id_by_uid: dict[str, set[int]],
) -> list[str]:
    dest_uid, view_panel = parse_dashboard_view_panel(url)
    if dest_uid is None or view_panel is None or dest_uid.startswith("${"):
        return []
    findings: list[str] = []
    dest_ids = id_by_uid.get(dest_uid)
    missing_remote = dest_ids is not None and view_panel not in dest_ids
    missing_local = dest_uid == uid and view_panel not in id_set
    if missing_remote:
        findings.append(
            f"{path_name}: broken viewPanel={view_panel} on {dest_uid} "
            f"(title={title!r})"
        )
    if missing_local:
        findings.append(
            f"{path_name}: local viewPanel={view_panel} missing (title={title!r})"
        )
    return findings


def _lint_urls(
    path: Path,
    payload: dict[str, Any],
    *,
    uid: str,
    id_set: set[int],
    id_by_uid: dict[str, set[int]],
) -> list[str]:
    findings: list[str] = []
    for title, url in _iter_urls(payload):
        findings.extend(_url_transport_findings(path.name, title, url))
        findings.extend(
            _view_panel_findings(
                path.name,
                title,
                url,
                uid=uid,
                id_set=id_set,
                id_by_uid=id_by_uid,
            )
        )
    return findings


def _variable_reference_patterns(name: str) -> tuple[str, ...]:
    return (
        f"${name}",
        f"${{{name}",
        f"var-{name}",
        f'"repeat": "{name}"',
        f'"repeat":"{name}"',
    )


def _lint_unused_variables(path: Path, payload: dict[str, Any]) -> list[str]:
    """Phase-4: every templating variable must be referenced outside templating."""
    variables = (payload.get("templating") or {}).get("list") or []
    body = {key: value for key, value in payload.items() if key != "templating"}
    blob = json.dumps(body)
    findings: list[str] = []
    for var in variables:
        if not isinstance(var, dict):
            continue
        name = str(var.get("name") or "")
        if not name:
            continue
        if not any(pattern in blob for pattern in _variable_reference_patterns(name)):
            findings.append(f"{path.name}: unused template variable {name!r}")
    return findings


def _lint_dead_renames(path: Path, panels: list[dict[str, Any]]) -> list[str]:
    """Phase-4: renameByName keys must appear in the same organize indexByName."""
    findings: list[str] = []
    for panel in panels:
        for transform in panel.get("transformations") or []:
            if not isinstance(transform, dict) or transform.get("id") != "organize":
                continue
            options = transform.get("options") or {}
            index = options.get("indexByName")
            rename = options.get("renameByName")
            if not isinstance(index, dict) or not isinstance(rename, dict) or not index:
                continue
            dead = sorted(key for key in rename if key not in index)
            if dead:
                findings.append(
                    f"{path.name}: panel {panel.get('id')} dead renameByName {dead}"
                )
    return findings


_EXPECTED_REFRESH_INTERVALS = [
    "5s",
    "10s",
    "30s",
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "1d",
]


def _lint_timepicker(path: Path, payload: dict[str, Any]) -> list[str]:
    """Phase-4: shared timepicker.refresh_intervals across provisioned boards."""
    intervals = (payload.get("timepicker") or {}).get("refresh_intervals")
    if intervals == _EXPECTED_REFRESH_INTERVALS:
        return []
    return [
        f"{path.name}: timepicker.refresh_intervals must match shared Phase 4.4 list"
    ]


def lint_dashboard(path: Path, *, profile: str = "phase2") -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    uid = str(payload.get("uid") or UID_BY_FILE.get(path.name) or "")
    panels = _walk(payload.get("panels", []))
    id_set = _ids(panels)
    id_by_uid = {
        UID_BY_FILE[name]: _ids(
            _walk(
                json.loads((DASH_DIR / name).read_text(encoding="utf-8")).get(
                    "panels", []
                )
            )
        )
        for name in FILES
        if (DASH_DIR / name).exists()
    }
    findings: list[str] = []
    findings.extend(_lint_nav(path, panels))
    findings.extend(_lint_organize(path, panels))
    findings.extend(_lint_thresholds(path, panels))
    findings.extend(
        _lint_urls(path, payload, uid=uid, id_set=id_set, id_by_uid=id_by_uid)
    )
    if profile == "phase4":
        findings.extend(_lint_unused_variables(path, payload))
        findings.extend(_lint_dead_renames(path, panels))
        findings.extend(_lint_timepicker(path, payload))
    return findings


def lint_donor_jsonata() -> list[str]:
    """Validate Phase 2.5 donor JSONata bracket balance when the module loads."""
    from scripts.ops.observability.grafana.apply_phase25_srs_prr_budget import (
        _assert_donor_jsonata_balanced,
    )

    try:
        _assert_donor_jsonata_balanced()
    except ValueError as exc:
        return [str(exc)]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("phase2", "phase4"),
        default="phase4",
        help=(
            "phase2 = nav/links/index/thresholds; "
            "phase4 (default) adds unused vars, dead renames, shared timepicker"
        ),
    )
    args = parser.parse_args(argv)
    all_findings: list[str] = []
    all_findings.extend(lint_donor_jsonata())
    for name in FILES:
        path = DASH_DIR / name
        if not path.exists():
            all_findings.append(f"missing {name}")
            continue
        all_findings.extend(lint_dashboard(path, profile=args.profile))
    if all_findings:
        print(f"{args.profile} dashboard lint FAILED:")
        for item in all_findings:
            print(f"  - {item}")
        return 1
    print(f"{args.profile} dashboard lint OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
