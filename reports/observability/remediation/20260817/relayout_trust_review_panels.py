"""One-shot layout fix: make named Review* tables findable on dashboard 0."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PATH = Path("grafana/dashboards/bioetl-control-plane-v1.json")


def find_root(panels: list[dict[str, Any]], panel_id: int) -> dict[str, Any]:
    for panel in panels:
        if panel.get("id") == panel_id:
            return panel
    raise KeyError(panel_id)


def extract_from_row(
    panels: list[dict[str, Any]], row_id: int, child_id: int
) -> dict[str, Any]:
    row = find_root(panels, row_id)
    children = list(row.get("panels") or [])
    for index, child in enumerate(children):
        if child.get("id") == child_id:
            row["panels"] = children[:index] + children[index + 1 :]
            return child
    raise KeyError(child_id)


def ensure_limit(panel: dict[str, Any], limit: int) -> None:
    transforms = list(panel.get("transformations") or [])
    for transform in transforms:
        if transform.get("id") == "limit":
            options = transform.setdefault("options", {})
            options["limitField"] = limit
            panel["transformations"] = transforms
            return
    transforms.append({"id": "limit", "options": {"limitField": limit}})
    panel["transformations"] = transforms


def ensure_organize(
    panel: dict[str, Any], exclude: list[str], index_by: dict[str, int]
) -> None:
    transforms = list(panel.get("transformations") or [])
    for transform in transforms:
        if transform.get("id") == "organize":
            options = transform.setdefault("options", {})
            excluded = options.setdefault("excludeByName", {})
            for name in exclude:
                excluded[name] = True
            options["indexByName"] = index_by
            panel["transformations"] = transforms
            return
    transforms.append(
        {
            "id": "organize",
            "options": {
                "excludeByName": {name: True for name in exclude},
                "indexByName": index_by,
                "renameByName": {},
            },
        }
    )
    panel["transformations"] = transforms


def main() -> None:
    dash = json.loads(PATH.read_text(encoding="utf-8"))
    panels: list[dict[str, Any]] = dash["panels"]

    p9415 = extract_from_row(panels, 904, 9415)
    p9416 = extract_from_row(panels, 904, 9416)
    p9418 = find_root(panels, 9418)
    p906 = find_root(panels, 906)
    p9400 = find_root(panels, 9400)

    p9418["gridPos"] = {"h": 5, "w": 12, "x": 0, "y": 8}
    ensure_limit(p9418, 4)
    ensure_organize(
        p9418,
        exclude=["reasons"],
        index_by={
            "trust_status": 0,
            "processing_status": 1,
            "scope_kind": 2,
            "evidence_freshness": 3,
            "evidence_observed_at": 4,
        },
    )
    p9418["description"] = (
        "SELECTED RUN HTTP trust summary on the first screen. "
        "processing_status is the data-processing outcome; trust_status is fail-closed "
        "exact-run evidence (INCOMPLETE/ERROR are not OK). Scope is exact_run when "
        "run_id resolves. No-data or backend unavailable is not a health verdict."
    )

    p9416["gridPos"] = {"h": 5, "w": 12, "x": 12, "y": 8}
    ensure_limit(p9416, 4)
    ensure_organize(
        p9416,
        exclude=[],
        index_by={"check": 0, "status": 1, "reason": 2, "detail": 3},
    )
    p9416["description"] = (
        "SELECTED RUN retention policy, reproducibility evidence floor, required "
        "evidence, and archive support. First-screen table — not inside a collapsed "
        "row. UNKNOWN is not a healthy zero. No matching rows are a valid empty "
        "result; backend unavailable means the query could not be evaluated."
    )

    p9415["gridPos"] = {"h": 6, "w": 24, "x": 0, "y": 28}
    p9415["description"] = (
        "SELECTED RUN lineage closure, identity consistency, cycle freedom, and "
        "persistence profile. Root table below the collapsed rows — not inside "
        "Inspect Audit & Lineage Evidence. UNKNOWN is not a healthy zero. No "
        "matching rows are a valid empty result; backend unavailable means the "
        "query could not be evaluated."
    )

    p906["gridPos"] = {"h": 2, "w": 24, "x": 0, "y": 13}
    p906["options"]["content"] = (
        '<div style="padding:4px 8px;line-height:1.3;font-size:16px;'
        'white-space:normal;overflow-wrap:anywhere">'
        "<strong>Do not replay this run</strong> if its Trust status is "
        "<b>INCOMPLETE</b> or <b>UNKNOWN</b>. This-screen tables: "
        "<b>Review Selected-Run Trust</b> and <b>Review Retention Compliance</b>. "
        "<b>Review Lineage Validation</b> is the first table below the collapsed "
        "rows.</div>"
    )
    p906["description"] = (
        "Next-step rail (native title omitted so h=2 does not scroll). "
        "Do not replay this run if its Trust status is INCOMPLETE or UNKNOWN. "
        "First-screen tables: Review Selected-Run Trust (9418) and Review "
        "Retention Compliance (9416). Review Lineage Validation (9415) is the "
        "first root table below the collapsed rows. Monitor Replay Readiness "
        "(9401) is current Prometheus for the pipeline, not this run."
    )

    p9400["options"]["content"] = (
        '<div style="padding:6px 10px;border-left:4px solid #ff9830;'
        "background:rgba(255,152,48,0.08);font-size:16px;line-height:1.35;"
        'white-space:normal;overflow-wrap:anywhere"><div style="max-width:96ch">'
        '<div style="font-size:18px;font-weight:700">'
        "Can this run be replayed safely?</div>"
        "<div><b>SELECTED RUN</b> tables on this screen: Review Selected-Run Trust "
        "· Review Retention Compliance. <b>CURRENT</b> = pipeline replay readiness "
        "now, not this run.</div>"
        "<div><b>Review Lineage Validation</b> is the first table below the "
        "collapsed rows. <b>INCOMPLETE/UNKNOWN</b> = missing evidence — not OK."
        "</div></div></div>"
    )
    p9400["description"] = (
        "processing_status is whether the pipeline finished. trust_status is "
        "whether this run's evidence is complete enough to replay. Monitor Replay "
        "Readiness (9401) is CURRENT Prometheus for pipeline x run_type; run_id "
        "never filters Prometheus. First-screen SELECTED RUN tables: Review "
        "Selected-Run Trust (9418) and Review Retention Compliance (9416). Review "
        "Lineage Validation (9415) is the first root table below the collapsed "
        "rows. UNKNOWN/INCOMPLETE is missing or contradictory evidence, never "
        "healthy."
    )

    for kpi_id in (891, 892, 893, 907):
        find_root(panels, kpi_id)["gridPos"]["y"] = 18

    row_y = {902: 22, 901: 23, 903: 24, 904: 25, 905: 26, 9412: 27}
    for row_id, new_y in row_y.items():
        row = find_root(panels, row_id)
        old_y = int(row["gridPos"]["y"])
        delta = new_y - old_y
        row["gridPos"]["y"] = new_y
        if row_id == 902:
            for child in row.get("panels") or []:
                child["gridPos"]["y"] = int(child["gridPos"]["y"]) + delta

    existing = {panel.get("id") for panel in panels}
    insert_at = [panel.get("id") for panel in panels].index(9418) + 1
    to_insert = []
    if 9416 not in existing:
        to_insert.append(p9416)
    if 9415 not in existing:
        to_insert.append(p9415)
    if to_insert:
        panels[insert_at:insert_at] = to_insert

    dash["description"] = (
        "Answers whether manifest, ledger, checkpoint, replay, and lineage state "
        "are trustworthy enough to allow replay/resume for the selected "
        "pipeline/run_type/time range. Primary question: Can we trust "
        "manifest/ledger/checkpoint/lineage state and safely replay/resume? "
        "GLOBAL read-path panels are not pipeline-scoped and must not use "
        "$pipeline or $run_type filtering. First screen shows Monitor Replay "
        "Readiness plus Review Selected-Run Trust and Review Retention "
        "Compliance. Review Lineage Validation is the first root table below "
        "the collapsed rows."
    )

    PATH.write_text(
        json.dumps(dash, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    dash2 = json.loads(PATH.read_text(encoding="utf-8"))
    root = {panel["id"]: panel for panel in dash2["panels"]}
    print("9418", root[9418]["title"], root[9418]["gridPos"])
    print("9416", root[9416]["title"], root[9416]["gridPos"])
    print("9415", root[9415]["title"], root[9415]["gridPos"])
    print("906", root[906]["gridPos"])
    for panel_id in (891, 892, 893, 907, 902, 901, 903, 904, 905, 9412):
        print(panel_id, root[panel_id]["title"], root[panel_id]["gridPos"])
    child_ids = [child.get("id") for child in root[904].get("panels") or []]
    print("row904 children", child_ids)
    assert 9415 not in child_ids
    assert 9416 not in child_ids
    print("OK")


if __name__ == "__main__":
    main()
