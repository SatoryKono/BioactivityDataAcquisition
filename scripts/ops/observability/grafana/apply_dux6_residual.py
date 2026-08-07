#!/usr/bin/env python3
"""Apply DUX6 residual (live/pixel enforcement after closed DUX5).

Epic #7139. Builds on apply_dux5_residual + _fix_no_scroll_triage_panels.
Does not invent metrics, rename contract titles, or change L0 UNKNOWN tokens.

Run from repo root:

    PYTHONPATH=. python scripts/ops/observability/grafana/apply_dux6_residual.py
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"
DOCS = ROOT / "docs" / "03-guides" / "dashboards"

NAV_ID = 1000
MARKER = "DUX6:"
PRIMARY_STATUS_IDS = {9401, 214}

# Grafana payloads are recursively heterogeneous JSON documents.  Keep the
# dynamic value type at this file-format mutation boundary.
type JsonObject = dict[str, Any]

RUN_SCOPE_HTML = (
    '<div style="padding:2px 6px;border-left:3px solid #64748b;'
    "background:rgba(100,116,139,0.10);line-height:1.2;font-size:12px;"
    'overflow:hidden">'
    "<strong>Run Explorer</strong> · pick recent run → ID → accounting → actions. "
    "Exact-run forensic owner. Full paths live in report artifacts, not triage bodies."
    "</div>"
)

NEXT_ACTIONS_HTML = (
    '<div style="padding:2px 8px;line-height:1.25;font-size:12px;overflow:hidden">'
    "<strong>Next actions (≤4)</strong> — "
    "1) Pick recent run · "
    "2) Verify ID + Processed Records · "
    "3) Expand funnel/reasons/artifacts · "
    "4) Trust Review First Recovery Action for resume/replay"
    "</div>"
)

# Compact handoff panels (markdown → short HTML)
HANDOFF_COMPACT: dict[str, dict[str, str]] = {
    "bioetl-dq-v2": {
        "Review: Lineage Handoff to Control Plane": (
            '<div style="padding:2px 8px;font-size:12px;line-height:1.25;overflow:hidden">'
            "<strong>Lineage handoff</strong> — open Trust/Control Plane for lineage trust, "
            "checkpoint integrity, and replay blockers. Preserve time range + pipeline scope."
            "</div>"
        ),
        "Review: Aggregate Control-plane Handoff": (
            '<div style="padding:2px 8px;font-size:12px;line-height:1.25;overflow:hidden">'
            "<strong>Aggregate control-plane handoff</strong> — open Trust for store/manifest "
            "failures and fleet-wide control-plane reliability. Use when DQ impact is global."
            "</div>"
        ),
    },
    "bioetl-runtime": {
        "Review Runtime-owned escalation": (
            '<div style="padding:2px 8px;font-size:12px;line-height:1.25;overflow:hidden">'
            "<strong>Runtime escalation</strong> — blockers + phase evidence first; then "
            "Incident for multi-domain blast radius; Run Explorer for exact-run proof."
            "</div>"
        ),
        "Review Cross-domain handoffs": (
            '<div style="padding:2px 8px;font-size:12px;line-height:1.25;overflow:hidden">'
            "<strong>Cross-domain handoffs</strong> — Provider (deps) · DQ (rejects) · "
            "Trust (replay) · Incident (ranked triage). Preserve scope variables."
            "</div>"
        ),
        "Review Process-level signals (GLOBAL)": (
            '<div style="padding:2px 8px;font-size:12px;line-height:1.25;overflow:hidden">'
            "<strong>Process-level (GLOBAL)</strong> — memory/error process signals are "
            "fleet evidence, not selected-run health. Pair with pipeline Status."
            "</div>"
        ),
    },
}


def _object_copy(value: object) -> JsonObject:
    if not isinstance(value, dict):
        return {}
    return cast(JsonObject, value.copy())


def _object_list(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [cast(JsonObject, item) for item in value if isinstance(item, dict)]


def walk(
    panels: list[JsonObject] | None, acc: list[JsonObject] | None = None
) -> list[JsonObject]:
    acc = acc if acc is not None else []
    for panel in panels or []:
        acc.append(panel)
        if panel.get("panels"):
            walk(panel["panels"], acc)
    return acc


def load(path: Path) -> JsonObject:
    return cast(JsonObject, json.loads(path.read_text(encoding="utf-8")))


def save(path: Path, data: JsonObject) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    os.replace(tmp, path)


def prepend_description(panel: dict[str, Any], sentence: str) -> bool:
    desc = panel.get("description") or ""
    if sentence[:36] in desc:
        return False
    panel["description"] = f"{sentence} {desc}".strip()
    return True


def set_html(panel: dict[str, Any], content: str) -> None:
    opts = _object_copy(panel.get("options"))
    links = opts.get("dataLinks")
    opts["mode"] = "html"
    opts["content"] = content
    if links is not None:
        opts["dataLinks"] = links
    panel["options"] = opts


def ensure_value_display_name(panel: dict[str, Any], display: str = "Count") -> bool:
    if panel.get("type") not in {"table", "table-old"}:
        return False
    fc = _object_copy(panel.get("fieldConfig"))
    overrides = _object_list(fc.get("overrides"))
    changed = False
    matcher_re = r"^(Value|#Value|Value \(.*\)|value|Value #.*)$"
    found = False
    for ov in overrides:
        matcher = ov.get("matcher") or {}
        if matcher.get("id") == "byRegexp" and "Value" in str(
            matcher.get("options") or ""
        ):
            found = True
            props = _object_list(ov.get("properties"))
            if not any(p.get("id") == "displayName" for p in props):
                props.append({"id": "displayName", "value": display})
                ov["properties"] = props
                changed = True
    if not found:
        overrides.append(
            {
                "matcher": {"id": "byRegexp", "options": matcher_re},
                "properties": [{"id": "displayName", "value": display}],
            }
        )
        changed = True
    # organize rename for Value #*
    transforms = _object_list(panel.get("transformations"))
    for tr in transforms:
        if tr.get("id") != "organize":
            continue
        opts = _object_copy(tr.get("options"))
        rename = _object_copy(opts.get("renameByName"))
        for key in ("Value", "Value #A", "Value #B", "Value #C", "Value #J"):
            if key in rename or key == "Value":
                target = (
                    display if key == "Value" else key.replace("Value #", "Series ")
                )
                if rename.get(key) != target and (
                    not rename.get(key) or str(rename.get(key)).startswith("Value")
                ):
                    rename[key] = target
                    changed = True
        if rename:
            opts["renameByName"] = rename
            tr["options"] = opts
    if transforms:
        panel["transformations"] = transforms
    if changed:
        fc["overrides"] = overrides
        panel["fieldConfig"] = fc
    return changed


def hide_path_columns(panel: dict[str, Any]) -> bool:
    """Hide raw path columns on browse/artifact tables (DUX6-06/21)."""
    title = (panel.get("title") or "").lower()
    if panel.get("type") not in {"table", "table-old"}:
        return False
    if not any(k in title for k in ("browse", "recent", "artifact")):
        return False
    transforms = _object_list(panel.get("transformations"))
    organize = None
    for tr in transforms:
        if tr.get("id") == "organize":
            organize = tr
            break
    if organize is None:
        organize = {"id": "organize", "options": {}}
        transforms.append(organize)
    opts = _object_copy(organize.get("options"))
    exclude = _object_copy(opts.get("excludeByName"))
    rename = _object_copy(opts.get("renameByName"))
    changed = False
    for col in (
        "json_path",
        "markdown_path",
        "path",
        "report_path",
        "artifact_path",
    ):
        if not exclude.get(col):
            exclude[col] = True
            changed = True
    # Prefer operator headers
    for src, dst in (
        ("completed_at", "Completed"),
        ("run_id", "Run"),
        ("pipeline", "Pipeline"),
        ("status", "Status"),
        ("kind", "Artifact"),
        ("name", "Artifact"),
    ):
        if rename.get(src) != dst:
            rename[src] = dst
            changed = True
    opts["excludeByName"] = exclude
    opts["renameByName"] = rename
    organize["options"] = opts
    panel["transformations"] = transforms
    options = _object_copy(panel.get("options"))
    if options.get("cellHeight") != "sm":
        options["cellHeight"] = "sm"
        panel["options"] = options
        changed = True
    return changed


def soft_evidence_stat_colors(panel: dict[str, Any]) -> bool:
    if panel.get("type") != "stat":
        return False
    if panel.get("id") in PRIMARY_STATUS_IDS:
        return False
    title = panel.get("title") or ""
    if title == "Status" or "Replay Safety" in title:
        return False
    if "Freshness" in title or "Telemetry" in title:
        return False
    opts = _object_copy(panel.get("options"))
    if opts.get("colorMode") != "background":
        return False
    if any(
        k in title
        for k in (
            "Reject",
            "Quarantine",
            "Blocked",
            "Failure",
            "No-Records",
            "Alert Conditions",
            "Lag",
            "Score",
            "Records",
            "Mismatch",
        )
    ):
        opts["colorMode"] = "value"
        panel["options"] = opts
        return True
    return False


def compress_percent_decimals(panel: dict[str, Any]) -> bool:
    fc = _object_copy(panel.get("fieldConfig"))
    defaults = _object_copy(fc.get("defaults"))
    unit = defaults.get("unit")
    decimals = defaults.get("decimals")
    if unit not in {"percent", "percentunit"}:
        return False
    if decimals is None or int(decimals) <= 0:
        return False
    defaults["decimals"] = 0
    fc["defaults"] = defaults
    panel["fieldConfig"] = fc
    return True


def annotate_unknown_status(panel: dict[str, Any]) -> bool:
    title = panel.get("title") or ""
    if panel.get("id") in PRIMARY_STATUS_IDS or title in {
        "Status",
        "Now · DQ Threshold State",
        "Monitor Provider Telemetry Freshness",
        "Triage Alert State",
    }:
        return prepend_description(
            panel,
            f"{MARKER} UNKNOWN = evidence incomplete "
            "(missing/stale/not-started/backend-error/selection). "
            "Pair with Provenance reason + action; never read as OK.",
        )
    return False


def annotate_zero_applicability(panel: dict[str, Any]) -> bool:
    title = panel.get("title") or ""
    if not any(
        k in title
        for k in (
            "Blocked",
            "Quarantine",
            "Reject",
            "Processed",
            "Silver",
            "Gold",
            "Failure Rate",
            "Mismatch",
            "No-Records",
        )
    ):
        return False
    return prepend_description(
        panel,
        f"{MARKER} zero/empty = none observed, Not started, or Not available — "
        "never bare success; red only for validated failure (not lifecycle zero).",
    )


def annotate_empty_chart(panel: dict[str, Any]) -> bool:
    if panel.get("type") not in {
        "timeseries",
        "bargauge",
        "histogram",
        "heatmap",
        "piechart",
    }:
        return False
    return prepend_description(
        panel,
        f"{MARKER} empty chart: distinguish none observed in range vs telemetry missing; "
        "do not treat No data as healthy 0 without basis.",
    )


def rewrite_novalue_developer_tokens(panel: dict[str, Any]) -> bool:
    """Soften developer-facing noValue where tests allow."""
    fc = _object_copy(panel.get("fieldConfig"))
    defaults = _object_copy(fc.get("defaults"))
    no_value = defaults.get("noValue")
    if not isinstance(no_value, str):
        return False
    # Identity/noValue contracts (RF004 / metric-semantics) must stay intact.
    if no_value.startswith("Not resolved") or no_value.startswith("NOT RESOLVED"):
        return False
    if no_value in {
        "UNKNOWN",
        "0",
        "N/A",
        "NO DATA — empty report section, UNRESOLVED_SCOPE, or BACKEND_ERROR. Check /health/live and run_id.",
    }:
        return False
    if panel.get("id") in {9402, 9300} or (panel.get("title") or "") == "ID":
        return False
    if "VALID_EMPTY" in no_value or no_value.lower().startswith("valid empty"):
        defaults["noValue"] = "None observed"
        fc["defaults"] = defaults
        panel["fieldConfig"] = fc
        return True
    if no_value in {"No data", "no data", "NO DATA"}:
        defaults["noValue"] = "No samples"
        fc["defaults"] = defaults
        panel["fieldConfig"] = fc
        return True
    return False


def collapse_run_context(data: dict[str, Any]) -> bool:
    if data.get("uid") == "bioetl-run-explorer-v1":
        return False
    changed = False
    for panel in walk(data.get("panels")):
        if panel.get("type") != "row":
            continue
        title = (panel.get("title") or "").lower()
        if "run context" in title and not panel.get("collapsed", False):
            panel["collapsed"] = True
            changed = True
    return changed


def apply_board(path: Path) -> list[str]:
    data = load(path)
    uid = str(data.get("uid") or path.stem)
    changes: list[str] = []
    if collapse_run_context(data):
        changes.append(f"{uid}:run-context-collapsed")

    handoffs = HANDOFF_COMPACT.get(uid, {})

    for panel in walk(data.get("panels")):
        if panel.get("type") == "row":
            continue
        title = panel.get("title") or ""
        pid = panel.get("id")

        if pid == NAV_ID:
            continue

        # Run Explorer orientation / actions
        if uid == "bioetl-run-explorer-v1":
            if title == "Run Scope" or pid == 1:
                set_html(panel, RUN_SCOPE_HTML)
                changes.append(f"{uid}:Run Scope compact")
            if title.startswith("Next actions"):
                set_html(panel, NEXT_ACTIONS_HTML)
                changes.append(f"{uid}:Next actions compact")

        if title in handoffs:
            set_html(panel, handoffs[title])
            prepend_description(
                panel,
                f"{MARKER} handoff copy compacted; full runbook in description/docs.",
            )
            changes.append(f"{uid}:{title}:handoff-compact")

        # Text: strip residual developer tokens / endpoints
        if panel.get("type") == "text":
            opts = _object_copy(panel.get("options"))
            content = opts.get("content")
            if isinstance(content, str):
                new = content
                new = re.sub(
                    r"VALID_EMPTY\s*[—\-–]?\s*", "No active items — ", new, flags=re.I
                )
                new = re.sub(r"###\s*", "", new)
                new = re.sub(
                    r"`?GET\s+/ops/observability/[^\s`)]+`?",
                    "Open run report",
                    new,
                    flags=re.I,
                )
                if new != content:
                    opts["content"] = new
                    panel["options"] = opts
                    changes.append(f"{uid}:{title}:text-clean")

        if ensure_value_display_name(
            panel,
            display=(
                # NOSONAR - S3358: nested ternary is intentional for display classification
                "Severity"
                if "alert" in title.lower()
                else "Signal"
                if "suspect" in title.lower()
                else "Count"
            ),
        ):
            changes.append(f"{uid}:{title}:value-label")

        if hide_path_columns(panel):
            prepend_description(
                panel,
                f"{MARKER} raw paths hidden; use Open/report artifact for full path (short scan).",
            )
            changes.append(f"{uid}:{title}:hide-paths")

        if soft_evidence_stat_colors(panel):
            changes.append(f"{uid}:{title}:colorMode-value")
        if compress_percent_decimals(panel):
            changes.append(f"{uid}:{title}:decimals0")
        if annotate_unknown_status(panel):
            changes.append(f"{uid}:{title}:unknown-grammar")
        if annotate_zero_applicability(panel):
            changes.append(f"{uid}:{title}:zero-grammar")
        if annotate_empty_chart(panel):
            changes.append(f"{uid}:{title}:empty-chart")
        if rewrite_novalue_developer_tokens(panel):
            changes.append(f"{uid}:{title}:novalue")

        # Identity short-form guidance
        if panel.get("type") == "table" and any(
            k in title.lower() for k in ("id", "identity", "manifest")
        ):
            if prepend_description(
                panel,
                f"{MARKER} prefer short run/manifest display; full value via tooltip/Copy/Open; "
                "never put full UUIDs into Prometheus labels.",
            ):
                changes.append(f"{uid}:{title}:short-id")

    if changes:
        save(path, data)
    return changes


def write_docs() -> list[str]:
    written: list[str] = []
    residual = DOCS / "dux6-residual-readability.md"
    residual.write_text(
        """# DUX6 residual readability (post-DUX5 re-audit)

**Status:** active
**Epic:** #7139
**Predecessor:** DUX5 #7116 (closed)

## Intent

DUX5 closed contract/copy residual. DUX6 enforces **pixel/operator residual** from the
re-submitted screenshot audit (SG-01..SG-07):

- UNKNOWN always paired with reason class (description + Provenance)
- triage text fits without internal scroll
- Value columns labelled; paths hidden on browse/artifacts
- evidence stats prefer value color over full-surface green/red
- empty charts distinguish none-observed vs missing telemetry
- integer percent precision; zero applicability grammar

## Applicators

1. `scripts/ops/observability/grafana/apply_dux5_residual.py`
1. `scripts/ops/observability/grafana/_fix_no_scroll_triage_panels.py`
1. `scripts/ops/observability/grafana/apply_dux6_residual.py`
1. `scripts/ops/observability/grafana/render_nav_bus.py`

## Copy SSOT

- [dux5-copy-dictionary.md](dux5-copy-dictionary.md)
- [dux5-screenshot-regression-protocol.md](dux5-screenshot-regression-protocol.md)
- [verdict-ontology.md](verdict-ontology.md)

## Title policy

Panel titles with `Monitor:` / `Track:` / `Inspect:` remain contract-stable (DUX4-01 Approach B).

## L0 tokens

Status enum tokens stay `OK/WARN/CRIT/UNKNOWN/INCOMPLETE` for metric-semantics tests.
Operator expansion lives in Provenance + descriptions.

## Residual still live-only

- WCAG contrast computation on real theme tokens
- Keyboard/focus a11y walkthrough
- Light theme parity (or explicit unsupported)
- True Copy button UX if Grafana panel plugin cannot provide it (use data links / explorer)
""",
        encoding="utf-8",
        newline="\n",
    )
    written.append(str(residual.relative_to(ROOT)))

    # Extend copy dictionary with DUX6 pointer
    copy_dict = DOCS / "dux5-copy-dictionary.md"
    text = copy_dict.read_text(encoding="utf-8")
    if "dux6-residual-readability.md" not in text:
        copy_dict.write_text(
            text.rstrip() + "\n\n## DUX6 residual\n\n"
            "Pixel residual after re-audit: "
            "[dux6-residual-readability.md](dux6-residual-readability.md).\n",
            encoding="utf-8",
            newline="\n",
        )
        written.append(str(copy_dict.relative_to(ROOT)) + ":append")

    protocol = DOCS / "dux5-screenshot-regression-protocol.md"
    ptext = protocol.read_text(encoding="utf-8")
    if "DUX6" not in ptext:
        protocol.write_text(
            ptext.rstrip() + "\n\n## DUX6 residual matrix\n\n"
            "After DUX6 apply, re-capture SG-01..SG-07 at 1366×768 dark and assert:\n"
            "1. No internal scroll on Provenance / Review First Recovery Action / Next Best Actions / Run Scope\n"
            "2. No bare VALID_EMPTY / GET /ops in bodies\n"
            "3. Browse tables do not dominate with full paths\n"
            "4. Status still paired with Provenance reason class\n",
            encoding="utf-8",
            newline="\n",
        )
        written.append(str(protocol.relative_to(ROOT)) + ":append")
    return written


def main() -> int:
    # Ensure DUX5 + no-scroll baselines first (best effort)
    try:
        from scripts.ops.observability.grafana import apply_dux5_residual as dux5
        from scripts.ops.observability.grafana import (
            _fix_no_scroll_triage_panels as noscroll,
        )

        dux5.main()
        noscroll.main()
        print("dux5 + no-scroll baselines applied")
    except Exception as exc:  # pragma: no cover
        print(f"baseline apply skipped: {exc}")

    all_changes: list[str] = []
    for path in sorted(DASH.glob("*.json")):
        ch = apply_board(path)
        all_changes.extend(ch)
        print(f"{path.name}: {len(ch)} changes")
    docs = write_docs()
    print(f"docs: {docs}")
    print(f"total_changes: {len(all_changes)}")
    try:
        from scripts.ops.observability.grafana.render_nav_bus import main as nav_main

        nav_main()
        print("nav bus re-rendered")
    except Exception as exc:  # pragma: no cover
        print(f"nav re-render skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
