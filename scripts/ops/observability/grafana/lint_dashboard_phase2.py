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
_NAV_CHIP_TITLES = (
    "Run Explorer",
    "Replay Readiness",
    "Run Overview",
    "Data Quality",
    "6. Incident Workspace",
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
    result: set[int] = set()
    for panel in panels:
        panel_id = panel.get("id")
        if isinstance(panel_id, int):
            result.add(panel_id)
    return result


def _iter_urls(value: Any) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        title = str(value.get("title") or "")
        url = value.get("url")
        if isinstance(url, str) and url:
            found.append((title, url))
        for item in value.values():
            found.extend(_iter_urls(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_iter_urls(item))
    elif isinstance(value, str) and ("href=" in value or "/d/" in value):
        for match in re.finditer(r'href="([^"]+)"', value):
            found.append(("", match.group(1).replace("&amp;", "&")))
    return found


def parse_dashboard_view_panel(url: str) -> tuple[str | None, int | None]:
    """Extract ``/d/{uid}/…`` destination uid and ``viewPanel`` from any query position."""
    cleaned = url.replace("&amp;", "&")
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
    fallback = re.search(r"(?:^|[&])viewPanel=(\d+)", parts.query)
    if fallback:
        return dest_uid, int(fallback.group(1))
    return dest_uid, None


def _lint_nav(path: Path, panels: list[dict[str, Any]]) -> list[str]:
    findings: list[str] = []
    nav = next((p for p in panels if p.get("id") == 1000), None)
    if nav is None:
        return [f"{path.name}: missing navigation panel id=1000"]
    content = str((nav.get("options") or {}).get("content") or "")
    if "bioetl-nav" not in content:
        findings.append(f"{path.name}: panel 1000 missing bioetl-nav markup")
    chip_count = content.count("19.5%")
    if chip_count < 5:
        findings.append(
            f"{path.name}: panel 1000 expected five 19.5% chips, found {chip_count}"
        )
    if "16.5%" in content:
        findings.append(f"{path.name}: panel 1000 still uses legacy 16.5% chip width")
    if "<span" not in content or "bioetl-nav-current" not in content:
        findings.append(
            f"{path.name}: panel 1000 current chip must be "
            '<span class="bioetl-nav-current">'
        )
    if re.search(r'<a[^>]*class="[^"]*bioetl-nav-current', content):
        findings.append(f"{path.name}: panel 1000 current chip must not be an <a>")
    for title in _NAV_CHIP_TITLES:
        if title not in content:
            findings.append(f"{path.name}: panel 1000 missing chip {title!r}")
    return findings


def _lint_organize(path: Path, panels: list[dict[str, Any]]) -> list[str]:
    findings: list[str] = []
    for panel in panels:
        for transform in panel.get("transformations") or []:
            if not isinstance(transform, dict) or transform.get("id") != "organize":
                continue
            index = (transform.get("options") or {}).get("indexByName") or {}
            if not isinstance(index, dict):
                continue
            seen: dict[Any, list[str]] = {}
            for name, position in index.items():
                seen.setdefault(position, []).append(str(name))
            for position, names in seen.items():
                if len(names) > 1:
                    findings.append(
                        f"{path.name}: panel {panel.get('id')} indexByName "
                        f"collision at {position}: {names}"
                    )
    return findings


def _mappings_look_like_text_status(mappings: list[Any]) -> bool:
    """True when mappings encode OK/WARN/CRIT-style labels (not numeric counts)."""
    status_tokens = ("OK", "WARN", "CRIT", "ERROR", "UNKNOWN", "SELECT RUN", "INCOMPLETE")
    for item in mappings:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        options = item.get("options") or {}
        if kind == "regex":
            pattern = str(options.get("pattern") or "")
            if any(token in pattern for token in status_tokens):
                return True
        if kind == "value" and isinstance(options, dict):
            for key in options:
                if any(token in str(key) for token in status_tokens):
                    return True
                if not str(key).isdigit():
                    return True
    return False


def _lint_thresholds(path: Path, panels: list[dict[str, Any]]) -> list[str]:
    findings: list[str] = []
    for panel in panels:
        if panel.get("type") != "stat":
            continue
        defaults = ((panel.get("fieldConfig") or {}).get("defaults") or {})
        mappings = defaults.get("mappings") or []
        if not mappings or not _mappings_look_like_text_status(mappings):
            continue  # numeric gauges / digit value maps may use green
        steps = (defaults.get("thresholds") or {}).get("steps") or []
        if not steps:
            continue
        base = steps[0] if isinstance(steps[0], dict) else {}
        color = str(base.get("color") or "").strip()
        if color.lower() in GREEN or color == "green":
            findings.append(
                f"{path.name}: panel {panel.get('id')} text-stat base threshold "
                f"is green ({color})"
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
        if "/${__data.fields.action_path}&" in url or "/${__data.fields.action_path}&amp;" in url:
            findings.append(f"{path.name}: action_path glued with & ({title or url[:60]})")
        if "github.com/" in url and (
            "var-" in url or "${__url_time_range}" in url or "${pipeline" in url
        ):
            findings.append(f"{path.name}: GitHub URL carries Grafana params ({url[:80]})")
        dest_uid, view_panel = parse_dashboard_view_panel(url)
        if dest_uid is not None and view_panel is not None:
            if dest_uid.startswith("${"):
                continue
            dest_ids = id_by_uid.get(dest_uid)
            if dest_ids is not None and view_panel not in dest_ids:
                findings.append(
                    f"{path.name}: broken viewPanel={view_panel} on {dest_uid} "
                    f"(title={title!r})"
                )
            if dest_uid == uid and view_panel not in id_set:
                findings.append(
                    f"{path.name}: local viewPanel={view_panel} missing (title={title!r})"
                )
        if title and "Provider Health" in title and "bioetl-overview-v2" in url:
            findings.append(
                f"{path.name}: link title {title!r} points at Overview — "
                "prefer Run Overview wording (F-25)"
            )
    return findings


def lint_dashboard(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    uid = str(payload.get("uid") or UID_BY_FILE.get(path.name) or "")
    panels = _walk(payload.get("panels", []))
    id_set = _ids(panels)
    id_by_uid = {
        UID_BY_FILE[name]: _ids(
            _walk(json.loads((DASH_DIR / name).read_text(encoding="utf-8")).get("panels", []))
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
    return findings


def lint_donor_jsonata() -> list[str]:
    """Validate Phase 2.5 donor JSONata bracket balance when the module loads."""
    try:
        from scripts.ops.observability.grafana.apply_phase25_srs_prr_budget import (
            _assert_donor_jsonata_balanced,
        )
    except Exception as exc:  # pragma: no cover - import surface only
        return [f"phase25 donor import failed: {exc}"]
    try:
        _assert_donor_jsonata_balanced()
    except SystemExit as exc:
        return [str(exc)]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    all_findings: list[str] = []
    all_findings.extend(lint_donor_jsonata())
    for name in FILES:
        path = DASH_DIR / name
        if not path.exists():
            all_findings.append(f"missing {name}")
            continue
        all_findings.extend(lint_dashboard(path))
    if all_findings:
        print("phase-2 dashboard lint FAILED:")
        for item in all_findings:
            print(f"  - {item}")
        return 1
    print("phase-2 dashboard lint OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
