#!/usr/bin/env python3
"""Scalar information-density survey/gate for shipped Grafana dashboards.

Implements ``DASH-DENSITY-002`` (see
``docs/01-requirements/DASHBOARD_REQUIREMENTS.md``): information density of a
panel group, measured over **scalar** panels only, must exceed the first-screen
scalar density of the same dashboard.

Density (scalar-only)::

    rho(surface) = sum(values) / sum(width * height)   over stat/gauge/bargauge

`timeseries`, `table`, `text`, `row` are intentionally excluded (their value
count is runtime/interpretation dependent). A single reduced stat/gauge counts
one value; a multi-value scalar (``reduceOptions.values = true``) counts its
non-hidden targets.

Report-only by default; ``--check`` exits non-zero for groups (with >=1 scalar)
whose density does not exceed the first-screen density, minus an optional
governed allowlist. The compute helpers are pure and import-safe for tests.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

SCALAR_TYPES = frozenset({"stat", "gauge", "bargauge"})
FIRST_WINDOW_Y = 18
DEFAULT_DASHBOARD_DIR = Path("grafana/dashboards")
DEFAULT_OUT_JSON = Path("reports/quality/dashboard-scalar-density.json")
DEFAULT_OUT_MD = Path("reports/quality/dashboard-scalar-density.md")


def panel_area(panel: dict[str, Any]) -> int:
    grid = panel.get("gridPos")
    if not isinstance(grid, dict):
        return 0
    return int(grid.get("w", 0)) * int(grid.get("h", 0))


def panel_value_count(panel: dict[str, Any]) -> int:
    """One value per reduced scalar; multi-value scalars count non-hidden targets."""
    options = panel.get("options")
    reduce_options = options.get("reduceOptions") if isinstance(options, dict) else None
    if isinstance(reduce_options, dict) and reduce_options.get("values") is True:
        targets = panel.get("targets") or []
        live = [
            target
            for target in targets
            if isinstance(target, dict) and target.get("hide") is not True
        ]
        return max(len(live), 1)
    return 1


def scalar_panels(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        panel
        for panel in panels
        if isinstance(panel, dict) and panel.get("type") in SCALAR_TYPES
    ]


def scalar_density(panels: list[dict[str, Any]]) -> float | None:
    """Return sum(values)/sum(area) over scalar panels, or None when undefined."""
    scal = scalar_panels(panels)
    area = sum(panel_area(panel) for panel in scal)
    if not scal or area <= 0:
        return None
    return sum(panel_value_count(panel) for panel in scal) / area


def first_screen_scalar_panels(dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for panel in dashboard.get("panels") or []:
        if not isinstance(panel, dict) or panel.get("type") == "row":
            continue
        y = (panel.get("gridPos") or {}).get("y", 999)
        if (
            isinstance(y, int)
            and y < FIRST_WINDOW_Y
            and panel.get("type") in SCALAR_TYPES
        ):
            out.append(panel)
    return out


def survey_dashboard(dashboard: dict[str, Any]) -> dict[str, Any]:
    first_screen = first_screen_scalar_panels(dashboard)
    first_density = scalar_density(first_screen)
    groups: list[dict[str, Any]] = []
    for panel in dashboard.get("panels") or []:
        if not isinstance(panel, dict) or panel.get("type") != "row":
            continue
        children = scalar_panels(panel.get("panels") or [])
        density = scalar_density(children)
        passes: bool | None
        if density is None:
            passes = None  # group has no scalar panels -> exempt (N/A)
        elif first_density is None:
            passes = None  # first screen has no scalars -> rule not applicable
        else:
            passes = density > first_density
        groups.append(
            {
                "row_id": panel.get("id"),
                "row_title": panel.get("title"),
                "scalar_count": len(children),
                "scalar_area": sum(panel_area(child) for child in children),
                "density": density,
                "passes": passes,
            }
        )
    return {
        "uid": dashboard.get("uid"),
        "first_screen_scalar_count": len(first_screen),
        "first_screen_density": first_density,
        "groups": groups,
    }


def _atomic_write(path: Path, payload: str) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")  # NOSONAR -- suffix-only sibling
    os.replace(tmp, path)


def _load_allowlist(path: Path | None) -> set[tuple[str, Any]]:
    if path is None or not path.exists():
        return set()
    import yaml  # local import keeps the module import-light for pure tests

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = payload.get("scalar_density_exceptions", {}).get("entries", [])
    allow: set[tuple[str, Any]] = set()
    for entry in entries:
        if isinstance(entry, dict):
            allow.add((str(entry.get("uid")), entry.get("row_id")))
    return allow


def survey_repo(dashboard_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(dashboard_dir.glob("*.json")):
        dashboard = json.loads(path.read_text(encoding="utf-8-sig"))
        result = survey_dashboard(dashboard)
        result["file"] = path.name
        results.append(result)
    return results


def _render_markdown(results: list[dict[str, Any]]) -> str:
    lines = ["# Dashboard scalar information density (DASH-DENSITY-002)", ""]
    lines.append("rho = sum(values)/sum(w*h) over stat/gauge/bargauge only.")
    lines.append("")
    lines.append("| dashboard | first-screen rho | group | group rho | passes |")
    lines.append("| --- | ---: | --- | ---: | --- |")
    for result in results:
        fs = result["first_screen_density"]
        fs_str = f"{fs:.4f}" if isinstance(fs, float) else "n/a"
        for group in result["groups"]:
            gd = group["density"]
            gd_str = f"{gd:.4f}" if isinstance(gd, float) else "n/a"
            verdict = {True: "PASS", False: "FAIL", None: "n/a"}[group["passes"]]
            lines.append(
                f"| {result['uid']} | {fs_str} | {group['row_title']} "
                f"| {gd_str} | {verdict} |"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--dashboard-dir", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--allowlist", type=Path, default=None)
    parser.add_argument("--check", action="store_true", help="exit 1 on FAIL groups")
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    args = parser.parse_args(argv)

    dashboard_dir = args.dashboard_dir or (args.repo_root / DEFAULT_DASHBOARD_DIR)
    results = survey_repo(dashboard_dir)
    allow = _load_allowlist(args.allowlist)

    _atomic_write(
        args.out_json, json.dumps(results, indent=2, ensure_ascii=False) + "\n"
    )
    _atomic_write(args.out_md, _render_markdown(results))

    failures = [
        (result["uid"], group["row_title"])
        for result in results
        for group in result["groups"]
        if group["passes"] is False
        and (str(result["uid"]), group["row_id"]) not in allow
    ]
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for result in results:
            print(f"{result['uid']}: first-screen rho={result['first_screen_density']}")
            for group in result["groups"]:
                print(
                    f"  [{ {True: 'PASS', False: 'FAIL', None: 'n/a'}[group['passes']] }] "
                    f"{group['row_title']} rho={group['density']} "
                    f"(scalars={group['scalar_count']})"
                )
    if args.check and failures:
        print(f"\nDASH-DENSITY-002 violations (non-allowlisted): {len(failures)}")
        for uid, title in failures:
            print(f"  - {uid} :: {title}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
