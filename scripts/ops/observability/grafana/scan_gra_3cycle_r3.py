"""Residual scanner for Grafana 3-cycle r3 closed-loop audits."""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tests"))

try:
    from integration.grafana_contract_specs import SUMMARY_ZERO_FALLBACK_EXPECTATIONS
except Exception:  # noqa: BLE001
    SUMMARY_ZERO_FALLBACK_EXPECTATIONS = {}


def walk(panels: list | None):
    for panel in panels or []:
        if panel.get("type") == "row":
            yield from walk(panel.get("panels"))
            continue
        yield panel
        yield from walk(panel.get("panels"))


def pquery(expr: str) -> list:
    q = urllib.parse.urlencode({"query": expr})
    with urllib.request.urlopen(f"http://127.0.0.1:9090/api/v1/query?{q}", timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    return payload.get("data", {}).get("result", [])


def resolve_ops_url(url: str) -> str:
    out = url
    for token, value in {
        "${pipeline}": "chembl_activity",
        "${run_type:csv}": "backfill",
        "${run_type}": "backfill",
        "${run_id}": "-",
        "${workflow}": "all",
        "${provider}": "chembl",
        "${stage}": "unknown",
    }.items():
        out = out.replace(token, value)
    return out


def greenish_pct(path: Path) -> float:
    try:
        from PIL import Image
    except ImportError:
        return -1.0
    image = Image.open(path).convert("RGB")
    width, height = image.size
    pixels = image.load()
    green = total = 0
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            r, g, b = pixels[x, y]
            total += 1
            if g > 140 and g > r + 20 and g > b + 20:
                green += 1
    return round(100 * green / total, 2) if total else 0.0


def scan(iteration_dir: Path) -> dict:
    findings: list[dict] = []
    dash_dir = ROOT / "grafana" / "dashboards"

    # JSON contract residual classes
    for path in sorted(dash_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        uid = data.get("uid")
        for panel in walk(data.get("panels")):
            title = str(panel.get("title") or "")
            panel_id = panel.get("id")
            panel_type = panel.get("type")
            g = panel.get("gridPos") or {}
            if (g.get("w") or 0) == 0 or (g.get("h") or 0) == 0:
                findings.append(
                    {
                        "sev": "P1",
                        "kind": "zero_size_panel",
                        "uid": uid,
                        "id": panel_id,
                        "title": title,
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )
            if (g.get("x") or 0) + (g.get("w") or 0) > 24:
                findings.append(
                    {
                        "sev": "P1",
                        "kind": "grid_overflow",
                        "uid": uid,
                        "id": panel_id,
                        "title": title,
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

            defaults = ((panel.get("fieldConfig") or {}).get("defaults") or {})
            steps = (defaults.get("thresholds") or {}).get("steps") or []
            for step in steps:
                color = str(step.get("color") or "").lower().replace(" ", "")
                if color in {"transparent", "rgba(0,0,0,0)"}:
                    findings.append(
                        {
                            "sev": "P1",
                            "kind": "transparent_threshold",
                            "uid": uid,
                            "id": panel_id,
                            "title": title,
                            "confidence": "FACT",
                            "evidence": "DASHBOARD_JSON",
                        }
                    )

            for override in (panel.get("fieldConfig") or {}).get("overrides") or []:
                for prop in override.get("properties") or []:
                    if prop.get("id") != "custom.cellOptions":
                        continue
                    value = prop.get("value") or {}
                    if (
                        isinstance(value, dict)
                        and value.get("type") == "color-text"
                        and "mode" in value
                    ):
                        findings.append(
                            {
                                "sev": "P1",
                                "kind": "invalid_color_text_mode",
                                "uid": uid,
                                "id": panel_id,
                                "title": title,
                                "confidence": "FACT",
                                "evidence": "DASHBOARD_JSON",
                            }
                        )

            if panel_type == "stat" and defaults.get("noValue") is None:
                findings.append(
                    {
                        "sev": "P2",
                        "kind": "stat_missing_noValue",
                        "uid": uid,
                        "id": panel_id,
                        "title": title,
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

            if "Processed Records" in title:
                for transform in panel.get("transformations") or []:
                    if transform.get("id") != "organize":
                        continue
                    exclude = (transform.get("options") or {}).get("excludeByName") or {}
                    if not exclude.get("percintage"):
                        findings.append(
                            {
                                "sev": "P1",
                                "kind": "missing_percintage_exclude",
                                "uid": uid,
                                "id": panel_id,
                                "title": title,
                                "confidence": "FACT",
                                "evidence": "DASHBOARD_JSON",
                            }
                        )

            for target in panel.get("targets") or []:
                if not isinstance(target, dict) or target.get("hide"):
                    continue
                expr = target.get("expr")
                if (
                    isinstance(expr, str)
                    and 'run_id="' in expr
                    and "$run_id" not in expr
                ):
                    findings.append(
                        {
                            "sev": "P0",
                            "kind": "hardcoded_run_id_label",
                            "uid": uid,
                            "id": panel_id,
                            "title": title,
                            "confidence": "FACT",
                            "evidence": "DASHBOARD_JSON",
                        }
                    )

            if not title.strip() and panel_type not in (None, "row"):
                findings.append(
                    {
                        "sev": "P2",
                        "kind": "empty_title",
                        "uid": uid,
                        "id": panel_id,
                        "type": panel_type,
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

            # first-screen non-collapsed long PromQL
            # (row collapsed state handled by top-level walk of nested panels only
            # for collapsed content inside row panels — nested under collapsed rows
            # still appear via walk of row.panels; mark y<18 as first-screen candidate)

    # first-screen open (not under collapsed row) expr length
    for path in sorted(dash_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        uid = data.get("uid")

        def walk_open(panels: list | None, collapsed: bool = False):
            for panel in panels or []:
                if panel.get("type") == "row":
                    yield from walk_open(
                        panel.get("panels"),
                        collapsed=bool(panel.get("collapsed")),
                    )
                    continue
                yield panel, collapsed
                yield from walk_open(panel.get("panels"), collapsed=collapsed)

        for panel, collapsed in walk_open(data.get("panels")):
            if collapsed:
                continue
            y = (panel.get("gridPos") or {}).get("y", 99)
            if y >= 18:
                continue
            for target in panel.get("targets") or []:
                if not isinstance(target, dict):
                    continue
                expr = target.get("expr") or ""
                if not isinstance(expr, str):
                    continue
                title = str(panel.get("title") or "")
                limit = 200
                if len(expr) > limit:
                    findings.append(
                        {
                            "sev": "P2",
                            "kind": "first_screen_long_expr",
                            "uid": uid,
                            "id": panel.get("id"),
                            "title": title,
                            "len": len(expr),
                            "limit": limit,
                            "confidence": "FACT",
                            "evidence": "DASHBOARD_JSON",
                        }
                    )

    for dash_name, expectations in SUMMARY_ZERO_FALLBACK_EXPECTATIONS.items():
        path = dash_dir / dash_name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        by_title = {
            panel.get("title"): panel
            for panel in walk(data.get("panels"))
            if panel.get("title")
        }
        for title, snippet in expectations.items():
            panel = by_title.get(title)
            if panel is None:
                findings.append(
                    {
                        "sev": "P1",
                        "kind": "missing_summary_panel",
                        "dash": dash_name,
                        "title": title,
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )
                continue
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets") or []
                if isinstance(target.get("expr"), str)
            ]
            if not any(snippet in expr for expr in expressions):
                findings.append(
                    {
                        "sev": "P1",
                        "kind": "missing_vector0",
                        "dash": dash_name,
                        "title": title,
                        "id": panel.get("id"),
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

    # Ops HTTP panel probes
    ops_bad: list[dict] = []
    for path in sorted(dash_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for panel in walk(data.get("panels")):
            for target in panel.get("targets") or []:
                if not isinstance(target, dict):
                    continue
                url = target.get("url")
                if not isinstance(url, str) or not url.startswith("/"):
                    continue
                full = "http://127.0.0.1:8000" + resolve_ops_url(url)
                try:
                    with urllib.request.urlopen(full, timeout=12) as resp:
                        status = resp.status
                except Exception as exc:  # noqa: BLE001
                    status = str(exc)
                if status not in (200, 204):
                    item = {
                        "sev": "P1",
                        "kind": "ops_http_error",
                        "uid": data.get("uid"),
                        "id": panel.get("id"),
                        "title": panel.get("title"),
                        "url": url,
                        "status": status,
                        "confidence": "FACT",
                        "evidence": "HTTP",
                    }
                    findings.append(item)
                    ops_bad.append(item)

    live: dict = {}
    for key, expr in {
        "l0_status": "count(bioetl_l0_status)",
        "next_action": "count(bioetl_l0_next_action_route)",
        "up": 'up{job="bioetl"}',
        "no_route": "count(bioetl_l0_next_action_no_route)",
    }.items():
        try:
            results = pquery(expr)
            live[key] = [item.get("value", [None, None])[1] for item in results]
        except Exception as exc:  # noqa: BLE001
            live[key] = f"ERR:{exc}"

    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:8000/ops/observability/processed-records"
            "?pipeline=chembl_activity&run_type=backfill&run_id=-",
            timeout=15,
        ) as resp:
            body = json.loads(resp.read().decode())
        rows = body.get("rows") or []
        keys: set[str] = set()
        for row in rows:
            keys |= set(row.keys())
        live["processed_keys"] = sorted(keys)
        if "percintage" in keys and "percentage" not in keys:
            findings.append(
                {
                    "sev": "P2",
                    "kind": "live_percintage_only",
                    "confidence": "FACT",
                    "evidence": "HTTP",
                }
            )
    except Exception as exc:  # noqa: BLE001
        findings.append(
            {
                "sev": "P2",
                "kind": "ops_processed_error",
                "detail": str(exc),
                "confidence": "FACT",
                "evidence": "HTTP",
            }
        )

    # timeseries missing maxDataPoints
    for path in sorted(dash_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for panel in walk(data.get("panels")):
            if panel.get("type") != "timeseries":
                continue
            if panel.get("maxDataPoints") is None:
                findings.append(
                    {
                        "sev": "P3",
                        "kind": "timeseries_missing_maxDataPoints",
                        "uid": data.get("uid"),
                        "id": panel.get("id"),
                        "title": panel.get("title"),
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

    greenish = {}
    dash_png = iteration_dir / "dashboards"
    if dash_png.exists():
        for png in sorted(dash_png.glob("*.png")):
            greenish[png.name] = greenish_pct(png)

    # exact PromQL dups within dashboard
    for path in sorted(dash_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        by_expr: dict[str, list] = {}
        for panel in walk(data.get("panels")):
            for target in panel.get("targets") or []:
                if not isinstance(target, dict):
                    continue
                expr = (target.get("expr") or "").strip()
                if not expr:
                    continue
                by_expr.setdefault(expr, []).append(
                    {"id": panel.get("id"), "title": panel.get("title")}
                )
        for expr, panels in by_expr.items():
            if len(panels) > 1:
                findings.append(
                    {
                        "sev": "P3",
                        "kind": "exact_promql_dup",
                        "uid": data.get("uid"),
                        "panels": panels,
                        "expr_len": len(expr),
                        "snippet": expr[:120],
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

    registry = {
        "iteration": int(iteration_dir.name.split("-")[-1]),
        "captured_at": datetime.now(UTC).isoformat(),
        "findings_count": len(findings),
        "findings": findings,
        "ops_bad_count": len(ops_bad),
        "live": live,
        "greenish_pct": greenish,
    }
    out = iteration_dir / "inventory" / "findings-registry.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return registry


def main() -> None:
    iteration = sys.argv[1] if len(sys.argv) > 1 else "01"
    base = (
        ROOT
        / "reports"
        / "observability"
        / "grafana-3cycle-20260805-r3"
        / f"iteration-{iteration}"
    )
    registry = scan(base)
    print("findings", registry["findings_count"])
    for finding in registry["findings"]:
        print(finding)
    print("live", json.dumps(registry["live"], indent=2))
    print("greenish", registry["greenish_pct"])


if __name__ == "__main__":
    main()
