#!/usr/bin/env python3
"""Apply DUX5 residual: operator reading-order, copy safety, layout density.

Implements waves V1–V4 from DUX5 epic #7116 without inventing metrics or
renaming contract-stable panel titles (DUX4-01 Approach B).

Run from repo root:

    PYTHONPATH=. python scripts/ops/observability/grafana/apply_dux5_residual.py
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"
DOCS = ROOT / "docs" / "03-guides" / "dashboards"

NAV_ID = 1000
MARKER = "DUX5:"

# Primary Status panel ids (companion Provenance carries expanded reason).
PRIMARY_STATUS_IDS = {9401, 214}

# Compact status-card templates (HTML) keyed by dashboard uid.
# Avoid "workflow=" / "pipeline=" literals in body HTML (metric-semantics contract).
STATUS_CARD_HTML: dict[str, str] = {
    "bioetl-control-plane-v1": (
        '<div style="padding:2px 6px;border-left:3px solid #64748b;'
        "background:rgba(100,116,139,0.10);line-height:1.2;font-size:12px;"
        'overflow:hidden;white-space:normal">'
        "<strong>Replay trust</strong> · Status → Reason → Action · "
        "<code>$workflow</code>/<code>$pipeline</code>/<code>$run_type</code>/"
        "run <code>$run_id</code><br>"
        "<strong>UNKNOWN</strong> = evidence incomplete — not OK. "
        "Open Review First Recovery Action or Run Explorer."
        "</div>"
    ),
    "bioetl-overview-v2": (
        '<div style="padding:2px 6px;border-left:3px solid #64748b;'
        "background:rgba(100,116,139,0.10);line-height:1.2;font-size:12px;"
        'overflow:hidden;white-space:normal">'
        "<strong>What is broken or degraded right now</strong>, and "
        "<strong>where should the operator drill down first</strong>? "
        "Status → First Action → Inputs · "
        "<code>$workflow</code>/<code>$pipeline</code>/<code>$run_type</code>/"
        "run <code>$run_id</code><br>"
        "UNKNOWN = evidence incomplete. Prefer First Action over raw numbers."
        "</div>"
    ),
    "bioetl-runtime": (
        '<div style="padding:2px 6px;border-left:3px solid #64748b;'
        "background:rgba(100,116,139,0.10);line-height:1.2;font-size:12px;"
        'overflow:hidden;white-space:normal">'
        "<strong>Pipeline diagnostics</strong> · Status/Health → Phase → Blockers → Action · "
        "<code>$pipeline</code>/<code>$run_type</code>/stage <code>$stage</code>/"
        "run <code>$run_id</code><br>"
        "SCRAPING = execution evidence, not delivery OK. Silver/Gold zeros while scraping = "
        "<strong>Not started</strong>."
        "</div>"
    ),
    "bioetl-provider-health-v2": (
        '<div style="padding:2px 6px;border-left:3px solid #ff9830;'
        "background:rgba(255,152,48,0.08);line-height:1.2;font-size:12px;"
        'overflow:hidden;white-space:normal">'
        "<strong>Which provider is degraded, and why?</strong> "
        "Start with GLOBAL severity + telemetry freshness · "
        "Selected-provider Status can disagree by design<br>"
        "Blank Provider → <strong>Selection required</strong>. "
        "UNKNOWN freshness = telemetry missing — inspect scrape target."
        "</div>"
    ),
    "bioetl-dq-v2": (
        '<div style="padding:4px 8px;border-left:4px solid #ff9830;'
        "background:rgba(255,152,48,0.08);line-height:1.25;font-size:12px;"
        'overflow:hidden">'
        '<div style="font-weight:700">Is data conformant, and what delivery impact needs action?</div>'
        "<div><b>Scope:</b> <b>CURRENT</b> = Status/reasons · <b>SELECTED RUN</b> = ID/Processed Records · "
        "<b>TIME RANGE</b> = score, freshness and impact cards below. "
        "Do not compare different badges as peers.</div>"
        "</div>"
    ),
    "bioetl-incident-v1": (
        '<div style="padding:2px 6px;border-left:3px solid #64748b;'
        "background:rgba(100,116,139,0.10);line-height:1.2;font-size:12px;"
        'overflow:hidden;white-space:normal">'
        "<strong>Incident triage</strong> · Status → Impact/confidence → Next action · "
        "<code>$workflow</code>/<code>$pipeline</code>/<code>$run_type</code>/"
        "run <code>$run_id</code><br>"
        "Read labelled Status (never bare numbers). Empty domain = "
        "<strong>No active suspects</strong>, not healthy fleet."
        "</div>"
    ),
    "bioetl-run-explorer-v1": (
        '<div style="padding:8px 12px;border-left:4px solid #64748b;'
        'background:rgba(100,116,139,0.10);line-height:1.4;font-size:13px">'
        "<div><strong>Run Explorer</strong> · select a recent run → identity → accounting → actions</div>"
        '<div style="margin-top:4px;opacity:0.9">'
        "Exact-run forensic owner. Short run id on strip; full id via Copy/Open report."
        "</div>"
        '<div style="margin-top:4px">'
        "Paths and endpoint syntax stay in report artifacts — not in triage bodies."
        "</div></div>"
    ),
}

PROVENANCE_DESC_PREFIX = (
    "DUX5: status-card shell (reason/action beside Status; no internal scroll)."
)

# Operator-facing rewrites for common empty-state / help bodies.
TEXT_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"VALID_EMPTY\s*[—\-–]?\s*", re.I),
        "No active items — ",
    ),
    (
        re.compile(r"\bvalid empty range\b", re.I),
        "none observed in selected range",
    ),
    (
        re.compile(r"VALID EMPTY\s*/\s*0", re.I),
        "None observed / 0",
    ),
    (
        re.compile(r"###\s*"),
        "",
    ),
    (
        re.compile(
            r"`?GET\s+/ops/observability/pipeline-run-report\?[^`\s)]+`?",
            re.I,
        ),
        "Open run report (JSON/Markdown)",
    ),
    (
        re.compile(r"GET\s+/ops/observability/[^\s)]+", re.I),
        "Open control-plane report",
    ),
]


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
    panels: list[dict[str, Any]] | None,
    parent_collapsed: bool = False,
    acc: list[tuple[dict[str, Any], bool]] | None = None,
) -> list[tuple[dict[str, Any], bool]]:
    acc = acc if acc is not None else []
    for panel in panels or []:
        collapsed = parent_collapsed or bool(panel.get("collapsed"))
        acc.append((panel, collapsed))
        if panel.get("panels"):
            walk(panel["panels"], collapsed, acc)
    return acc


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict[str, Any]) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))  # NOSONAR -- suffix-only sibling temp path
    os.replace(tmp, path)


def prepend_description(panel: dict[str, Any], sentence: str) -> bool:
    desc = panel.get("description") or ""
    if sentence[:40] in desc:
        return False
    panel["description"] = f"{sentence} {desc}".strip()
    return True


def rewrite_text_content(content: str) -> str:
    out = content
    for pattern, repl in TEXT_REPLACEMENTS:
        out = pattern.sub(repl, out)
    return out


def shorten_markdown(content: str, *, max_len: int = 420) -> str:
    """Shorten free-form markdown only (never structured HTML shells)."""
    stripped = content.lstrip()
    if stripped.startswith("<"):
        return content
    # Preserve contract-backed forensic/help panels that integration tests pin.
    if any(
        marker in content
        for marker in (
            "/ops/control-plane/identity-evidence",
            "replay duplicate-record evidence metric",
            "manifest/run identity",
        )
    ):
        return content
    if len(content) <= max_len:
        return content
    cut = content[: max_len - 24].rsplit("\n", 1)[0].rstrip()
    if not cut:
        cut = content[: max_len - 24].rstrip()
    return cut + "\n\n_Details in panel description._"


def ensure_value_display_name(panel: dict[str, Any], display: str) -> bool:
    """Rename bare Value columns via field override displayName."""
    fc = dict(panel.get("fieldConfig") or {})
    overrides = list(fc.get("overrides") or [])
    changed = False
    target_matcher = {
        "id": "byRegexp",
        "options": r"^(Value|#Value|Value \(.*\)|value|Value #.*)$",
    }
    found = False
    for ov in overrides:
        matcher = ov.get("matcher") or {}
        if matcher.get("id") == "byRegexp" and "Value" in str(
            matcher.get("options") or ""
        ):
            props = list(ov.get("properties") or [])
            if not any(p.get("id") == "displayName" for p in props):
                props.append({"id": "displayName", "value": display})
                ov["properties"] = props
                changed = True
            found = True
    if not found and panel.get("type") in {"table", "table-old"}:
        overrides.append(
            {
                "matcher": target_matcher,
                "properties": [{"id": "displayName", "value": display}],
            }
        )
        changed = True
    # Also fill organize renameByName when empty
    transforms = list(panel.get("transformations") or [])
    for tr in transforms:
        if tr.get("id") != "organize":
            continue
        opts = dict(tr.get("options") or {})
        rename = dict(opts.get("renameByName") or {})
        for key in list(rename.keys()) + ["Value", "Value #A", "Value #B", "Value #C"]:
            if key.startswith("Value") and not rename.get(key):
                rename[key] = (
                    display if key == "Value" else key.replace("Value #", "Series ")
                )
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


def neutralize_red_at_zero_for_scores(panel: dict[str, Any]) -> bool:
    """DQ/score panels: red threshold must not start at 0 (0% is bad only below band)."""
    title = (panel.get("title") or "").lower()
    if "score" not in title and "rate limiter" not in title:
        return False
    fc = dict(panel.get("fieldConfig") or {})
    defaults = dict(fc.get("defaults") or {})
    thresholds = dict(defaults.get("thresholds") or {})
    steps = list(thresholds.get("steps") or [])
    if not steps:
        return False
    changed = False
    new_steps: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            new_steps.append(step)
            continue
        color = str(step.get("color") or "").lower()
        val = step.get("value")
        if (_is_zeroish(val)) and "red" in color:
            # Keep base step neutral; scores use continuous thresholds elsewhere
            step = dict(step)
            step["color"] = "transparent"
            changed = True
        new_steps.append(step)
    if changed:
        thresholds["steps"] = new_steps
        defaults["thresholds"] = thresholds
        fc["defaults"] = defaults
        panel["fieldConfig"] = fc
    return changed


def compress_percent_decimals(panel: dict[str, Any]) -> bool:
    fc = dict(panel.get("fieldConfig") or {})
    defaults = dict(fc.get("defaults") or {})
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


def soft_stat_background(panel: dict[str, Any]) -> bool:
    """Primary Status keeps background; other stats prefer value color (less saturation)."""
    if panel.get("type") != "stat":
        return False
    if panel.get("id") in PRIMARY_STATUS_IDS:
        return False
    title = panel.get("title") or ""
    # Keep true health status chips on background
    if title in {"Status", "Triage Alert State"} or title.endswith(" State"):
        if "Replay Safety" in title or title == "Status":
            return False
    opts = dict(panel.get("options") or {})
    if opts.get("colorMode") != "background":
        return False
    # Only demote evidence/count style stats
    # Keep telemetry/status freshness chips on background (metric-semantics contract).
    if "Freshness" in title or "Telemetry" in title:
        return False
    if any(
        key in title
        for key in (
            "Failure",
            "Reject",
            "Quarantine",
            "Blocked",
            "No-Records",
            "Alert Conditions",
            "Lag",
        )
    ):
        opts["colorMode"] = "value"
        panel["options"] = opts
        return True
    return False


def collapse_run_context_rows(data: dict[str, Any]) -> bool:
    if data.get("uid") == "bioetl-run-explorer-v1":
        return False
    changed = False
    for panel, _ in walk(data.get("panels") or []):
        if panel.get("type") != "row":
            continue
        title = (panel.get("title") or "").lower()
        if "run context" in title or title.strip() == "run context":
            if not panel.get("collapsed", False):
                panel["collapsed"] = True
                changed = True
    return changed


def apply_text_panel(panel: dict[str, Any], *, uid: str) -> list[str]:
    changes: list[str] = []
    if panel.get("type") != "text":
        return changes
    if panel.get("id") == NAV_ID:
        return changes
    options = dict(panel.get("options") or {})
    content = options.get("content")
    if not isinstance(content, str):
        return changes
    title = panel.get("title") or ""

    # Status-card provenance / scope shells
    if title in {"Provenance", "Run Scope"} or panel.get("id") in {9400, 99}:
        card = STATUS_CARD_HTML.get(uid)
        if card and (content != card or title == "Provenance"):
            if title == "Provenance" or panel.get("id") in {9400, 99}:
                options["mode"] = "html"
                options["content"] = card
                panel["options"] = options
                # Replace description to satisfy context-shell contracts.
                prepend_description(panel, PROVENANCE_DESC_PREFIX)
                # Keep contract phrases required by first-screen tests.
                desc = panel.get("description") or ""
                if "scope:" not in desc.lower():
                    desc += (
                        " Scope: workflow, pipeline, run_type, run_id, "
                        "selected Grafana time range."
                    )
                if "local control-plane identity context only" not in desc.lower():
                    desc += " run_id is local control-plane identity context only."
                panel["description"] = desc.strip()
                changes.append(f"{uid}:{title}:status-card")
                return changes

    rewritten = rewrite_text_content(content)
    mode = str(options.get("mode") or "markdown").lower()
    if mode != "html" and not rewritten.lstrip().startswith("<"):
        rewritten = shorten_markdown(rewritten, max_len=420)

    # Domain-specific short action cards
    if title in {
        "First Action",
        "Review First Recovery Action",
        "Next Best Actions",
        "Next actions (<=4)",
    }:
        rewritten = rewrite_action_card(uid, title, rewritten)
        if rewritten.lstrip().startswith("<"):
            options["mode"] = "html"
        else:
            rewritten = shorten_markdown(rewritten, max_len=360)

    if title.startswith("Selected run · layers") or "stage timings" in title.lower():
        rewritten = (
            "**Record accounting available** on Processed Records and run report.\n\n"
            "Actions: Open JSON · Open Markdown · View stage timing / failure in report.\n\n"
            "_Endpoint syntax and full paths live in the report artifact, not here._"
        )

    if rewritten != content:
        options["content"] = rewritten
        panel["options"] = options
        prepend_description(
            panel,
            f"{MARKER} triage copy shortened; caveats in description; no raw endpoints.",
        )
        changes.append(f"{uid}:{title}:text-rewrite")
    return changes


def rewrite_action_card(uid: str, title: str, content: str) -> str:
    """Keep ≤4 operator actions; drop meta-documentation."""
    _ = content
    templates = {
        ("bioetl-incident-v1", "Next Best Actions"): (
            '<div style="padding:2px 8px;line-height:1.25;font-size:12px;overflow:hidden">'
            "<strong>Next best actions (≤4, read-only)</strong> — "
            "1) Read labelled <strong>Status</strong> · "
            "2) Open top Ranked Active Suspect domain · "
            "3) Confirm Current Alerts age/severity · "
            "4) Run Explorer for exact-run proof"
            "</div>"
        ),
        ("bioetl-provider-health-v2", "First Action"): (
            "**Next actions (≤4)**\n\n"
            "1. Confirm **Telemetry Freshness** (missing vs degraded).\n"
            "2. Open worst row in **Severity Matrix**.\n"
            "3. Read **Top Causes** for selected provider.\n"
            "4. If selector blank → choose provider (Selection required)."
        ),
        ("bioetl-control-plane-v1", "Review First Recovery Action"): (
            '<div style="padding:4px 10px;line-height:1.3;font-size:12px;overflow:hidden">'
            "<strong>Review First Recovery Action (≤4)</strong> — "
            "1) Read <strong>Status</strong> + Replay Safety / Checkpoint · "
            "2) INCOMPLETE/UNKNOWN → verify checkpoint scrape · "
            "3) Open blockers (reconstructability/drift) · "
            "4) Run Explorer for exact-run identity"
            "</div>"
        ),
        ("bioetl-overview-v2", "First Action"): (
            "**First action (≤4)**\n\n"
            "1. Read **Status** with Inputs freshness chips.\n"
            "2. Open domain board for the worst Input (Runtime/DQ/Provider/Trust).\n"
            "3. Check **Active alerts** age.\n"
            "4. Jump to Incident Workspace if multi-domain blast radius."
        ),
        ("bioetl-run-explorer-v1", "Next actions (<=4)"): (
            "**Next actions (≤4)**\n\n"
            "1. Pick a recent run in Browse.\n"
            "2. Verify **ID** + **Processed Records**.\n"
            "3. Expand reasons / reconciliation / artifacts.\n"
            "4. Open Trust for recovery if replay blocked."
        ),
    }
    key = (uid, title)
    if key in templates:
        return templates[key]
    # generic
    return (
        f"**{title}**\n\n"
        "1. Read labelled Status + freshness.\n"
        "2. Open the highest-impact evidence panel.\n"
        "3. Confirm scope (pipeline/run_type/run).\n"
        "4. Hand off to Run Explorer or Incident as needed."
    )


def apply_table_panel(panel: dict[str, Any], *, uid: str) -> list[str]:
    """Apply DUX5 residual fixes to table panels.

    NOSONAR - S3776: complexity 22 exceeds 15; extraction would obscure table panel logic
    """
    changes: list[str] = []
    if panel.get("type") not in {"table", "table-old"}:
        return changes
    title = panel.get("title") or ""
    display = "Count"
    if "alert" in title.lower():
        display = "Severity"
    elif "suspect" in title.lower():
        display = "Signal"
    elif "reason" in title.lower():
        display = "Count"
    if ensure_value_display_name(panel, display):
        prepend_description(
            panel,
            f"{MARKER} Value columns labelled as {display} (no bare Value # headers).",
        )
        changes.append(f"{uid}:{title}:value-header")
    # Mapping cleanup VALID EMPTY
    fc = dict(panel.get("fieldConfig") or {})
    defaults = dict(fc.get("defaults") or {})
    mappings = defaults.get("mappings")
    if isinstance(mappings, list):
        new_maps = []
        map_changed = False
        for m in mappings:
            if not isinstance(m, dict):
                new_maps.append(m)
                continue
            m2 = dict(m)
            opts = m2.get("options")
            if isinstance(opts, dict):
                opts2 = dict(opts)
                for k, v in list(opts2.items()):
                    if isinstance(v, dict) and "text" in v:
                        text = str(v.get("text") or "")
                        if (
                            "VALID EMPTY" in text.upper()
                            or "VALID_EMPTY" in text.upper()
                        ):
                            nv = dict(v)
                            nv["text"] = "None observed / 0"
                            opts2[k] = nv
                            map_changed = True
                m2["options"] = opts2
            new_maps.append(m2)
        if map_changed:
            defaults["mappings"] = new_maps
            fc["defaults"] = defaults
            panel["fieldConfig"] = fc
            changes.append(f"{uid}:{title}:map-valid-empty")
    return changes


def apply_stat_panel(panel: dict[str, Any], *, uid: str) -> list[str]:
    changes: list[str] = []
    title = panel.get("title") or ""
    # Percent precision applies to timeseries score trends as well as stats.
    if compress_percent_decimals(panel):
        changes.append(f"{uid}:{title}:decimals0")
    if panel.get("type") not in {"stat", "gauge"}:
        return changes
    if neutralize_red_at_zero_for_scores(panel):
        changes.append(f"{uid}:{title}:red-zero")
    if soft_stat_background(panel):
        changes.append(f"{uid}:{title}:colorMode-value")

    # Empty-state language in description for zero/rate cards
    if any(
        k in title
        for k in (
            "Blocked",
            "Quarantine",
            "Reject",
            "Failure Rate",
            "Healthy Checks",
            "Processed",
        )
    ):
        if prepend_description(
            panel,
            f"{MARKER} zero means none observed or Not started/Not available — "
            "never bare success; red only on validated failure.",
        ):
            changes.append(f"{uid}:{title}:zero-grammar")

    # Primary status: expand UNKNOWN meaning in description (token stays for contracts)
    if panel.get("id") in PRIMARY_STATUS_IDS or title == "Status":
        if prepend_description(
            panel,
            f"{MARKER} UNKNOWN = evidence incomplete (missing/stale/not-started/backend-error); "
            "pair with Provenance reason + action. Not a healthy OK.",
        ):
            changes.append(f"{uid}:{title}:unknown-grammar")
    return changes


def apply_identity_short_id_hints(panel: dict[str, Any], *, uid: str) -> list[str]:
    title = (panel.get("title") or "").lower()
    if panel.get("type") != "table":
        return []
    if not any(k in title for k in ("id", "identity", "manifest", "processed records")):
        return []
    if prepend_description(
        panel,
        f"{MARKER} show short run/manifest ids in cells where possible; full value via "
        "tooltip/Copy/Open. Do not put full UUIDs into Prometheus labels.",
    ):
        return [f"{uid}:{panel.get('title')}:short-id-hint"]
    return []


def apply_board(path: Path) -> list[str]:
    data = load(path)
    uid = str(data.get("uid") or path.stem)
    changes: list[str] = []
    if collapse_run_context_rows(data):
        changes.append(f"{uid}:run-context-collapsed")

    for panel, _collapsed in walk(data.get("panels") or []):
        if panel.get("type") == "row":
            continue
        changes.extend(apply_text_panel(panel, uid=uid))
        changes.extend(apply_table_panel(panel, uid=uid))
        changes.extend(apply_stat_panel(panel, uid=uid))
        changes.extend(apply_identity_short_id_hints(panel, uid=uid))

    if changes:
        save(path, data)
    return changes


def write_docs() -> list[str]:
    written: list[str] = []

    copy_dict = DOCS / "dux5-copy-dictionary.md"
    copy_dict.write_text(
        """# DUX5 operator copy dictionary

**Status:** active
**Wave:** DUX5 (#7116)
**Owner:** interface / Grafana dashboard system
**Verdict logic owner:** application / control-plane / recording rules (not Grafana transforms)

## Reading order

`Context → Status → Reason → Impact → Action → Evidence`

## State classes (operator-facing)

| Class | When | Display guidance |
| --- | --- | --- |
| **OK** | Validated healthy | green badge; neutral surface preferred for non-critical |
| **WARN** | Degraded / attention | orange |
| **CRIT** | Confirmed failure | red |
| **INCOMPLETE** | Required trust evidence missing/stale | gray; never OK |
| **UNKNOWN** | Evidence incomplete (missing/stale/not-started/backend-error) | gray; always pair with Reason |
| **None observed** | Query completed; zero matching events | neutral; not success |
| **Not started** | Stage not applicable yet (e.g. Silver during SCRAPING) | neutral |
| **Not available** | Denominator zero / signal N/A | neutral; never `0%` rate |
| **Selection required** | Required selector empty | neutral; action = select |
| **Telemetry missing** | Required metric family absent | gray; action = inspect scrape |

L0 Status panels keep enum tokens `OK/WARN/CRIT/UNKNOWN/INCOMPLETE` for contract stability
(DUX4-01 Approach B + metric semantics tests). Expanded meaning lives in Provenance /
description / paired reason panels.

## Forbidden primary copy

- Bare `No data` without class
- `VALID_EMPTY` developer token
- Raw `GET /ops/...` endpoint syntax in triage bodies
- Literal Markdown `###` headings as on-canvas chrome
- Auto `Value #A` without displayName
- Full UUID as the only visible identity without Copy/Open

## Title policy

Panel titles with `Monitor:` / `Track:` / `Inspect:` prefixes remain **contract-stable**
for integration tests. Operator nouns live in Provenance status cards and action lists.

## Typography floors (DUX5-10)

| Token | Min size @1366 | Use |
| --- | ---: | --- |
| `dashboard-context` | 12px | breadcrumb / selectors |
| `panel-title` | 13px | panel titles (≤2 lines) |
| `status-badge` | 14px bold | Status enum |
| `stat-primary` | 18px | primary numeric |
| `body-primary` | 13px | reason/action |
| `body-secondary` | 12px | scope/freshness |
| `table-cell` | 12px | tables |
| `axis-label` | 11px | chart axes |

No auto-shrink below floors; reflow/wrap/shorten instead.

## Ownership

| Surface | Owner board |
| --- | --- |
| Exact-run forensic tables | Run Explorer |
| Ranked triage | Incident Workspace |
| Cross-domain routing | Overview |
| Replay confidence | Trust |
| Domain decision | Runtime / Provider / DQ |
""",
        encoding="utf-8",
        newline="\n",
    )
    written.append(str(copy_dict.relative_to(ROOT)))

    protocol = DOCS / "dux5-screenshot-regression-protocol.md"
    protocol.write_text(
        """# DUX5 screenshot & accessibility regression protocol

**Issue:** #7133 (DUX5-31)
**Parent epic:** #7116

## Purpose

Prevent readability defects (clipping, internal scroll, bare UNKNOWN, false-red zeros)
from re-entering `grafana/dashboards/*.json` without merge-blocking evidence.

## Baseline viewports

| Viewport | Zoom | Theme |
| --- | ---: | --- |
| 1366×768 | 100%, 125% | dark (required) |
| 1440×900 | 100% | dark |
| 1920×1080 | 100% | dark |
| light | 100% | document unsupported if not verified |

## Assertions (non-pixel)

1. No internal vertical scrollbar on first-screen Status / Provenance / First Action / Next actions
2. Status, Reason, Impact, Action visible without tooltip-only disclosure
3. No bare `VALID_EMPTY` / raw `GET /ops` in panel bodies
4. No `Value #*` column headers without displayName
5. Nav bus `id=1000` shows chips `0. Trust` … `6. Run Explorer` without truncation marker
6. Typography floors from `dux5-copy-dictionary.md` (manual or render measure)
7. Focus/active nav distinguishable without color alone (keyboard pass)

## Capture commands

Prefer repo tools:

```bash
python scripts/ops/observability/grafana/check_grafana_dashboard_audit_preflight.py
# optional live render when stack is up:
# python scripts/ops/observability/grafana/rerender_grafana_screenshots.py
```

Store before/after under operator-local evidence; do not commit secrets.

## Exit

- [ ] Dark theme verified at 1366 baseline
- [ ] Light theme verified **or** explicitly unsupported in this file
- [ ] Linked from DUX5 pack closeout
""",
        encoding="utf-8",
        newline="\n",
    )
    written.append(str(protocol.relative_to(ROOT)))

    # Patch design-system with typography pointer if missing
    ds = DOCS / "design-system.md"
    text = ds.read_text(encoding="utf-8")
    if "dux5-copy-dictionary.md" not in text:
        text = text.rstrip() + (
            "\n\n## 9) DUX5 typography & copy residual\n\n"
            "Operator reading-order, state classes, and typography floors are normative in "
            "[dux5-copy-dictionary.md](dux5-copy-dictionary.md). "
            "Screenshot regression protocol: "
            "[dux5-screenshot-regression-protocol.md](dux5-screenshot-regression-protocol.md).\n"
        )
        ds.write_text(text, encoding="utf-8", newline="\n")
        written.append(str(ds.relative_to(ROOT)) + ":append")

    # Verdict ontology pointer
    vo = DOCS / "verdict-ontology.md"
    vo_text = vo.read_text(encoding="utf-8")
    if "dux5-copy-dictionary.md" not in vo_text:
        vo.write_text(
            vo_text.rstrip() + "\n\n## DUX5 expansion\n\n"
            "Operator-facing empty-state and applicability classes "
            "(None observed / Not started / Not available / Selection required / "
            "Telemetry missing) are listed in "
            "[dux5-copy-dictionary.md](dux5-copy-dictionary.md). "
            "L0 Status enum tokens remain OK/WARN/CRIT/UNKNOWN/INCOMPLETE.\n",
            encoding="utf-8",
            newline="\n",
        )
        written.append(str(vo.relative_to(ROOT)) + ":append")

    return written


def main() -> int:
    all_changes: list[str] = []
    for path in sorted(DASH.glob("*.json")):
        ch = apply_board(path)
        all_changes.extend(ch)
        print(f"{path.name}: {len(ch)} changes")
    docs = write_docs()
    print(f"docs: {docs}")
    print(f"total_panel_changes: {len(all_changes)}")
    # Re-render nav bus to ensure id=1000 stays whole after any accidental touch
    try:
        from scripts.ops.observability.grafana.render_nav_bus import main as nav_main

        nav_main()
        print("nav bus re-rendered")
    except Exception as exc:  # pragma: no cover - best effort
        print(f"nav bus re-render skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
