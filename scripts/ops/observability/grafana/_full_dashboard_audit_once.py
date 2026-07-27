#!/usr/bin/env python3
"""One-shot evidence collector for Grafana/Prometheus dashboard audit (read-only)."""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "reports" / "quality" / "grafana-full-audit-2026-07-27"
DASH_DIR = ROOT / "grafana" / "dashboards"
INV_YAML = ROOT / "docs/03-guides/dashboards/contracts/dashboard-inventory.yaml"
PANEL_INV = ROOT / "docs/03-guides/dashboards/panel-contract-inventory.json"
METRICS_CAT = ROOT / "docs/04-reference/observability/metrics-catalog.md"
PROV = ROOT / "grafana/provisioning/dashboards/bioetl.yaml"
PROM_RULES_DIR = ROOT / "grafana/prometheus-rules"
DOC_PANELS = ROOT / "docs/03-guides/dashboards/panels"

METRIC_RE = re.compile(
    r"\b(bioetl_[a-zA-Z0-9_:]+|up|process_[a-zA-Z0-9_:]+|python_[a-zA-Z0-9_:]+)\b"
)
FORBIDDEN_LABELS = {
    "run_id",
    "manifest_id",
    "record_id",
    "payload_hash",
    "content_hash",
    "path",
    "url",
    "exception",
    "error_message",
    "traceback",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def walk_panels(node: Any, acc: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if acc is None:
        acc = []
    if not isinstance(node, dict):
        return acc
    if "type" in node and (
        "targets" in node
        or node.get("type")
        in {
            "row",
            "text",
            "dashlist",
            "news",
            "stat",
            "timeseries",
            "table",
            "bargauge",
            "heatmap",
            "histogram",
            "piechart",
            "gauge",
            "logs",
            "nodeGraph",
            "canvas",
            "state-timeline",
            "status-history",
            "geomap",
            "xychart",
        }
    ):
        acc.append(node)
    for child in node.get("panels") or []:
        walk_panels(child, acc)
    return acc


def extract_targets(panel: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for target in panel.get("targets") or []:
        if not isinstance(target, dict):
            continue
        expr = (
            target.get("expr")
            or target.get("query")
            or target.get("rawSql")
            or target.get("url")
            or ""
        )
        if not expr and "url_options" in target:
            expr = json.dumps(target.get("url_options") or {}, sort_keys=True)[:400]
        datasource = target.get("datasource")
        if isinstance(datasource, dict):
            ds_name = datasource.get("type") or datasource.get("uid") or datasource.get(
                "name"
            )
        else:
            ds_name = datasource
        out.append(
            {
                "refId": target.get("refId"),
                "expr": expr if isinstance(expr, str) else str(expr),
                "datasource": ds_name,
                "legendFormat": target.get("legendFormat"),
                "instant": target.get("instant"),
                "range": target.get("range"),
            }
        )
    return out


def panel_datasource(panel: dict[str, Any]) -> Any:
    datasource = panel.get("datasource")
    if isinstance(datasource, dict):
        return datasource.get("type") or datasource.get("uid") or datasource.get("name")
    return datasource


def classify_ds(ds: Any, expr: str) -> str:
    ds_s = str(ds or "")
    low = ds_s.lower()
    if "infinity" in low or "yesoreyeram" in low:
        return "BioETL Ops HTTP"
    if "loki" in low:
        return "Loki"
    if "tempo" in low or "jaeger" in low:
        return "Tempo"
    if "grafana" in low or ds_s == "-- Grafana --":
        return "Grafana"
    if "prometheus" in low or ds_s in {"", "None", "${datasource}"}:
        if any(token in expr for token in ("/api/", "manifest", "ledger", "checkpoint")):
            return "ControlPlane/HTTP-ish"
        return "Prometheus"
    if "bioetl" in low or "ops" in low:
        return "BioETL Ops HTTP"
    return ds_s or "unknown"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for name in (".env", ".env.local"):
        path = ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            env[key] = value
    return env


def http_get(url: str, auth: str | None = None, timeout: float = 8.0) -> tuple[int, str]:
    request = urllib.request.Request(url)
    if auth:
        request.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:800]
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    dashboards: list[dict[str, Any]] = []
    all_metrics: Counter[str] = Counter()
    panel_rows: list[dict[str, Any]] = []
    selector_rows: list[dict[str, Any]] = []
    nav_rows: list[dict[str, Any]] = []
    ds_boundary_rows: list[dict[str, Any]] = []
    forbidden_hits: list[dict[str, Any]] = []
    json_uids: set[str] = set()
    linked_uids: set[str] = set()

    for path in sorted(DASH_DIR.glob("*.json")):
        dashboard = load_json(path)
        uid = str(dashboard.get("uid") or "")
        json_uids.add(uid)
        panels: list[dict[str, Any]] = []
        for top in dashboard.get("panels") or []:
            walk_panels(top, panels)
        # de-dupe
        seen: set[tuple[Any, Any, Any]] = set()
        unique_panels: list[dict[str, Any]] = []
        for panel in panels:
            key = (panel.get("id"), panel.get("title"), panel.get("type"))
            if key in seen:
                continue
            seen.add(key)
            unique_panels.append(panel)

        variables: list[dict[str, Any]] = []
        for variable in (dashboard.get("templating") or {}).get("list") or []:
            query = variable.get("query")
            if isinstance(query, dict):
                query_s = json.dumps(query, sort_keys=True)
            else:
                query_s = query
            datasource = variable.get("datasource")
            if isinstance(datasource, dict):
                ds_name = datasource.get("type") or datasource.get("uid")
            else:
                ds_name = datasource
            current = variable.get("current")
            current_text = (
                current.get("text") if isinstance(current, dict) else current
            )
            item = {
                "name": variable.get("name"),
                "type": variable.get("type"),
                "label": variable.get("label"),
                "query": query_s,
                "definition": variable.get("definition"),
                "datasource": ds_name,
                "includeAll": variable.get("includeAll"),
                "multi": variable.get("multi"),
                "regex": variable.get("regex"),
                "current": current_text,
                "allValue": variable.get("allValue"),
                "refresh": variable.get("refresh"),
            }
            variables.append(item)
            selector_rows.append(
                {
                    "dashboard": uid,
                    "selector": item["name"],
                    "type": item["type"],
                    "query": item["query"],
                    "datasource": item["datasource"],
                    "includeAll": item["includeAll"],
                    "multi": item["multi"],
                    "regex": item["regex"],
                    "default": item["current"],
                    "allValue": item["allValue"],
                }
            )

        for link in dashboard.get("links") or []:
            target_uid = link.get("uid") or link.get("dashboardUid")
            if target_uid:
                linked_uids.add(str(target_uid))
            nav_rows.append(
                {
                    "dashboard": uid,
                    "kind": "dashboard_link",
                    "title": link.get("title"),
                    "type": link.get("type"),
                    "url": link.get("url"),
                    "uid": target_uid,
                    "keepTime": link.get("keepTime"),
                    "includeVars": link.get("includeVars"),
                    "tags": link.get("tags"),
                }
            )

        text = path.read_text(encoding="utf-8")
        for match in re.findall(r"d/(bioetl-[a-z0-9-]+)", text):
            linked_uids.add(match)
        for match in re.findall(r'"uid"\s*:\s*"(bioetl-[a-z0-9-]+)"', text):
            linked_uids.add(match)

        non_row = 0
        for panel in unique_panels:
            if panel.get("type") != "row":
                non_row += 1
            for link in panel.get("links") or []:
                nav_rows.append(
                    {
                        "dashboard": uid,
                        "kind": "panel_link",
                        "panel": panel.get("title"),
                        "panel_id": panel.get("id"),
                        "title": link.get("title"),
                        "url": link.get("url"),
                        "type": link.get("type"),
                    }
                )
            targets = extract_targets(panel)
            if not targets and panel.get("type") not in {"row", "text", "dashlist"}:
                panel_rows.append(
                    {
                        "dashboard": uid,
                        "panel_id": panel.get("id"),
                        "title": panel.get("title"),
                        "type": panel.get("type"),
                        "datasource": str(panel_datasource(panel) or ""),
                        "ds_class": classify_ds(panel_datasource(panel), ""),
                        "expr": "",
                        "metrics": [],
                        "unit": (
                            (panel.get("fieldConfig") or {})
                            .get("defaults", {})
                            .get("unit")
                        ),
                        "description": (panel.get("description") or "")[:200],
                    }
                )
            for target in targets:
                expr = target["expr"] or ""
                metrics = METRIC_RE.findall(expr)
                for metric in metrics:
                    all_metrics[metric] += 1
                for label in FORBIDDEN_LABELS:
                    if re.search(rf"\b{label}\s*=", expr) or re.search(
                        rf"by\s*\([^)]*\b{label}\b", expr
                    ):
                        forbidden_hits.append(
                            {
                                "dashboard": uid,
                                "panel": panel.get("title"),
                                "label": label,
                                "expr": expr[:300],
                            }
                        )
                ds_raw = target["datasource"] or panel_datasource(panel)
                ds_class = classify_ds(ds_raw, expr)
                ds_boundary_rows.append(
                    {
                        "dashboard": uid,
                        "panel_id": panel.get("id"),
                        "panel": panel.get("title"),
                        "datasource_raw": str(ds_raw or ""),
                        "classified": ds_class,
                        "expr_preview": expr[:220],
                    }
                )
                panel_rows.append(
                    {
                        "dashboard": uid,
                        "panel_id": panel.get("id"),
                        "title": panel.get("title"),
                        "type": panel.get("type"),
                        "datasource": str(ds_raw or ""),
                        "ds_class": ds_class,
                        "expr": expr,
                        "metrics": metrics,
                        "unit": (
                            (panel.get("fieldConfig") or {})
                            .get("defaults", {})
                            .get("unit")
                        ),
                        "description": (panel.get("description") or "")[:200],
                    }
                )

        dashboards.append(
            {
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "uid": uid,
                "title": dashboard.get("title"),
                "tags": dashboard.get("tags") or [],
                "refresh": dashboard.get("refresh"),
                "timezone": dashboard.get("timezone"),
                "panel_count": non_row,
                "variables": [item["name"] for item in variables],
                "variable_detail": variables,
                "version": dashboard.get("version"),
                "schemaVersion": dashboard.get("schemaVersion"),
                "links_count": len(dashboard.get("links") or []),
            }
        )

    inv = (
        yaml.safe_load(INV_YAML.read_text(encoding="utf-8"))
        if INV_YAML.exists()
        else {}
    )
    inv_uids: set[str] = set()
    if isinstance(inv, dict):
        for inventory_key in ("dashboards", "entries", "items"):
            inventory_entries = inv.get(inventory_key)
            if isinstance(inventory_entries, list):
                for entry in inventory_entries:
                    if isinstance(entry, dict):
                        inv_uids.add(
                            str(
                                entry.get("uid")
                                or entry.get("id")
                                or entry.get("dashboard_uid")
                                or ""
                            )
                        )
            if isinstance(inventory_entries, dict):
                for nested_key, nested_val in inventory_entries.items():
                    if isinstance(nested_val, dict):
                        inv_uids.add(
                            str(nested_val.get("uid") or nested_key)
                        )
                    else:
                        inv_uids.add(str(nested_key))
        # top-level uid maps
        for key, value in inv.items():
            if isinstance(value, dict) and (
                "uid" in value or "panels" in value or "title" in value
            ):
                inv_uids.add(str(value.get("uid") or key))

    doc_panel_uids = {
        path.stem[: -len("-panels")]
        if path.stem.endswith("-panels")
        else path.stem
        for path in DOC_PANELS.glob("bioetl-*.md")
    }

    panel_doc_uids: set[str] = set()
    if PANEL_INV.exists():
        panel_doc = load_json(PANEL_INV)
        if isinstance(panel_doc, dict):
            for key, value in panel_doc.items():
                if str(key).startswith("bioetl-"):
                    panel_doc_uids.add(str(key))
                if isinstance(value, dict):
                    for nested in value:
                        if str(nested).startswith("bioetl-"):
                            panel_doc_uids.add(str(nested))

    catalog_text = (
        METRICS_CAT.read_text(encoding="utf-8") if METRICS_CAT.exists() else ""
    )
    catalog_metrics = set(re.findall(r"bioetl_[a-zA-Z0-9_]+", catalog_text))

    code_metrics: set[str] = set()
    for path in (ROOT / "src/bioetl/infrastructure/observability").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        code_metrics |= set(re.findall(r"['\"](bioetl_[a-zA-Z0-9_]+)['\"]", text))
    for path in (ROOT / "src/bioetl").rglob("*.py"):
        # light scan for Counter/Histogram names
        if "bioetl_" not in path.read_text(encoding="utf-8", errors="replace")[:0]:
            pass
    # broader bounded scan
    for folder in (
        ROOT / "src/bioetl/infrastructure/observability",
        ROOT / "src/bioetl/domain/ports",
        ROOT / "src/bioetl/application/observability",
    ):
        if not folder.exists():
            continue
        for path in folder.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            code_metrics |= set(re.findall(r"['\"](bioetl_[a-zA-Z0-9_]+)['\"]", text))

    rule_metrics: set[str] = set()
    for path in PROM_RULES_DIR.glob("*.yml"):
        text = path.read_text(encoding="utf-8", errors="replace")
        rule_metrics |= set(re.findall(r"\b(bioetl_[a-zA-Z0-9_:]+)\b", text))

    # LIVE
    env = load_env()
    password = env.get("GF_SECURITY_ADMIN_PASSWORD") or env.get("GRAFANA_PASSWORD") or ""
    user = env.get("GRAFANA_USERNAME") or "admin"
    basic = (
        "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
        if password
        else None
    )
    live: dict[str, Any] = {}
    status, body = http_get("http://127.0.0.1:3000/api/health")
    live["grafana_health"] = {"status": status, "body": body[:200]}
    status, body = http_get("http://127.0.0.1:9090/-/ready")
    live["prometheus_ready"] = {"status": status, "body": body[:80]}
    status, body = http_get("http://127.0.0.1:9090/api/v1/targets")
    prom_targets: list[dict[str, Any]] = []
    if status == 200:
        payload = json.loads(body)
        for target in payload.get("data", {}).get("activeTargets", []):
            prom_targets.append(
                {
                    "job": target.get("labels", {}).get("job"),
                    "instance": target.get("labels", {}).get("instance"),
                    "health": target.get("health"),
                    "lastError": (target.get("lastError") or "")[:160],
                }
            )
    live["prom_targets"] = prom_targets

    status, body = http_get("http://127.0.0.1:9090/api/v1/label/__name__/values")
    live_metric_names: list[str] = []
    if status == 200:
        live_metric_names = json.loads(body).get("data") or []
    live["metric_name_count"] = len(live_metric_names)
    live_bioetl = [name for name in live_metric_names if name.startswith("bioetl_")]
    live["bioetl_metric_count"] = len(live_bioetl)

    label_values: dict[str, Any] = {}
    for label in (
        "pipeline",
        "workflow",
        "run_type",
        "provider",
        "stage",
        "entity",
        "job",
    ):
        status, body = http_get(f"http://127.0.0.1:9090/api/v1/label/{label}/values")
        if status == 200:
            label_values[label] = json.loads(body).get("data") or []
        else:
            label_values[label] = {"error": status, "body": body[:120]}
    live["label_values"] = label_values

    sample_queries = {
        "up_bioetl": 'up{job="bioetl"}',
        "pipeline_runs": "sum(bioetl_pipeline_runs_total) or vector(0)",
        "stage_records": "sum(bioetl_stage_records_total) or vector(0)",
        "http_requests": "sum(bioetl_http_requests_total) or vector(0)",
        "dq_failures": "sum(bioetl_dq_validation_failures_total) or vector(0)",
        "workflow_runs": "sum(bioetl_workflow_runs_total) or vector(0)",
        "process_cpu": 'rate(process_cpu_seconds_total{job="bioetl"}[5m]) or vector(0)',
    }
    sample_results: dict[str, Any] = {}
    for name, query in sample_queries.items():
        status, body = http_get(
            "http://127.0.0.1:9090/api/v1/query?"
            + urllib.parse.urlencode({"query": query})
        )
        if status == 200:
            result = json.loads(body).get("data", {}).get("result", [])
            sample_results[name] = {
                "status": "ok",
                "series": len(result),
                "value": result[0]["value"][1] if result else None,
            }
        else:
            sample_results[name] = {
                "status": "error",
                "http": status,
                "body": body[:200],
            }
    live["sample_queries"] = sample_results

    if basic:
        status, body = http_get(
            "http://127.0.0.1:3000/api/search?type=dash-db", auth=basic
        )
        if status == 200:
            live["grafana_dashboards"] = [
                {
                    "uid": item.get("uid"),
                    "title": item.get("title"),
                    "url": item.get("url"),
                }
                for item in json.loads(body)
            ]
        else:
            live["grafana_dashboards_error"] = {"status": status, "body": body[:200]}
        status, body = http_get("http://127.0.0.1:3000/api/datasources", auth=basic)
        if status == 200:
            live["grafana_datasources"] = [
                {
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "url": item.get("url"),
                    "uid": item.get("uid"),
                }
                for item in json.loads(body)
            ]
        else:
            live["grafana_datasources_error"] = {"status": status, "body": body[:200]}

    status, body = http_get("http://127.0.0.1:8000/metrics")
    live["bioetl_metrics_endpoint"] = {
        "status": status,
        "bytes": len(body) if status == 200 else 0,
    }
    exposed: set[str] = set()
    if status == 200:
        exposed = set(re.findall(r"^(bioetl_[a-zA-Z0-9_]+)", body, flags=re.M))
        live["bioetl_exposed_metrics"] = sorted(exposed)
        live["bioetl_exposed_count"] = len(exposed)

    dash_metrics = set(all_metrics)
    metric_matrix: list[dict[str, Any]] = []
    universe = (
        dash_metrics
        | code_metrics
        | set(live_bioetl)
        | catalog_metrics
        | set(exposed)
        | rule_metrics
    )
    for metric in sorted(universe):
        if not str(metric).startswith("bioetl_"):
            continue
        metric_matrix.append(
            {
                "metric": metric,
                "in_dashboard_queries": metric in dash_metrics,
                "dashboard_refs": all_metrics.get(metric, 0),
                "in_code_strings": metric in code_metrics,
                "in_catalog_docs": metric in catalog_metrics,
                "in_prometheus_live": metric in set(live_metric_names),
                "in_rules": metric in rule_metrics,
                "in_bioetl_scrape": metric in exposed,
            }
        )

    missing_linked = sorted(linked_uids - json_uids)
    docs_gap = sorted(json_uids - doc_panel_uids)
    docs_orphan = sorted(doc_panel_uids - json_uids)

    summary = {
        "dashboards_json": len(dashboards),
        "panel_target_rows": len(panel_rows),
        "unique_panel_ids": len(
            {(row["dashboard"], row["panel_id"]) for row in panel_rows}
        ),
        "selectors": len(selector_rows),
        "nav_links": len(nav_rows),
        "metrics_in_queries": len([m for m in dash_metrics if m.startswith("bioetl_")]),
        "metrics_code": len(code_metrics),
        "metrics_live_bioetl": len(live_bioetl),
        "metrics_exposed_scrape": len(exposed),
        "forbidden_label_hits": len(forbidden_hits),
        "missing_linked_dashboards": missing_linked,
        "json_without_panel_docs": docs_gap,
        "docs_without_json": docs_orphan,
        "ds_class_counts": dict(Counter(row["classified"] for row in ds_boundary_rows)),
    }

    payload = {
        "summary": summary,
        "dashboards": dashboards,
        "panel_rows": panel_rows,
        "selector_rows": selector_rows,
        "nav_rows": nav_rows,
        "ds_boundary_rows": ds_boundary_rows,
        "forbidden_hits": forbidden_hits,
        "metric_matrix": metric_matrix,
        "live": live,
        "inventory_contract_uids": sorted(uid for uid in inv_uids if uid),
        "doc_panel_uids": sorted(doc_panel_uids),
        "panel_doc_uids": sorted(panel_doc_uids),
        "provisioning": PROV.read_text(encoding="utf-8") if PROV.exists() else None,
        "inventory_top_keys": list(inv.keys()) if isinstance(inv, dict) else [],
    }
    (OUT / "full-audit.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines = [
        "# Grafana Full Audit Evidence Snapshot",
        "generated: 2026-07-27",
        "",
        "## Summary",
    ]
    for summary_key, summary_value in summary.items():
        lines.append(f"- **{summary_key}**: `{summary_value}`")
    lines.extend(
        [
            "",
            "## Dashboard Inventory Matrix",
            "| Dashboard | UID | JSON | Panel docs | Panels | Variables | Broken nav UIDs | Status |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for dashboard in dashboards:
        text = (ROOT / dashboard["file"]).read_text(encoding="utf-8")
        referenced = set(re.findall(r"d/(bioetl-[a-z0-9-]+)", text))
        broken = sorted(referenced - json_uids)
        docs_ok = dashboard["uid"] in doc_panel_uids
        if broken:
            dashboard_status = "NAV_DRIFT"
        elif not docs_ok:
            dashboard_status = "DOCS_GAP"
        else:
            dashboard_status = "SHIPPED"
        lines.append(
            "| {title} | `{uid}` | `{file}` | {docs} | {panels} | {vars} | {broken} | {status} |".format(
                title=dashboard["title"],
                uid=dashboard["uid"],
                file=dashboard["file"],
                docs="Y" if docs_ok else "N",
                panels=dashboard["panel_count"],
                vars=", ".join(dashboard["variables"]),
                broken=", ".join(broken) or "—",
                status=dashboard_status,
            )
        )

    used_not_live = [
        row
        for row in metric_matrix
        if row["in_dashboard_queries"] and not row["in_prometheus_live"]
    ]
    live_not_used = [
        row
        for row in metric_matrix
        if row["in_prometheus_live"] and not row["in_dashboard_queries"]
    ]
    lines.extend(
        [
            "",
            "## Live",
            f"- grafana: `{live.get('grafana_health')}`",
            f"- prometheus: `{live.get('prometheus_ready')}`",
            f"- targets: `{live.get('prom_targets')}`",
            f"- bioetl series in Prometheus: `{live.get('bioetl_metric_count')}`",
            f"- scrape :8000/metrics bioetl_*: `{live.get('bioetl_exposed_count')}`",
            f"- label values: `{json.dumps(live.get('label_values'), ensure_ascii=False)}`",
            f"- sample queries: `{json.dumps(live.get('sample_queries'), ensure_ascii=False)}`",
            "",
            "## Metric coverage gaps",
            f"- dashboard-used missing in live Prometheus: **{len(used_not_live)}**",
            f"- live Prometheus bioetl_* unused by dashboards: **{len(live_not_used)}**",
            "### Used-by-dashboard but not live (sample)",
        ]
    )
    for row in used_not_live[:50]:
        lines.append(
            f"- `{row['metric']}` refs={row['dashboard_refs']} code={row['in_code_strings']} catalog={row['in_catalog_docs']} scrape={row['in_bioetl_scrape']}"
        )
    lines.append("### Live but unused by dashboards (sample)")
    for row in live_not_used[:50]:
        lines.append(f"- `{row['metric']}`")

    if forbidden_hits:
        lines.extend(["", "## Forbidden label hits"])
        for hit in forbidden_hits[:30]:
            lines.append(f"- {hit}")

    (OUT / "EVIDENCE_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
