#!/usr/bin/env python3
"""Apply DUX3 residual surgical edits to shipped Grafana dashboards."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def walk_panels(panels: list | None):
    for panel in panels or []:
        yield panel
        if panel.get("panels"):
            yield from walk_panels(panel["panels"])


def ensure_title_prefix(panel: dict, prefix: str) -> bool:
    """Scope markers stay in descriptions — exact titles are contract-tested.

    Kept as a no-op so residual docs can still mention the intended
    ``[SCOPE·FAMILY]`` grammar without breaking panel title assertions.
    """
    _ = (panel, prefix)
    return False


def prepend_description(panel: dict, sentence: str) -> bool:
    desc = panel.get("description") or ""
    if sentence[:40] in desc:
        return False
    panel["description"] = f"{sentence} {desc}".strip()
    return True


def find_row(panels: list | None, title_substr: str) -> dict | None:
    for panel in walk_panels(panels):
        if panel.get("type") == "row" and title_substr.lower() in (
            panel.get("title") or ""
        ).lower():
            return panel
    return None


def collapse_run_context_shell(data: dict, tag: str, changes: list[str]) -> None:
    row = find_row(data.get("panels"), "Run context")
    if row is None:
        return
    row["collapsed"] = True
    for child in row.get("panels") or []:
        gp = child.get("gridPos") or {}
        if int(gp.get("h") or 0) > 6:
            gp["h"] = 6
            child["gridPos"] = gp
            changes.append(f"{tag}:shell h shrink {child.get('title')}")
    if prepend_description(
        row,
        "DUX3-26: Collapsed thin shell only. Canonical ID/Processed Records hub is Run Explorer.",
    ):
        changes.append(f"{tag}:shell row desc")
    changes.append(f"{tag}:shell collapsed")


def main() -> None:
    changes: list[str] = []

    # Runtime DUX3-10 / DUX3-21
    path = DASH / "bioetl-runtime.json"
    data = load(path)
    for panel in walk_panels(data.get("panels")):
        title = panel.get("title") or ""
        if title == "Status":
            if ensure_title_prefix(panel, "[NOW·HEALTH]"):
                changes.append("runtime:Status scope prefix")
            if prepend_description(
                panel,
                "DUX3-10: Execution/health verdict (NOW). Not telemetry collection state. "
                "Peer SCRAPING/gap chips are EVIDENCE confidence only.",
            ):
                changes.append("runtime:Status desc")
        if any(
            key in title
            for key in ("SCRAPING", "Metrics Evidence", "Telemetry", "Matrix Evidence")
        ):
            if ensure_title_prefix(panel, "[NOW·EVIDENCE]"):
                changes.append(f"runtime:{title} evidence prefix")
            if prepend_description(
                panel,
                "DUX3-10: Telemetry/scrape confidence (EVIDENCE). Not pipeline HEALTH. "
                "Do not read as run success/failure.",
            ):
                changes.append(f"runtime:{title} evidence desc")
        if title in ("Failed Runs", "Worst Stage Lag", "Monitor Runtime Blockers"):
            if ensure_title_prefix(panel, "[RANGE·EXEC]"):
                changes.append(f"runtime:{title} exec prefix")
    collapse_run_context_shell(data, "runtime", changes)
    save(path, data)

    # Provider DUX3-11 / DUX3-22
    path = DASH / "bioetl-provider-health-v2.json"
    data = load(path)
    for panel in walk_panels(data.get("panels")):
        title = panel.get("title") or ""
        if title == "Status":
            ensure_title_prefix(panel, "[NOW·HEALTH]")
            prepend_description(
                panel,
                "DUX3-11: Selected-provider HEALTH only when provider is selected. "
                "Empty provider → N/A (not green zero success).",
            )
        if "Freshness" in title:
            ensure_title_prefix(panel, "[NOW·EVIDENCE]")
            prepend_description(
                panel,
                "DUX3-11: Freshness is EVIDENCE confidence. STALE/MISSING reduces trust; "
                "does not prove provider OK.",
            )
        if any(
            key in title
            for key in ("Healthy Checks", "Health Checks Total", "Failure Rate")
        ):
            ensure_title_prefix(panel, "[RANGE·HEALTH]")
            prepend_description(
                panel,
                "DUX3-11/03: Ratios with denominator 0 must render N/A or VALID_EMPTY — "
                "never green success 0.00%.",
            )
            changes.append(f"provider:{title} zero policy note")
        if "First Action" in title:
            prepend_description(
                panel,
                "DUX3-22: Start GLOBAL fleet matrix + freshness before selected-provider detail.",
            )
    collapse_run_context_shell(data, "provider", changes)
    for panel in walk_panels(data.get("panels")):
        title = (panel.get("title") or "").lower()
        if panel.get("type") == "row" and any(
            key in title for key in ("latency", "selected-provider", "detail")
        ):
            if not panel.get("collapsed", False):
                panel["collapsed"] = True
                changes.append(f"provider:collapse row {panel.get('title')}")
    save(path, data)

    # DQ DUX3-12 / DUX3-23
    path = DASH / "bioetl-dq-v2.json"
    data = load(path)
    for panel in walk_panels(data.get("panels")):
        title = panel.get("title") or ""
        if title == "Status":
            ensure_title_prefix(panel, "[NOW·HEALTH]")
            prepend_description(
                panel,
                "DUX3-12: NOW DQ health only. Not peer with RANGE scores or RUN accounting.",
            )
        if "Data Quality Score" in title or "Worst-Entity DQ Score" in title:
            ensure_title_prefix(panel, "[RANGE·EVIDENCE]")
            prepend_description(
                panel,
                "DUX3-12: RANGE evidence score — not a substitute for NOW status. "
                "Do not read dual 100% as “all healthy” when Status is UNKNOWN/INCOMPLETE.",
            )
            gp = panel.get("gridPos") or {}
            if int(gp.get("h") or 0) >= 6:
                gp["h"] = 4
                panel["gridPos"] = gp
                changes.append(f"dq:shrink {title}")
        if "Freshness" in title:
            ensure_title_prefix(panel, "[RANGE·EVIDENCE]")
        if "First Action" in title:
            prepend_description(
                panel,
                "DUX3-12: Prefer typed reason (VALID_EMPTY/MISSING) + handoff to Run Explorer "
                "for RUN accounting.",
            )
    collapse_run_context_shell(data, "dq", changes)
    save(path, data)

    # Trust DUX3-13 / DUX3-24
    path = DASH / "bioetl-control-plane-v1.json"
    data = load(path)
    for panel in walk_panels(data.get("panels")):
        title = panel.get("title") or ""
        if title == "Status":
            ensure_title_prefix(panel, "[NOW·HEALTH]")
            prepend_description(
                panel,
                "DUX3-13: Overall trust gate. INCOMPLETE owns headline when evidence incomplete — "
                "Safety chips are not unconditional OK.",
            )
        if "Replay Safety" in title:
            ensure_title_prefix(panel, "[NOW·EVIDENCE]")
            prepend_description(
                panel,
                "DUX3-13: Evidence-qualified safety only. OK requires coverage; known blind spots "
                "reduce confidence. Not a substitute for overall Status.",
            )
        if "Telemetry Missing" in title or (
            "Manifest" in title and "Integrity" in title
        ) or "Checkpoint Freshness" in title:
            ensure_title_prefix(panel, "[NOW·EVIDENCE]")
        if title == "Processed Records":
            prepend_description(
                panel,
                "DUX3-13/03: Expected empty/zero accounting must not use red failure semantics "
                "(VALID_EMPTY/N/A).",
            )
            fc = panel.get("fieldConfig") or {}
            defaults = fc.get("defaults") or {}
            defaults["noValue"] = defaults.get("noValue") or "N/A"
            # Prefer text over pure color for zeros
            mappings = defaults.get("mappings") or []
            has_zero_map = any(
                isinstance(m, dict)
                and m.get("type") == "value"
                and "0" in str(m.get("options") or {})
                for m in mappings
            )
            if not has_zero_map:
                mappings.append(
                    {
                        "type": "value",
                        "options": {
                            "0": {
                                "text": "VALID EMPTY / 0",
                                "color": "text",
                                "index": 0,
                            }
                        },
                    }
                )
                defaults["mappings"] = mappings
                changes.append("trust:Processed Records zero mapping")
            fc["defaults"] = defaults
            panel["fieldConfig"] = fc
        if "Empty State" in title:
            prepend_description(
                panel, "DUX3-03: Expected absence — neutral, not CRIT."
            )
    collapse_run_context_shell(data, "trust", changes)
    for panel in walk_panels(data.get("panels")):
        if panel.get("type") != "row":
            continue
        title = (panel.get("title") or "").lower()
        if any(
            key in title
            for key in ("forensic", "remaining", "identity evidence", "debug", "raw")
        ):
            if not panel.get("collapsed", False):
                panel["collapsed"] = True
                changes.append(f"trust:collapse {panel.get('title')}")
    save(path, data)

    # Incident DUX3-14
    path = DASH / "bioetl-incident-v1.json"
    data = load(path)
    for panel in walk_panels(data.get("panels")):
        title = panel.get("title") or ""
        lower = title.lower()
        if title == "Status":
            ensure_title_prefix(panel, "[NOW·HEALTH]")
            prepend_description(
                panel,
                "DUX3-14: Incident status is read-only. Ranked suspects may be WORKFLOW/GLOBAL "
                "blast radius — check scope labels on tables.",
            )
        if "suspect" in lower or "ranked" in lower or (
            "active" in lower and "alert" not in lower
        ):
            if ensure_title_prefix(panel, "[WORKFLOW·IMPACT]"):
                changes.append(f"incident:scope {title}")
            prepend_description(
                panel,
                "DUX3-14: WORKFLOW/GLOBAL impact table unless explicitly filtered to selected "
                "pipeline. Selected pipeline may differ from row pipeline (blast radius).",
            )
        if "alert" in lower and panel.get("type") in (
            "table",
            "state-timeline",
            "stat",
        ):
            if not title.startswith("["):
                ensure_title_prefix(panel, "[NOW·IMPACT]")
    save(path, data)

    # Overview DUX3-20
    path = DASH / "bioetl-overview-v2.json"
    data = load(path)
    for panel in walk_panels(data.get("panels")):
        title = panel.get("title") or ""
        if title == "Status":
            ensure_title_prefix(panel, "[NOW·HEALTH]")
            prepend_description(
                panel,
                "DUX3-20: Composite NOW health. Pair with Inputs + First Action; domain matrix "
                "stays collapsed.",
            )
        if title == "Inputs":
            ensure_title_prefix(panel, "[NOW·EVIDENCE]")
            prepend_description(
                panel,
                "DUX3-20: Domain input evidence / freshness proxies for first-screen confidence.",
            )
        if "First Action" in title:
            ensure_title_prefix(panel, "[NOW·IMPACT]")
            prepend_description(
                panel,
                "DUX3-20: ≤4 actionable CTAs with time/vars preserved.",
            )
        if title == "Provenance":
            prepend_description(
                panel,
                "DUX3 scope legend: NOW=current, RANGE=selected window, RUN=exact run_id HTTP, "
                "WORKFLOW/GLOBAL=blast radius/fleet.",
            )
    collapse_run_context_shell(data, "overview", changes)
    save(path, data)

    # Run Explorer DUX3-25
    path = DASH / "bioetl-run-explorer-v1.json"
    data = load(path)
    for panel in walk_panels(data.get("panels")):
        title = panel.get("title") or ""
        if title == "ID" or title.endswith(" ID") and "RUN" not in title:
            if title == "ID" or title.endswith("ID"):
                ensure_title_prefix(panel, "[RUN·EVIDENCE]")
                prepend_description(
                    panel,
                    "DUX3-25: Canonical RUN identity hub. Empty until run_id selected.",
                )
        if "Processed Records" in title:
            ensure_title_prefix(panel, "[RUN·EVIDENCE]")
            prepend_description(
                panel,
                "DUX3-25: Canonical RUN accounting hub. Expected empty ≠ red failure (DUX3-03).",
            )
        if "Recent" in title and "run" in title.lower():
            ensure_title_prefix(panel, "[RANGE·EVIDENCE]")
            prepend_description(
                panel,
                "DUX3-25: Browse mode — pick a run. Selected-run narrative (ID/Processed/detail) "
                "is the answer path after selection.",
            )
        if "funnel" in title.lower() or "Selected run" in title:
            ensure_title_prefix(panel, "[RUN·IMPACT]")
            prepend_description(
                panel,
                "DUX3-25: Selected-run narrative — prefer above deep browse when run_id set.",
            )
        if title == "Run Scope":
            prepend_description(
                panel,
                "DUX3-25: Empty vs selected modes. run_id is Ops HTTP only — never a Prometheus "
                "label.",
            )
    save(path, data)

    print(f"applied {len(changes)} change markers")
    for item in changes:
        print(f" - {item}")


if __name__ == "__main__":
    main()
