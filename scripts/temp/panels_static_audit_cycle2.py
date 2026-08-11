#!/usr/bin/env python3
"""Static panels-contour audit for shipped Grafana dashboards (MONITORING=false)."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.engineering.qa import report_dashboard_panel_audit_matrix as matrix
from tests.integration._grafana_test_support import (
    get_all_valid_metric_names,
    get_dashboard_panels,
    load_dashboard,
)

DASHBOARD_DIR = ROOT / "grafana" / "dashboards"
SCOPE_UIDS = {
    "bioetl-control-plane-v1",
    "bioetl-overview-v2",
    "bioetl-runtime",
    "bioetl-provider-health-v2",
    "bioetl-dq-v2",
    "bioetl-incident-v1",
    "bioetl-run-explorer-v1",
}

NON_QUERY_TYPES = {
    "row",
    "text",
    "news",
    "dashlist",
    "alertlist",
    "annolist",
    "gettingstarted",
}

PROMQL_KEYWORDS = {
    "sum",
    "avg",
    "min",
    "max",
    "count",
    "rate",
    "irate",
    "increase",
    "by",
    "without",
    "group_left",
    "group_right",
    "offset",
    "and",
    "or",
    "unless",
    "on",
    "ignoring",
    "group",
    "bool",
    "vector",
    "scalar",
    "label_replace",
    "label_join",
    "clamp_max",
    "clamp_min",
    "abs",
    "sqrt",
    "exp",
    "ln",
    "log2",
    "log10",
    "histogram_quantile",
    "topk",
    "bottomk",
    "quantile",
    "absent",
    "absent_over_time",
    "last_over_time",
    "max_over_time",
    "min_over_time",
    "avg_over_time",
    "sum_over_time",
    "count_over_time",
    "stddev_over_time",
    "stdvar_over_time",
    "quantile_over_time",
    "changes",
    "resets",
    "delta",
    "idelta",
    "deriv",
    "predict_linear",
    "time",
    "timestamp",
    "sort",
    "sort_desc",
    "floor",
    "ceil",
    "round",
    "clamp",
    "sgn",
    "day_of_month",
    "day_of_week",
    "days_in_month",
    "hour",
    "minute",
    "month",
    "year",
    "pi",
    "inf",
    "nan",
    "true",
    "false",
}

SELECTOR_RE = re.compile(r"([a-zA-Z_:][a-zA-Z0-9_:]*)\{")


def _ds_kind(panel: dict) -> str:
    return matrix._datasource_kind(panel)


def _exprs(panel: dict) -> list[str]:
    return matrix._panel_exprs(panel)


def _extract_metrics(expr: str) -> list[str]:
    found: list[str] = []
    for m in SELECTOR_RE.finditer(expr):
        name = m.group(1)
        if name not in PROMQL_KEYWORDS and not name.startswith("$"):
            found.append(name)
    for m in re.finditer(r"\b([a-zA-Z_:][a-zA-Z0-9_:]*)\b", expr):
        name = m.group(1)
        if name in PROMQL_KEYWORDS or name.startswith("$"):
            continue
        if name.startswith("bioetl_") or name in {"ALERTS", "up"}:
            if name not in found:
                found.append(name)
    return found


def _target_has_query(target: dict) -> bool:
    for key in ("expr", "url", "query", "rawSql", "instantQuery", "source"):
        val = target.get(key)
        if isinstance(val, str) and val.strip():
            return True
    for key in ("columns", "root_selector", "parser", "format"):
        if target.get(key):
            return True
    # infinity datasource often nests under url/method
    if target.get("method") or target.get("type") == "json":
        if target.get("url") or target.get("url_options"):
            return True
    url_options = target.get("url_options")
    if isinstance(url_options, dict) and any(url_options.values()):
        return True
    return False


def analyze(out_dir: Path) -> dict:
    valid_metrics = get_all_valid_metric_names()
    panel_rows: list[dict] = []
    findings: list[dict] = []
    checks: list[dict] = []
    inventory: list[dict] = []
    defect_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    unknown_metric_hits: list[dict] = []
    empty_query_hits: list[dict] = []
    vector0_status_hits: list[dict] = []
    duplicate_ids: list[dict] = []

    total_panels = 0
    queryable_panels = 0
    row_panels = 0
    text_panels = 0
    prom_panels = 0
    http_panels = 0

    for path in sorted(DASHBOARD_DIR.glob("*.json")):
        if path.name.endswith(".backup"):
            continue
        payload = load_dashboard(path)
        uid = str(payload.get("uid") or path.stem)
        if uid not in SCOPE_UIDS:
            continue
        title = str(payload.get("title") or "")
        panels = get_dashboard_panels(payload)
        ds_set: set[str] = set()
        id_seen: set[str] = set()

        for panel in panels:
            total_panels += 1
            pid = str(panel.get("id", ""))
            ptype = str(panel.get("type") or "")
            ptitle = str(panel.get("title") or "")
            dsk = _ds_kind(panel)
            exprs = _exprs(panel)
            targets = (
                panel.get("targets") if isinstance(panel.get("targets"), list) else []
            )

            if pid in id_seen:
                duplicate_ids.append(
                    {"dashboard_uid": uid, "panel_id": pid, "title": ptitle}
                )
            id_seen.add(pid)

            if dsk != "unknown":
                ds_set.add(dsk)
            if ptype == "row":
                row_panels += 1
            elif ptype == "text":
                text_panels += 1
            if dsk == "prometheus":
                prom_panels += 1
            elif dsk == "http":
                http_panels += 1

            verdict = "OK"
            defect_class = ""
            evidence_bits: list[str] = []

            if ptype in NON_QUERY_TYPES:
                if ptype == "row":
                    verdict = "OK"
                    evidence_bits.append(f"type=row collapsed={panel.get('collapsed')}")
                elif ptype == "text":
                    content = ""
                    opts = panel.get("options") or {}
                    if isinstance(opts, dict):
                        content = str(opts.get("content") or "")
                    if not content.strip():
                        verdict = "Defect"
                        defect_class = "Dashboard query defect"
                        evidence_bits.append("text panel has empty options.content")
                        empty_query_hits.append(
                            {
                                "dashboard_uid": uid,
                                "panel_id": pid,
                                "title": ptitle,
                                "reason": "empty text content",
                            }
                        )
                    else:
                        verdict = "OK"
                        evidence_bits.append(f"text content_len={len(content)}")
                else:
                    verdict = "OK"
                    evidence_bits.append(f"non-query type={ptype}")
            else:
                queryable_panels += 1
                has_any_query = False
                if isinstance(targets, list):
                    for t in targets:
                        if isinstance(t, dict) and _target_has_query(t):
                            has_any_query = True
                            break
                if exprs:
                    has_any_query = True

                if not has_any_query and not targets:
                    verdict = "Defect"
                    defect_class = "Dashboard query defect"
                    evidence_bits.append(
                        f"queryable type={ptype} has no targets/expr/url"
                    )
                    empty_query_hits.append(
                        {
                            "dashboard_uid": uid,
                            "panel_id": pid,
                            "title": ptitle,
                            "reason": "no targets",
                        }
                    )
                elif not has_any_query:
                    verdict = "Defect"
                    defect_class = "Dashboard query defect"
                    evidence_bits.append(
                        f"targets present ({len(targets)}) but no expr/url/query"
                    )
                    empty_query_hits.append(
                        {
                            "dashboard_uid": uid,
                            "panel_id": pid,
                            "title": ptitle,
                            "reason": "empty targets",
                        }
                    )
                else:
                    if dsk == "prometheus" or any(
                        "bioetl_" in e or "ALERTS" in e for e in exprs
                    ):
                        unknown: list[str] = []
                        for e in exprs:
                            for metric in _extract_metrics(e):
                                if (
                                    metric not in valid_metrics
                                    and not metric.startswith("$")
                                ):
                                    if metric in {
                                        "up",
                                        "ALERTS",
                                        "ALERTS_FOR_STATE",
                                    }:
                                        continue
                                    unknown.append(metric)
                        if unknown:
                            unique_unknown = sorted(set(unknown))
                            unknown_metric_hits.append(
                                {
                                    "dashboard_uid": uid,
                                    "panel_id": pid,
                                    "title": ptitle,
                                    "metrics": unique_unknown,
                                    "exprs": exprs[:3],
                                }
                            )
                            verdict = "Defect"
                            defect_class = "Dashboard query defect"
                            evidence_bits.append(
                                "unknown metrics vs registry: "
                                + ",".join(unique_unknown[:8])
                            )
                        else:
                            evidence_bits.append(
                                f"exprs={len(exprs)} metrics_ok ds={dsk or 'inferred'}"
                            )
                    else:
                        evidence_bits.append(
                            f"has_query targets={len(targets)} ds={dsk} exprs={len(exprs)}"
                        )

                if any(
                    k in ptitle for k in ("Status", "Current Cause", "Current Status")
                ):
                    for e in exprs:
                        if "or vector(0)" in e:
                            vector0_status_hits.append(
                                {
                                    "dashboard_uid": uid,
                                    "panel_id": pid,
                                    "title": ptitle,
                                }
                            )
                            verdict = "Defect"
                            defect_class = "Dashboard query defect"
                            evidence_bits.append("status panel uses or vector(0)")

                if dsk == "unknown" and has_any_query:
                    ds = panel.get("datasource")
                    if ds in (None, "", {}):
                        evidence_bits.append("datasource=inherited/default")
                    else:
                        evidence_bits.append(
                            f"datasource_kind=unknown raw={ds!r}"[:200]
                        )

            if defect_class:
                defect_counts[defect_class] += 1
            verdict_counts[verdict] += 1

            panel_rows.append(
                {
                    "dashboard_uid": uid,
                    "panel_id": pid,
                    "title": ptitle,
                    "panel_type": ptype,
                    "datasource_kind": dsk,
                    "verdict": verdict,
                    "defect_class": defect_class,
                    "evidence": "; ".join(evidence_bits)[:500],
                    "query_preview": " | ".join(exprs)[:300],
                }
            )

        inventory.append(
            {
                "file": path.name,
                "uid": uid,
                "title": title,
                "panel_count": len(panels),
                "datasources": sorted(ds_set),
            }
        )

    expected_count = matrix.EXPECTED_PANEL_COUNT
    checks.append(
        {
            "check_id": "PANELS-INV-01",
            "status": "pass" if total_panels == expected_count else "fail",
            "fact": (
                f"Shipped panel count across 7 dashboards is {total_panels} "
                f"(EXPECTED_PANEL_COUNT={expected_count})."
            ),
            "score_1_5": 5 if total_panels == expected_count else 2,
            "priority": "P1" if total_panels != expected_count else "P3",
            "bioetl_priority": "high" if total_panels != expected_count else "low",
            "block": "inventory",
            "epistemic": "FACT",
            "evidence": [
                "grafana/dashboards/*.json",
                "scripts/engineering/qa/report_dashboard_panel_audit_matrix.py:EXPECTED_PANEL_COUNT",
            ],
            "recommendation": (
                "Reconcile EXPECTED_PANEL_COUNT if intentional drift."
                if total_panels != expected_count
                else "Keep matrix contract green."
            ),
        }
    )
    checks.append(
        {
            "check_id": "PANELS-STRUCT-01",
            "status": "pass" if not empty_query_hits else "fail",
            "fact": (
                f"Queryable panels missing targets/expr/url: {len(empty_query_hits)}; "
                f"empty text panels included when content empty."
            ),
            "score_1_5": 5 if not empty_query_hits else 2,
            "priority": "P1" if empty_query_hits else "P3",
            "bioetl_priority": "high" if empty_query_hits else "low",
            "block": "query",
            "epistemic": "FACT",
            "evidence": [
                f"{h['dashboard_uid']}:{h['panel_id']} ({h['reason']})"
                for h in empty_query_hits[:15]
            ]
            or ["no empty-query panels"],
            "recommendation": "Add targets or convert panel type if intentional static content.",
        }
    )
    checks.append(
        {
            "check_id": "PANELS-METRIC-01",
            "status": "pass" if not unknown_metric_hits else "fail",
            "fact": (
                f"Panels referencing metrics absent from emitter+recording-rule registry: "
                f"{len(unknown_metric_hits)}."
            ),
            "score_1_5": 5 if not unknown_metric_hits else 2,
            "priority": "P1" if unknown_metric_hits else "P3",
            "bioetl_priority": "high" if unknown_metric_hits else "low",
            "block": "query",
            "epistemic": "FACT",
            "evidence": [
                f"{h['dashboard_uid']}:{h['panel_id']} metrics={h['metrics']}"
                for h in unknown_metric_hits[:15]
            ]
            or ["all extracted bioetl_/ALERTS/up metrics resolve in registry"],
            "recommendation": "Align PromQL with registered metrics or add recording rules/emitters.",
        }
    )
    checks.append(
        {
            "check_id": "PANELS-STATUS-01",
            "status": "pass" if not vector0_status_hits else "fail",
            "fact": (
                f"Status/Current Cause panels using 'or vector(0)': "
                f"{len(vector0_status_hits)} (fail-closed policy)."
            ),
            "score_1_5": 5 if not vector0_status_hits else 1,
            "priority": "P0" if vector0_status_hits else "P3",
            "bioetl_priority": "critical" if vector0_status_hits else "low",
            "block": "query",
            "epistemic": "FACT",
            "evidence": [
                f"{h['dashboard_uid']}:{h['panel_id']} {h['title']}"
                for h in vector0_status_hits[:10]
            ]
            or ["no status panel uses or vector(0)"],
            "recommendation": "Remove vector(0) fallback from status panels.",
        }
    )
    checks.append(
        {
            "check_id": "PANELS-ID-01",
            "status": "pass" if not duplicate_ids else "fail",
            "fact": f"Duplicate panel ids within a dashboard: {len(duplicate_ids)}.",
            "score_1_5": 5 if not duplicate_ids else 2,
            "priority": "P2" if duplicate_ids else "P3",
            "bioetl_priority": "medium" if duplicate_ids else "low",
            "block": "structure",
            "epistemic": "FACT",
            "evidence": [
                f"{h['dashboard_uid']}:{h['panel_id']}" for h in duplicate_ids[:10]
            ]
            or ["panel ids unique per dashboard"],
            "recommendation": "Renumber duplicate panel ids.",
        }
    )
    checks.append(
        {
            "check_id": "PANELS-LIVE-01",
            "status": "na",
            "fact": (
                "MONITORING=false: live Grafana/Prometheus render and query execution "
                "not performed; contrast/zoom/DOM not verifiable."
            ),
            "score_1_5": 3,
            "priority": "P3",
            "bioetl_priority": "low",
            "block": "render",
            "epistemic": "FACT",
            "evidence": [
                "task param MONITORING=false",
                "no docker-compose.monitoring.yml start",
            ],
            "recommendation": "Re-run with MONITORING=true + preflight for live panel audit.",
        }
    )
    checks.append(
        {
            "check_id": "PANELS-DS-01",
            "status": "pass",
            "fact": (
                f"Datasource kinds observed: prometheus panels≈{prom_panels}, "
                f"http panels≈{http_panels}, rows={row_panels}, text={text_panels}, "
                f"queryable={queryable_panels}."
            ),
            "score_1_5": 4,
            "priority": "P3",
            "bioetl_priority": "low",
            "block": "inventory",
            "epistemic": "FACT",
            "evidence": [
                f"{i['uid']}: {i['panel_count']} panels ds={i['datasources']}"
                for i in inventory
            ],
            "recommendation": "n/a",
        }
    )

    fid = 0
    for hit in empty_query_hits:
        fid += 1
        findings.append(
            {
                "id": f"PANELS-EMPTY-{fid:03d}",
                "path": f"grafana/dashboards/{hit['dashboard_uid']}.json",
                "observation": (
                    f"Panel id={hit['panel_id']} title={hit['title']!r} "
                    f"has {hit['reason']} (static JSON)."
                ),
                "status": "PROVEN",
                "priority": "P1",
                "severity": "High",
                "confidence": "high",
                "method": "static JSON walk of targets/expr/url/options.content",
                "expected": "Queryable panel has non-empty query target or intentional non-query type",
                "actual": hit["reason"],
                "impact": "Panel will show No data / blank in Grafana",
                "remediation": "Add PromQL/HTTP target or change panel type/content",
                "automated_fix_possible": True,
            }
        )
    for hit in unknown_metric_hits:
        fid += 1
        findings.append(
            {
                "id": f"PANELS-METRIC-{fid:03d}",
                "path": f"grafana/dashboards/{hit['dashboard_uid']}.json",
                "observation": (
                    f"Panel id={hit['panel_id']} title={hit['title']!r} references "
                    f"metrics not in emitter/recording-rule registry: {hit['metrics']}."
                ),
                "status": "PROVEN",
                "priority": "P1",
                "severity": "High",
                "confidence": "high",
                "method": "PromQL metric extract vs get_all_valid_metric_names()",
                "expected": "All bioetl_* metrics resolve to emitters or recording rules",
                "actual": f"unknown={hit['metrics']}",
                "impact": "Query may return empty or error depending on Prometheus content",
                "remediation": "Fix metric name or register recording rule / emitter",
                "automated_fix_possible": True,
            }
        )
    for hit in vector0_status_hits:
        fid += 1
        findings.append(
            {
                "id": f"PANELS-STATUS-{fid:03d}",
                "path": f"grafana/dashboards/{hit['dashboard_uid']}.json",
                "observation": (
                    f"Status panel id={hit['panel_id']} title={hit['title']!r} "
                    f"uses 'or vector(0)' (violates fail-closed status policy)."
                ),
                "status": "PROVEN",
                "priority": "P0",
                "severity": "Critical",
                "confidence": "high",
                "method": "static expr scan for status titles",
                "expected": "Status panels fail closed without vector(0)",
                "actual": "or vector(0) present",
                "impact": "False OK/zero status when series absent",
                "remediation": "Remove or vector(0) fallback",
                "automated_fix_possible": True,
            }
        )
    for hit in duplicate_ids:
        fid += 1
        findings.append(
            {
                "id": f"PANELS-DUPID-{fid:03d}",
                "path": f"grafana/dashboards/{hit['dashboard_uid']}.json",
                "observation": (
                    f"Duplicate panel id={hit['panel_id']} title={hit['title']!r}."
                ),
                "status": "PROVEN",
                "priority": "P2",
                "severity": "Medium",
                "confidence": "high",
                "method": "panel id uniqueness per dashboard",
                "expected": "Unique panel ids",
                "actual": "duplicate id",
                "impact": "Ambiguous links/overrides/audit keys",
                "remediation": "Assign unique panel ids",
                "automated_fix_possible": True,
            }
        )

    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    findings.sort(key=lambda f: (priority_rank.get(f["priority"], 9), f["id"]))
    findings_out = findings[:24]

    defects = [r for r in panel_rows if r["verdict"] == "Defect"]
    sample_ok: list[dict] = []
    by_uid: dict[str, list[dict]] = defaultdict(list)
    for r in panel_rows:
        by_uid[r["dashboard_uid"]].append(r)
    for _uid, rows in by_uid.items():
        oks = [r for r in rows if r["verdict"] == "OK"]
        sample_ok.extend(oks[:4])
    selected: dict[tuple[str, str], dict] = {
        (r["dashboard_uid"], r["panel_id"]): r for r in defects
    }
    for r in sample_ok:
        selected.setdefault((r["dashboard_uid"], r["panel_id"]), r)
    for r in panel_rows:
        if len(selected) >= 80:
            break
        selected.setdefault((r["dashboard_uid"], r["panel_id"]), r)
    panel_rows_out = list(selected.values())[:80]

    not_verifiable_count = sum(
        1 for r in panel_rows if r["verdict"] == "Not Verifiable"
    )
    live_nv = queryable_panels

    notes = (
        f"CONTOUR=panels cycle=2 MONITORING=false. "
        f"Static JSON audit only. inventory={inventory}. "
        f"totals: panels={total_panels} queryable={queryable_panels} "
        f"rows={row_panels} text={text_panels} "
        f"verdicts={dict(verdict_counts)} defects={dict(defect_counts)} "
        f"empty_query={len(empty_query_hits)} unknown_metric={len(unknown_metric_hits)} "
        f"vector0_status={len(vector0_status_hits)} dup_ids={len(duplicate_ids)} "
        f"live_render_nv_for_queryable={live_nv}. "
        f"panel_rows in output capped at 80 (schema); full matrix written to panel-matrix.csv. "
        f"Epistemic: structural query/metric issues are FACT from shipped JSON; "
        f"live render/data plane Not Verifiable without monitoring stack."
    )

    result = {
        "contour": "panels",
        "checks": checks[:40],
        "findings": findings_out,
        "panel_rows": [
            {
                "dashboard_uid": r["dashboard_uid"],
                "panel_id": r["panel_id"],
                "title": r.get("title", ""),
                "verdict": r["verdict"],
                "defect_class": r.get("defect_class") or "",
                "evidence": r.get("evidence") or "",
            }
            for r in panel_rows_out
        ],
        "not_verifiable_count": not_verifiable_count,
        "notes": notes,
        "_meta": {
            "inventory": inventory,
            "total_panels": total_panels,
            "verdict_counts": dict(verdict_counts),
            "findings_total_before_cap": len(findings),
            "panel_rows_full": len(panel_rows),
            "empty_query_hits": empty_query_hits,
            "unknown_metric_hits": unknown_metric_hits[:50],
            "vector0_status_hits": vector0_status_hits,
            "duplicate_ids": duplicate_ids,
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    full_csv = out_dir / "panel-matrix.csv"
    with full_csv.open("w", encoding="utf-8", newline="") as fh:
        fields = [
            "dashboard_uid",
            "panel_id",
            "title",
            "panel_type",
            "datasource_kind",
            "verdict",
            "defect_class",
            "evidence",
            "query_preview",
        ]
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in panel_rows:
            w.writerow({k: r.get(k, "") for k in fields})

    public = {k: v for k, v in result.items() if not k.startswith("_")}
    (out_dir / "panels-contour.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "findings.json").write_text(
        json.dumps(findings_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "checks.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "panels-meta.json").write_text(
        json.dumps(result["_meta"], ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(result["_meta"], indent=2, default=str)[:8000])
    print(f"wrote {full_csv} rows={len(panel_rows)}")
    print(f"findings={len(findings_out)} (raw {len(findings)})")
    return result


if __name__ == "__main__":
    out = (
        ROOT
        / "reports"
        / "audit"
        / "dashboard-cycle"
        / "20260811T180000Z-c205349-dash"
        / "cycle-2"
    )
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
    analyze(out)
