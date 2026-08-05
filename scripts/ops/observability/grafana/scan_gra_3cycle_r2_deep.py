"""Deep residual scan for Grafana 3-cycle r2 beyond baseline contract checks."""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def walk(panels: list | None):
    for panel in panels or []:
        if panel.get("type") == "row":
            yield from walk(panel.get("panels"))
            continue
        yield panel
        yield from walk(panel.get("panels"))


def pquery(expr: str) -> list:
    q = urllib.parse.urlencode({"query": expr})
    with urllib.request.urlopen(
        f"http://127.0.0.1:9090/api/v1/query?{q}", timeout=30
    ) as resp:
        payload = json.loads(resp.read().decode())
    return payload.get("data", {}).get("result", [])


def main() -> None:
    iteration = sys.argv[1] if len(sys.argv) > 1 else "01"
    base = (
        ROOT
        / "reports"
        / "observability"
        / "grafana-3cycle-20260805-r2"
        / f"iteration-{iteration}"
    )
    dash_dir = ROOT / "grafana" / "dashboards"
    findings: list[dict] = []

    for path in sorted(dash_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        uid = data.get("uid")
        title_dash = data.get("title")
        templating = (data.get("templating") or {}).get("list") or []
        var_names = [v.get("name") for v in templating if v.get("name")]

        # dashboard-level links
        for link in data.get("links") or []:
            if not link.get("title"):
                findings.append(
                    {
                        "sev": "P3",
                        "kind": "dashboard_link_empty_title",
                        "uid": uid,
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

        for panel in walk(data.get("panels")):
            pid = panel.get("id")
            ptitle = str(panel.get("title") or "")
            ptype = panel.get("type")
            g = panel.get("gridPos") or {}
            x, y, w, h = g.get("x", 0), g.get("y", 0), g.get("w", 0), g.get("h", 0)

            if w == 0 or h == 0:
                findings.append(
                    {
                        "sev": "P1",
                        "kind": "zero_size_panel",
                        "uid": uid,
                        "id": pid,
                        "title": ptitle,
                        "gp": g,
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )
            if x + w > 24:
                findings.append(
                    {
                        "sev": "P1",
                        "kind": "grid_overflow",
                        "uid": uid,
                        "id": pid,
                        "title": ptitle,
                        "gp": g,
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

            defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
            steps = (defaults.get("thresholds") or {}).get("steps") or []
            for step in steps:
                color = str(step.get("color") or "").lower().replace(" ", "")
                if color in {"transparent", "rgba(0,0,0,0)"}:
                    findings.append(
                        {
                            "sev": "P1",
                            "kind": "transparent_threshold",
                            "uid": uid,
                            "id": pid,
                            "title": ptitle,
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
                                "id": pid,
                                "title": ptitle,
                                "detail": value,
                                "confidence": "FACT",
                                "evidence": "DASHBOARD_JSON",
                            }
                        )

            if ptype == "stat" and defaults.get("noValue") is None:
                findings.append(
                    {
                        "sev": "P2",
                        "kind": "stat_missing_noValue",
                        "uid": uid,
                        "id": pid,
                        "title": ptitle,
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

            # null → OK/green masking
            for mapping in defaults.get("mappings") or []:
                opts = mapping.get("options") or {}
                if mapping.get("type") == "special" and opts.get("match") == "null":
                    res = opts.get("result") or {}
                    text = str(res.get("text") or "").lower()
                    color = str(res.get("color") or "").lower()
                    if text in {"ok", "healthy", "pass", "success"} or color in {
                        "green",
                        "dark-green",
                    }:
                        findings.append(
                            {
                                "sev": "P1",
                                "kind": "null_maps_ok_green",
                                "uid": uid,
                                "id": pid,
                                "title": ptitle,
                                "detail": res,
                                "confidence": "FACT",
                                "evidence": "DASHBOARD_JSON",
                            }
                        )

            if ptype == "stat" and steps:
                c0 = str(steps[0].get("color") or "").lower()
                nv = defaults.get("noValue")
                if c0 in {"green", "dark-green", "semi-dark-green"} and str(nv) in {
                    "0",
                    "0.0",
                }:
                    # legitimate for counters with vector(0); flag only without or vector
                    exprs = [
                        t.get("expr", "")
                        for t in panel.get("targets") or []
                        if isinstance(t.get("expr"), str)
                    ]
                    if exprs and not any("or vector(0)" in e for e in exprs):
                        findings.append(
                            {
                                "sev": "P2",
                                "kind": "green_zero_without_vector0",
                                "uid": uid,
                                "id": pid,
                                "title": ptitle,
                                "confidence": "FACT",
                                "evidence": "DASHBOARD_JSON",
                            }
                        )

            if "Processed Records" in ptitle:
                for transform in panel.get("transformations") or []:
                    if transform.get("id") != "organize":
                        continue
                    exclude = (transform.get("options") or {}).get(
                        "excludeByName"
                    ) or {}
                    if not exclude.get("percintage"):
                        findings.append(
                            {
                                "sev": "P1",
                                "kind": "missing_percintage_exclude",
                                "uid": uid,
                                "id": pid,
                                "title": ptitle,
                                "confidence": "FACT",
                                "evidence": "DASHBOARD_JSON",
                            }
                        )

            for target in panel.get("targets") or []:
                if target.get("hide"):
                    continue
                expr = target.get("expr")
                if (
                    ptype not in ("text", "row", "news", "dashlist", "canvas")
                    and isinstance(expr, str)
                    and not expr.strip()
                ):
                    findings.append(
                        {
                            "sev": "P1",
                            "kind": "empty_expr",
                            "uid": uid,
                            "id": pid,
                            "title": ptitle,
                            "confidence": "FACT",
                            "evidence": "DASHBOARD_JSON",
                        }
                    )
                if isinstance(expr, str):
                    # high-cardinality label misuse (literal label, not variable filter)
                    if 'run_id="' in expr and "$run_id" not in expr:
                        findings.append(
                            {
                                "sev": "P0",
                                "kind": "hardcoded_run_id_label",
                                "uid": uid,
                                "id": pid,
                                "title": ptitle,
                                "expr": expr[:160],
                                "confidence": "FACT",
                                "evidence": "DASHBOARD_JSON",
                            }
                        )

            if not ptitle.strip() and ptype not in (None, "row"):
                findings.append(
                    {
                        "sev": "P2",
                        "kind": "empty_title",
                        "uid": uid,
                        "id": pid,
                        "type": ptype,
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

            # broken panel links (empty url)
            for link in panel.get("links") or []:
                if not str(link.get("url") or "").strip() and not link.get("dashboard"):
                    findings.append(
                        {
                            "sev": "P2",
                            "kind": "empty_panel_link",
                            "uid": uid,
                            "id": pid,
                            "title": ptitle,
                            "confidence": "FACT",
                            "evidence": "DASHBOARD_JSON",
                        }
                    )

        # required shell vars present for operator bus
        required = {"pipeline", "run_type", "run_id"}
        missing = required - set(var_names)
        if missing and uid not in ():  # all seven should have shell
            if uid.startswith("bioetl-"):
                findings.append(
                    {
                        "sev": "P1",
                        "kind": "missing_shell_vars",
                        "uid": uid,
                        "title": title_dash,
                        "missing": sorted(missing),
                        "confidence": "FACT",
                        "evidence": "DASHBOARD_JSON",
                    }
                )

    # live ops percintage
    live: dict = {}
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
        if "percintage" in keys:
            findings.append(
                {
                    "sev": "P2",
                    "kind": "live_percintage_field",
                    "evidence": "HTTP",
                    "confidence": "FACT",
                    "detail": "Ops HTTP still returns percintage (stale runtime vs source)",
                    "remediation": "rebuild/restart bioetl docker image OR strip field at gateway",
                }
            )
    except Exception as exc:  # noqa: BLE001
        findings.append(
            {
                "sev": "P2",
                "kind": "ops_http_error",
                "detail": str(exc),
                "confidence": "FACT",
                "evidence": "HTTP",
            }
        )

    for key, expr in {
        "l0_status": "count(bioetl_l0_status)",
        "next_action": "count(bioetl_l0_next_action_route)",
        "up": 'up{job="bioetl"}',
    }.items():
        results = pquery(expr)
        live[key] = [item.get("value", [None, None])[1] for item in results]

    # source-side percintage should be absent
    src_hits = []
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "percintage" in text:
            src_hits.append(str(path.relative_to(ROOT)))
    live["source_percintage_files"] = src_hits
    if src_hits:
        findings.append(
            {
                "sev": "P1",
                "kind": "source_percintage_present",
                "files": src_hits,
                "confidence": "FACT",
                "evidence": "SOURCE",
            }
        )

    # dashboard exclude still present
    overview = json.loads(
        (dash_dir / "bioetl-overview-v2.json").read_text(encoding="utf-8")
    )
    for panel in walk(overview.get("panels")):
        if "Processed Records" in str(panel.get("title") or ""):
            for transform in panel.get("transformations") or []:
                if transform.get("id") == "organize":
                    exclude = (transform.get("options") or {}).get(
                        "excludeByName"
                    ) or {}
                    live["overview_percintage_excluded"] = bool(
                        exclude.get("percintage")
                    )

    registry = {
        "iteration": int(iteration),
        "captured_at": datetime.now(UTC).isoformat(),
        "findings_count": len(findings),
        "findings": findings,
        "live": live,
        "note": "Deep scan: JSON contracts + live Ops + source percintage",
    }
    out = base / "inventory" / "findings-registry-deep.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print("findings", len(findings))
    for f in findings:
        print(f)
    print("live", json.dumps(live, indent=2))


if __name__ == "__main__":
    main()
