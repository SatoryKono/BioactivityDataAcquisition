#!/usr/bin/env python3
"""DUX4 V0 inventories + visual enforcement (description/threshold/layout).

Titles stay contract-stable (DUX4-01 Approach B). Scope grammar remains in
descriptions + provenance; thresholds/layout get surgical fixes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"
DOCS = ROOT / "docs" / "03-guides" / "dashboards"

type JsonObject = dict[str, Any]


def _is_zeroish(val: object) -> bool:
    """True for None or numeric zero without float equality on non-numbers.
    NOSONAR - S1244: abs(float(val)) <= 1e-15 is the correct way to check near-zero without direct equality
    """
    if val is None:
        return True
    if isinstance(val, bool):
        return False
    if isinstance(val, (int, float)):
        return abs(float(val)) <= 1e-15
    return False


def walk(
    panels: list[JsonObject] | None,
    parent_collapsed: bool = False,
    acc: list[tuple[JsonObject, bool]] | None = None,
) -> list[tuple[JsonObject, bool]]:
    acc = acc if acc is not None else []
    for panel in panels or []:
        collapsed = parent_collapsed or bool(panel.get("collapsed"))
        acc.append((panel, collapsed))
        if panel.get("panels"):
            walk(panel["panels"], collapsed, acc)
    return acc


def load(path: Path) -> JsonObject:
    return cast(JsonObject, json.loads(path.read_text(encoding="utf-8")))


def save(path: Path, data: JsonObject) -> None:
    import os

    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    os.replace(tmp, path)


def prepend_description(panel: JsonObject, sentence: str) -> bool:
    desc = panel.get("description") or ""
    marker = sentence[:48]
    if marker in desc:
        return False
    panel["description"] = f"{sentence} {desc}".strip()
    return True


def find_row(panels: list[JsonObject] | None, substr: str) -> JsonObject | None:
    for panel, _ in walk(panels):
        if (
            panel.get("type") == "row"
            and substr.lower() in (panel.get("title") or "").lower()
        ):
            return panel
    return None


def write_v0_artifacts() -> None:
    """Write DUX4 v0 artifacts for field override inventory and panel redesign matrix.

    NOSONAR - S3776: complexity 27 exceeds 15; extraction would obscure dashboard analysis logic
    """
    override_rows: list[JsonObject] = []
    for path in sorted(DASH.glob("*.json")):
        data = load(path)
        for panel, collapsed in walk(data.get("panels") or []):
            if panel.get("type") == "row":
                continue
            defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
            thresholds = (defaults.get("thresholds") or {}).get("steps") or []
            mappings = defaults.get("mappings") or []
            custom = defaults.get("custom") or {}
            risks: list[str] = []
            for step in thresholds:
                if not isinstance(step, dict):
                    continue
                color = str(step.get("color") or "").lower()
                val = step.get("value")
                zeroish = _is_zeroish(val)
                if zeroish and "green" in color:
                    risks.append("green_at_or_below_zero")
                if zeroish and "red" in color:
                    risks.append("red_at_or_below_zero")
            if custom.get("displayMode") == "color-background":
                risks.append("color_background")
            title = panel.get("title") or ""
            desc = panel.get("description") or ""
            if "SCRAPING" in title or "SCRAPING" in desc:
                risks.append("scraping_related")
            if "alert" in title.lower() or "firing" in desc.lower():
                risks.append("alert_related")
            override_rows.append(
                {
                    "uid": data.get("uid"),
                    "file": path.name,
                    "panel_id": panel.get("id"),
                    "title": title,
                    "type": panel.get("type"),
                    "collapsed": collapsed,
                    "gridPos": panel.get("gridPos"),
                    "threshold_steps": thresholds,
                    "mapping_count": len(mappings) if isinstance(mappings, list) else 0,
                    "noValue": defaults.get("noValue"),
                    "unit": defaults.get("unit"),
                    "risks": sorted(set(risks)),
                }
            )
    risk_counts: dict[str, int] = {}
    for row in override_rows:
        for risk in row["risks"]:
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
    inv = {
        "schema_version": "dux4-field-override-inventory-v1",
        "issue": 7090,
        "panel_count": len(override_rows),
        "risk_counts": risk_counts,
        "panels": override_rows,
    }
    (DOCS / "dux4-field-override-inventory.json").write_text(
        json.dumps(inv, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("override inventory", inv["panel_count"], risk_counts)

    matrix_rows: list[JsonObject] = []
    risk_index = {(row["file"], row["panel_id"]): row["risks"] for row in override_rows}
    for path in sorted(DASH.glob("*.json")):
        data = load(path)
        for panel, collapsed in walk(data.get("panels") or []):
            if panel.get("type") == "row":
                continue
            title = panel.get("title") or ""
            desc = panel.get("description") or ""
            scope, family = "UNDECLARED", "UNDECLARED"
            if title == "Status":
                scope, family = "NOW", "HEALTH"
            if title in ("ID", "Processed Records"):
                scope, family = "RUN", "EVIDENCE"
            if "Metrics Evidence" in title or "Telemetry" in title:
                scope, family = "NOW", "EVIDENCE"
            if "Suspect" in title:
                scope, family = "WORKFLOW", "IMPACT"
            if "Freshness" in title:
                scope, family = "NOW", "EVIDENCE"
            if "Score" in title:
                scope, family = "RANGE", "EVIDENCE"
            defects: list[str] = []
            risks = risk_index.get((path.name, panel.get("id")), [])
            if "green_at_or_below_zero" in risks or "red_at_or_below_zero" in risks:
                defects.append("color_risk")
            gp = panel.get("gridPos") or {}
            if (
                not collapsed
                and panel.get("type") == "stat"
                and int(gp.get("h") or 0) >= 6
                and int(gp.get("w") or 0) >= 8
            ):
                defects.append("giant_stat")
            content = ""
            if panel.get("type") == "text":
                content = str((panel.get("options") or {}).get("content") or "")
                if not collapsed and len(content) > 500:
                    defects.append("long_text_scroll_risk")
            targets: list[str] = []
            if title == "Status":
                targets.append("DUX4-10")
            if "Metrics Evidence" in title:
                targets += ["DUX4-11", "DUX4-10"]
            if any(
                key in title
                for key in (
                    "Healthy Checks",
                    "Failure Rate",
                    "Health Checks Total",
                )
            ):
                targets.append("DUX4-12")
            if "Data Quality Score" in title or "Worst-Entity DQ Score" in title:
                targets.append("DUX4-13")
            if "Replay Safety" in title or (
                "Manifest" in title and "Integrity" in title
            ):
                targets.append("DUX4-14")
            if "Suspect" in title:
                targets.append("DUX4-15")
            if "giant_stat" in defects:
                targets.append("DUX4-21")
            if "long_text_scroll_risk" in defects:
                targets.append("DUX4-22")
            if (
                title in ("ID", "Processed Records")
                and not collapsed
                and data.get("uid") != "bioetl-run-explorer-v1"
            ):
                targets.append("DUX4-23")
            matrix_rows.append(
                {
                    "uid": data.get("uid"),
                    "file": path.name,
                    "panel_id": panel.get("id"),
                    "title": title,
                    "type": panel.get("type"),
                    "collapsed": collapsed,
                    "gridPos": gp,
                    "scope_intent": scope,
                    "family_intent": family,
                    "has_dux3_desc": "DUX3" in desc or "DUX4" in desc,
                    "defects": defects,
                    "dux4_targets": sorted(set(targets)),
                }
            )
    defect_counts: dict[str, int] = {}
    for row in matrix_rows:
        for defect in row["defects"]:
            defect_counts[defect] = defect_counts.get(defect, 0) + 1
    matrix = {
        "schema_version": "dux4-panel-redesign-matrix-v1",
        "issue": 7091,
        "panel_count": len(matrix_rows),
        "defect_counts": defect_counts,
        "panels": matrix_rows,
    }
    (DOCS / "dux4-panel-redesign-matrix.json").write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("matrix", matrix["panel_count"], defect_counts)

    (DOCS / "dux4-title-scope-harness.md").write_text(
        """# DUX4-01 title/scope harness decision

**Issue:** #7089

## Decision: Approach B (primary) + Approach A helpers

### Approach B (shipped)

Panel **titles stay exact** for integration contracts. Visible operator grammar:

- panel descriptions (`DUX3-*` / `DUX4-*` markers)
- Provenance / context strips with scope legend
- `dux3-residual-contracts.md`

### Approach A (optional; helpers ready)

ASCII title prefix pattern:

```text
[NOW/HEALTH] Status
```

Regex: `^\\[(NOW|RANGE|RUN|WORKFLOW|GLOBAL)/(HEALTH|EXEC|EVIDENCE|IMPACT|APPLICABILITY)\\]\\s+`

Helpers in `tests/integration/_grafana_test_support.py`:

- `SCOPE_TITLE_PREFIX_RE`
- `strip_scope_title_prefix`
- `panel_base_title`
- `index_panels_by_base_title`

Contracts may match **base titles** via helpers without requiring prefixes today.

## Acceptance

- [x] Decision documented
- [x] Helpers present
- [x] Existing exact-title tests remain the default path
""",
        encoding="utf-8",
        newline="\n",
    )


def neutralize_zero_color_thresholds(panel: JsonObject) -> bool:
    """Avoid green/red success/failure semantics at value 0 when present."""
    fc = panel.get("fieldConfig") or {}
    defaults = fc.get("defaults") or {}
    thresholds = defaults.get("thresholds") or {}
    steps = thresholds.get("steps")
    if not isinstance(steps, list) or not steps:
        return False
    changed = False
    new_steps = []
    for step in steps:
        if not isinstance(step, dict):
            new_steps.append(step)
            continue
        step = dict(step)
        color = str(step.get("color") or "").lower()
        val = step.get("value")
        zeroish = _is_zeroish(val)
        if zeroish and ("green" in color or "red" in color):
            step["color"] = "text"
            changed = True
        new_steps.append(step)
    if changed:
        thresholds = dict(thresholds)
        thresholds["steps"] = new_steps
        defaults = dict(defaults)
        defaults["thresholds"] = thresholds
        # ensure noValue is not empty-success coded
        if not defaults.get("noValue"):
            defaults["noValue"] = "N/A"
        fc = dict(fc)
        fc["defaults"] = defaults
        panel["fieldConfig"] = fc
    return changed


def shrink_stat(panel: JsonObject, *, max_h: int = 4, max_w: int = 6) -> bool:
    if panel.get("type") != "stat":
        return False
    gp = dict(panel.get("gridPos") or {})
    changed = False
    if int(gp.get("h") or 0) > max_h:
        gp["h"] = max_h
        changed = True
    if int(gp.get("w") or 0) > max_w and int(gp.get("y") or 0) < 14:
        # only shrink wide first-band stats that are not full nav
        if int(gp.get("w") or 0) >= 12:
            gp["w"] = max_w
            changed = True
    if changed:
        panel["gridPos"] = gp
    return changed


def shorten_text_panel(panel: JsonObject, *, max_len: int = 480) -> bool:
    """Shorten long markdown triage prose only.

    Never mid-cut HTML chrome (nav bus id=1000, provenance banners) or any
    structured HTML shell — that produced broken chips and DUX4-22 markers in
    operator-facing navigation.
    """
    if panel.get("type") != "text":
        return False
    # Shared navigation bus is generated by render_nav_bus.py and must stay whole.
    if panel.get("id") == 1000 or panel.get("title") == "Navigation":
        return False
    options = dict(panel.get("options") or {})
    content = options.get("content")
    if not isinstance(content, str) or len(content) <= max_len:
        return False
    mode = str(options.get("mode") or "markdown").lower()
    stripped = content.lstrip()
    # HTML layout contracts (nav, provenance banners) are not free-form prose.
    if (
        mode == "html"
        or "bioetl-nav" in content
        or stripped.startswith("<")
        or stripped.startswith("<div")
    ):
        return False
    # Keep first paragraphs, add note
    cut = content[: max_len - 40].rsplit("\n", 1)[0]
    if not cut.strip():
        return False
    options["content"] = (
        cut + "\n\n_(DUX4-22: truncated; full text in panel description/docs.)_"
    )
    panel["options"] = options
    prepend_description(
        panel,
        "DUX4-22: Full prose shortened on-canvas to remove internal scroll; details in description/docs.",
    )
    return True


def apply_board_enforcement() -> list[str]:
    changes: list[str] = []

    for path in sorted(DASH.glob("*.json")):
        data = load(path)
        uid = data.get("uid")
        for panel, collapsed in walk(data.get("panels") or []):
            title = panel.get("title") or ""
            # Scope legend on Provenance
            if title == "Provenance":
                if prepend_description(
                    panel,
                    "DUX4-10: Scope legend — NOW=current, RANGE=window, RUN=exact run_id (HTTP), "
                    "WORKFLOW/GLOBAL=blast radius/fleet. Family: HEALTH|EXEC|EVIDENCE|IMPACT|APPLICABILITY.",
                ):
                    changes.append(f"{uid}:Provenance scope legend")
            # Runtime SCRAPING/evidence
            if uid == "bioetl-runtime" and (
                "Metrics Evidence" in title or title == "Status"
            ):
                if title == "Status":
                    prepend_description(
                        panel,
                        "DUX4-11: NOW HEALTH only. SCRAPING/telemetry chips are EVIDENCE, not success.",
                    )
                else:
                    prepend_description(
                        panel,
                        "DUX4-11: Lifecycle/telemetry EVIDENCE — use neutral phase semantics, not health-green.",
                    )
                # neutralize green thresholds on evidence chips if any
                if neutralize_zero_color_thresholds(panel):
                    changes.append(f"{uid}:{title} neutralize zero color")
            # Provider zero rates
            if uid == "bioetl-provider-health-v2" and any(
                key in title
                for key in (
                    "Healthy Checks",
                    "Health Checks Total",
                    "Failure Rate",
                )
            ):
                prepend_description(
                    panel,
                    "DUX4-12: Denominator 0 → N/A/SELECTION_REQUIRED, never green success 0.00%.",
                )
                if neutralize_zero_color_thresholds(panel):
                    changes.append(f"{uid}:{title} zero color")
                defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
                if defaults.get("noValue") in (None, "", "0"):
                    fc = dict(panel.get("fieldConfig") or {})
                    d2 = dict(defaults)
                    d2["noValue"] = "N/A"
                    fc["defaults"] = d2
                    panel["fieldConfig"] = fc
                    changes.append(f"{uid}:{title} noValue N/A")
            if uid == "bioetl-provider-health-v2" and "Latency" in title:
                prepend_description(
                    panel,
                    "DUX4-12: Empty state must describe latency samples (not circuit-breaker trips).",
                )
            # DQ scores
            if uid == "bioetl-dq-v2" and "Score" in title:
                prepend_description(
                    panel,
                    "DUX4-13: RANGE evidence only — not peer NOW health; dual 100% ≠ healthy if Status UNKNOWN.",
                )
                if shrink_stat(panel, max_h=4, max_w=8):
                    changes.append(f"{uid}:{title} shrink")
            if uid == "bioetl-dq-v2" and title == "Status":
                prepend_description(
                    panel,
                    "DUX4-13: Composite first strip owner — pair with evidence freshness + delivery impact.",
                )
            # Trust
            if uid == "bioetl-control-plane-v1" and "Replay Safety" in title:
                prepend_description(
                    panel,
                    "DUX4-14: OK only WITHIN OBSERVED COVERAGE; blind spots ⇒ PARTIAL confidence.",
                )
            if uid == "bioetl-control-plane-v1" and title == "Processed Records":
                if neutralize_zero_color_thresholds(panel):
                    changes.append("trust:Processed Records zero color")
                prepend_description(
                    panel,
                    "DUX4-14/03: Expected empty accounting is VALID_EMPTY/N/A — not red failure.",
                )
            # Incident
            if uid == "bioetl-incident-v1" and "Suspect" in title:
                prepend_description(
                    panel,
                    "DUX4-15: WORKFLOW blast radius — show selected vs affected pipeline; not a silent filter bug.",
                )
            if uid == "bioetl-incident-v1" and "Alert" in title:
                prepend_description(
                    panel,
                    "DUX4-17: Firing/pending must not use success-green series colors.",
                )
                if neutralize_zero_color_thresholds(panel):
                    changes.append(f"{uid}:{title} alert color")
            # Overview
            if uid == "bioetl-overview-v2" and title in (
                "Status",
                "Inputs",
                "First Action",
            ):
                prepend_description(
                    panel,
                    "DUX4-16: First strip = health + evidence/freshness proxy + action; blast radius via Inputs/alerts.",
                )
            # Run explorer hub notes
            if uid == "bioetl-run-explorer-v1" and title in (
                "ID",
                "Processed Records",
            ):
                prepend_description(
                    panel,
                    "DUX4-23/25: Canonical RUN hub — only board with first-class ID/Processed KPIs.",
                )
            # Layout: shrink giant first-band stats
            if not collapsed and panel.get("type") == "stat":
                if shrink_stat(panel):
                    changes.append(f"{uid}:{title} stat shrink")
            # Scroll: shorten long text
            if not collapsed and panel.get("type") == "text":
                if shorten_text_panel(panel):
                    changes.append(f"{uid}:{title} text shorten")

        # Force run-context shells collapsed on non-run boards
        if uid != "bioetl-run-explorer-v1":
            row = find_row(data.get("panels"), "Run context")
            if row is not None:
                row["collapsed"] = True
                prepend_description(
                    row,
                    "DUX4-23: Collapsed by default — Run Explorer owns first-class ID/Processed Records.",
                )
                for child in row.get("panels") or []:
                    gp = dict(child.get("gridPos") or {})
                    if int(gp.get("h") or 0) > 6:
                        gp["h"] = 6
                        child["gridPos"] = gp
                changes.append(f"{uid}:shell collapsed")

        # Collapse deep forensic rows on Trust
        if uid == "bioetl-control-plane-v1":
            for panel, _ in walk(data.get("panels") or []):
                if panel.get("type") != "row":
                    continue
                t = (panel.get("title") or "").lower()
                if any(
                    key in t
                    for key in (
                        "forensic",
                        "remaining",
                        "debug",
                        "raw",
                        "identity evidence",
                    )
                ):
                    panel["collapsed"] = True

        save(path, data)

    return changes


def write_v3_v4_docs() -> None:
    (DOCS / "dux4-variable-rules.md").write_text(
        """# DUX4 variable rules (V3)

**Issues:** #7106–#7110

## Ownership

| Variable | Global? | Owner board | Notes |
| --- | --- | --- | --- |
| `workflow` | yes | all | Context |
| `pipeline` | yes | all | Derived from workflow when possible |
| `run_type` | yes | NOW/RANGE boards | |
| time range | yes | all | |
| `run_id` | **optional handoff** | **Run Explorer** primary select | Never Prometheus label; do not recolor NOW health |
| `provider` | Provider Health (required/derived) | Provider | Empty ⇒ SELECTION_REQUIRED |
| `stage` | Runtime/DQ only | Runtime/DQ | Defaults: Current/All — not literal `unknown` |

## Rules

1. Selecting `run_id` should derive/lock pipeline + run_type from run identity (UI/docs; implement where templating allows).
2. NOW panels ignore `run_id` for Prom filters.
3. Data links: preserve `${__url_time_range}`; pass `run_id` only to run-scoped destinations.
4. Incompatible combos documented in selector contracts.

See also `contracts/selector-contracts.yaml` and `navigation-links.yaml`.
""",
        encoding="utf-8",
        newline="\n",
    )
    (DOCS / "dux4-visual-enforcement-closeout.md").write_text(
        """# DUX4 visual enforcement closeout

**Epic:** #7088
**Date:** 2026-07-29

## Delivered

| Wave | Deliverable |
| --- | --- |
| V0 | Title harness decision (Approach B + helpers), field-override inventory, panel redesign matrix |
| V1 | Description-level enforcement + threshold neutralization for zero green/red risks on key panels |
| V2 | Stat shrink, text truncation, collapsed run-context shells, forensic row collapse |
| V3 | Variable ownership rules doc |
| V4 | Screenshot protocol (existing DUX3), fixtures (existing), usability note |
| Track | DUX4-44 remains tracking-only |

## Artifacts

- `dux4-title-scope-harness.md`
- `dux4-field-override-inventory.json`
- `dux4-panel-redesign-matrix.json`
- `dux4-variable-rules.md`
- `scripts/ops/observability/grafana/apply_dux4_enforcement.py`
- helpers in `tests/integration/_grafana_test_support.py`

## Residual (honest)

Full audit wireframe rebuild (1.0 viewport) and live screenshot captures remain iterative:
live PNG gates when Grafana render is available (#7112). Query-level SELECTION_REQUIRED
and run_id templating locks may need follow-up if Grafana variable capabilities limit
pure JSON solutions.

## Tests

`pytest tests/integration/test_grafana_config.py tests/integration/test_pipeline_runtime_dashboard.py`
""",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    write_v0_artifacts()
    changes = apply_board_enforcement()
    write_v3_v4_docs()
    print(f"board changes: {len(changes)}")
    for item in changes[:40]:
        print(" -", item)
    if len(changes) > 40:
        print(f" ... +{len(changes) - 40} more")


if __name__ == "__main__":
    main()
