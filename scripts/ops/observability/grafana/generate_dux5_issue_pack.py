#!/usr/bin/env python3
"""Generate DUX5 issue pack + body files from screenshot UX audit roadmap."""

from __future__ import annotations

import json
from pathlib import Path
from collections import Counter
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[4]


def left_strip_block(text: str) -> str:
    """Strip the modal leading indent from indented lines only.

    Unlike ``textwrap.dedent``, unindented inserted fragments (tables, f-string
    interpolations) do not collapse the common indent to zero.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    indents = [
        len(line) - len(line.lstrip(" "))
        for line in lines
        if line.strip() and line.startswith(" ")
    ]
    if not indents:
        return text
    common = Counter(indents).most_common(1)[0][0]
    out: list[str] = []
    for line in lines:
        if line.startswith(" " * common):
            out.append(line[common:])
        else:
            out.append(line)
    return "\n".join(out)


ISSUES = ROOT / ".github" / "ISSUES"
BODIES = ISSUES / "_dux5_bodies"
PACK = ISSUES / "DUX5-2026-07-29-DASHBOARD-TYPOGRAPHY-READING-ORDER-ISSUE-PACK.md"
ROADMAP = ROOT / "reports" / "quality" / "_ux_audit_roadmap_parsed.json"

CODE_MAP = {
    "UX-P0-01": "DUX5-01",
    "UX-P0-02": "DUX5-02",
    "UX-P0-03": "DUX5-03",
    "UX-P0-04": "DUX5-04",
    "UX-P0-05": "DUX5-05",
    "UX-P0-06": "DUX5-06",
    "UX-P1-01": "DUX5-10",
    "UX-P1-02": "DUX5-11",
    "UX-P1-03": "DUX5-12",
    "UX-P1-04": "DUX5-13",
    "UX-P1-05": "DUX5-14",
    "UX-P2-01": "DUX5-20",
    "UX-P2-02": "DUX5-21",
    "UX-P2-03": "DUX5-22",
    "UX-P2-04": "DUX5-23",
    "UX-P3-01": "DUX5-30",
    "UX-P3-02": "DUX5-31",
}

WAVE_MAP = {"P0": "V1", "P1": "V2", "P2": "V3", "P3": "V4"}

PREFIX = {
    "DUX5-01": "feat(grafana)",
    "DUX5-02": "refactor(grafana)",
    "DUX5-03": "fix(grafana)",
    "DUX5-04": "fix(grafana)",
    "DUX5-05": "fix(grafana)",
    "DUX5-06": "feat(grafana)",
    "DUX5-10": "chore(grafana)",
    "DUX5-11": "feat(grafana)",
    "DUX5-12": "refactor(grafana)",
    "DUX5-13": "refactor(grafana)",
    "DUX5-14": "refactor(grafana)",
    "DUX5-20": "docs(grafana)",
    "DUX5-21": "refactor(grafana)",
    "DUX5-22": "refactor(grafana)",
    "DUX5-23": "fix(grafana)",
    "DUX5-30": "docs(grafana)",
    "DUX5-31": "test(grafana)",
}

OVERLAP = {
    "DUX5-01": (
        "Extends DUX4-12/13/14 + verdict-ontology into operator-visible state "
        "classes (missing/stale/not-started/valid-empty/backend-error)."
    ),
    "DUX5-02": (
        "Hardens DUX4-22: screenshot audit still shows internal scroll on "
        "mandatory triage panels."
    ),
    "DUX5-03": (
        "Hardens DUX4-12/14 red-zero / applicability; screenshots show red "
        "Silver zeros during SCRAPING."
    ),
    "DUX5-04": (
        "New residual: literal Markdown, metric/copy mismatch, exposed "
        "endpoints (Provider/Overview/Trust/Run Explorer)."
    ),
    "DUX5-05": (
        "New residual: Value #* headers + clipping (Incident/Pipeline/Run/Trust)."
    ),
    "DUX5-06": (
        "Related to DUX4-25/30 density; adds short-ID + Copy without Prom cardinality."
    ),
    "DUX5-10": (
        "Related to DUX4-40 token contract; typography floors + no auto-shrink "
        "below min."
    ),
    "DUX5-11": (
        "Implements first-screen status card pattern "
        "(state x reason x impact x action) as library panel."
    ),
    "DUX5-12": "Title/copy normalization after DUX4-01 title harness.",
    "DUX5-13": "Nav/selector redesign residual after DUX4-22 nav bus restore.",
    "DUX5-14": (
        "Enforces DUX4-23: compact identity strip; Run Explorer owns forensic detail."
    ),
    "DUX5-20": "Copy rewrite pass once status cards exist.",
    "DUX5-21": "Table projection residual after DUX4-25.",
    "DUX5-22": "Chart empty-state rationalization residual after DUX4-21/24.",
    "DUX5-23": "Numeric grammar residual after DUX4-12 zero/rate work.",
    "DUX5-30": "Governance after patterns stabilize.",
    "DUX5-31": "Extends DUX4-41 live screenshot regression with a11y + text floors.",
}

SCREENSHOT_GROUPS = {
    "DUX5-01": "SG-01..SG-07 (all boards)",
    "DUX5-02": "SG-01 Run Explorer, SG-02 Incident, SG-03 DQ, SG-06 Overview, SG-07 Trust",
    "DUX5-03": "SG-07 Trust Processed Records; SG-05 Pipeline; SG-03 DQ; SG-04 Provider",
    "DUX5-04": "SG-04 Provider Health; SG-06 Overview; SG-07 Trust; SG-01 Run Explorer",
    "DUX5-05": "SG-02 Incident (Value #*); SG-05 Pipeline; SG-01 Run Explorer; SG-07 Trust",
    "DUX5-06": "SG-01..SG-07 selectors + identity tables",
    "DUX5-10": "SG-01..SG-07 (systemic)",
    "DUX5-11": "SG-02..SG-07 status-dominant boards",
    "DUX5-12": "SG-01..SG-07 titles",
    "DUX5-13": "SG-01..SG-07 nav + selectors",
    "DUX5-14": "SG-03..SG-07 lower-page Run context; SG-01 remains owner",
    "DUX5-20": "SG-01, SG-02, SG-03, SG-07 verbose bodies",
    "DUX5-21": "SG-01, SG-07 dense tables",
    "DUX5-22": "SG-03, SG-04, SG-05, SG-06, SG-07 empty charts",
    "DUX5-23": "SG-03 DQ 100.00%; all zero/rate cards",
    "DUX5-30": "system / docs",
    "DUX5-31": "all screenshot groups + viewport matrix",
}


def build_titles(items: list[dict[str, str]]) -> dict[str, str]:
    titles = {
        "DUX5-00": (
            "chore(grafana): DUX5 epic — typography & operator reading-order "
            "residual (screenshot audit)"
        )
    }
    for it in items:
        dux = CODE_MAP[it["code"]]
        titles[dux] = f"{PREFIX[dux]}: {dux} {it['title']}"
    return titles


def build_meta(items: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    meta: dict[str, tuple[str, str]] = {"DUX5-00": ("meta", "epic")}
    for it in items:
        dux = CODE_MAP[it["code"]]
        meta[dux] = (it["priority"], WAVE_MAP[it["priority"]])
    return meta


def write_epic_body() -> str:
    return dedent(
        """\
        ## Summary

        Execute **DUX5** after the **read-only screenshot UX audit** (7 boards / SG-01..SG-07):
        make typography, color, and text structure enforce the operator decision order

        **what happened → why it matters → what to do → supporting evidence**.

        DUX3/DUX4 delivered contracts, description grammar, and partial visual enforcement.
        This residual audit still shows **dangerous interpretations**: bare `UNKNOWN`/`No data`/`VALID_EMPTY`,
        giant `OK`/`100.00%`/`0` without applicability, internal scroll on triage panels,
        `Value #*` headers, literal Markdown, and forensic tables repeating on every board.

        **Verdict:** WARN / redesign required (interface-layer copy + layout; no Grafana verdict logic).

        ## Mode of source audit

        - **Read-only, screenshot-based**
        - No dashboard JSON / provisioning / Prometheus / API / code changes were made during the audit
        - Image dimensions are not proof of browser viewport; live validation still required for fonts, contrast, PromQL

        ## Waves

        | Wave | Codes | Focus | Exit |
        | --- | --- | --- | --- |
        | V0 | epic + inventory | freeze roadmap + evidence anchors | pack published; screenshot inventory linked |
        | V1 | DUX5-01..06 | **P0 semantic safety of text** | no bare UNKNOWN/No data; no internal triage scroll; no false-red zero; no Value #*/raw MD; short IDs + Copy |
        | V2 | DUX5-10..14 | **P1 system patterns** | typography tokens; status card library; titles; nav; compact run strip |
        | V3 | DUX5-20..23 | **P2 density polish** | copy rewrite; forensic tables; chart empty states; numeric grammar |
        | V4 | DUX5-30..31 | **P3 governance** | copy dictionary + screenshot/a11y regression matrix |

        ## Portfolio (unchanged UIDs)

        | uid | Board | SG |
        | --- | --- | --- |
        | `bioetl-run-explorer-v1` | Run Explorer | SG-01 |
        | `bioetl-incident-v1` | Incident Workspace | SG-02 |
        | `bioetl-dq-v2` | Data Quality | SG-03 |
        | `bioetl-provider-health-v2` | Provider Health | SG-04 |
        | `bioetl-runtime` | Pipeline Diagnostics | SG-05 |
        | `bioetl-overview-v2` | Overview | SG-06 |
        | `bioetl-control-plane-v1` | Trust | SG-07 |

        ## Reading-order contract (target)

        First viewport on every domain board:

        1. **Context** — short breadcrumb + scope chips (workflow/pipeline/run_type; short run id)
        2. **Status** — labelled state (not bare UNKNOWN)
        3. **Reason** — why
        4. **Impact** — delivery/blast radius confidence
        5. **Action** — one primary CTA visible without scroll
        6. **Evidence** — supporting metrics/tables below or collapsed

        Ownership:

        - **Overview** — cross-domain routing
        - **Incident** — ranked triage
        - **Domain boards** — concise domain decisions
        - **Run Explorer** — exact-run forensic detail
        - **Trust** — replay/control-plane confidence

        ## Constraints

        - Keep **7 stable UIDs**; surgical edits to `grafana/dashboards/*.json`
        - ADR-010 optional monitoring; no required Docker/Redis for product path
        - **No invent metrics**; **no Prometheus `run_id` labels**
        - Incident remains **read-only**
        - Verdict semantics stay in application/control-plane/recording-rule contracts — Grafana only renders bounded states
        - Tech-debt budgets **must not increase**
        - Prefer library panels + field overrides before custom plugins

        ## Predecessors

        - DUX4 epic #7088 (visual enforcement residual)
        - DUX3 epic #7053 (contracts / description grammar)
        - DSA #6982 / DS2 #6901
        - `docs/03-guides/dashboards/verdict-ontology.md`
        - `docs/03-guides/dashboards/dux3-residual-contracts.md`
        - `docs/03-guides/dashboards/design-system.md`

        ## Source audit

        - Session audit: screenshot-based Grafana UX audit (2026-07-29), groups SG-01..SG-07
        - Roadmap codes: `UX-P0-01`..`UX-P3-02` (mapped to DUX5-*)
        - Parsed inventory: `reports/quality/_ux_audit_roadmap_parsed.json`
        - Evidence model: FACT / INFERENCE / UNKNOWN as in audit

        ## Out of scope

        - Greenfield rewrite / second dashboard monorepo
        - Deleting Trust or DQ UID
        - Incident write-path / owner-ack store
        - Causal MTT* claims
        - Light-theme implementation unless already supported (audit only saw dark)

        ## Publish

        After `gh issue create`, fill Issue column + `reports/quality/dux5-2026-07-29-issue-publish.json`.
        """
    )


def write_child_body(
    *,
    it: dict[str, str],
    dux: str,
    pri: str,
    wave: str,
) -> str:
    return dedent(
        f"""\
        ## Summary

        **{it["title"]}**

        {it["problem"]}

        ## Priority / wave

        - Priority: **{pri}**
        - Wave: **{wave}**
        - Complexity: **{it["complexity"]}**
        - Audit code: `{it["code"]}`
        - DUX code: `{dux}`

        ## Scope

        {it["scope"]}

        Screenshot groups: {SCREENSHOT_GROUPS[dux]}

        ## Concrete change

        {it["change"]}

        ## Expected effect

        {it["effect"]}

        ## Acceptance criteria

        - {it["acceptance"]}
        - Aligns with epic acceptance: Status/Reason/Impact/Action visible without internal scroll on first viewport
        - No new high-cardinality Prometheus labels
        - No hidden verdict logic introduced only in Grafana transforms

        ## Dependencies

        {it["deps"]}

        ## Risk

        {it["risk"]}

        ## Overlap / predecessor notes

        {OVERLAP[dux]}

        ## Constraints

        - Surgical dashboard JSON only; preserve panel IDs where possible
        - Run Explorer remains forensic owner when moving detail off domain boards
        - Prefer description/runbook for caveats; keep first-screen copy to 2-4 lines
        - Tech-debt budgets non-increasing

        ## Verification

        - [ ] Before/after screenshots for affected panels (dark theme)
        - [ ] Viewports: 1366x768, 1440x900, 1920x1080 at 100% (125% when layout-sensitive)
        - [ ] Targeted pytest for navigation/contracts if JSON structure changes
        - [ ] Manual operator 5-second comprehension check on first-screen card

        ## Parent

        DUX5 epic (`DUX5-00`)
        """
    )


def write_pack(
    *,
    items: list[dict[str, str]],
    titles: dict[str, str],
    meta: dict[str, tuple[str, str]],
) -> str:
    matrix_rows = [
        "| Code | Issue | Pri | Wave | Title |",
        "|------|-------|-----|------|-------|",
        f"| DUX5-00 | _TBD_ | meta | epic | {titles['DUX5-00']} |",
    ]
    for it in items:
        dux = CODE_MAP[it["code"]]
        pri, wave = meta[dux]
        matrix_rows.append(f"| {dux} | _TBD_ | {pri} | {wave} | {titles[dux]} |")
    matrix = "\n".join(matrix_rows)
    return left_strip_block(
        f"""\
        # Dashboard typography & operator reading-order residual — DUX5

        **Status:** prepared (local pack; GH numbers filled after publish)
        **Wave code:** DUX5
        **Date:** 2026-07-29
        **Source audit:** read-only screenshot UX audit (SG-01..SG-07; Run Explorer to Trust)
        **Predecessor wave:** DUX4 epic #7088 (visual enforcement) after DUX3 #7053
        **Baseline:** post-DUX4 working tree / local `main`
        **Audit mode:** screenshot-based only — no dashboard JSON/provisioning/Prometheus/API/code changes during audit

        ## Context

        DUX3 closed **contracts** (scope/family/typed-state grammar, shell collapse).
        DUX4 closed **visual enforcement residual** at contract/description + partial pixel level.

        A **second-pass screenshot audit** still rates the system **WARN / redesign required** because:

        1. Typography/color/text structure do **not** enforce operator decision order
        2. Largest on-screen objects are often bare `UNKNOWN` / `OK` / `SCRAPING` / `INCOMPLETE` / `100.00%` / `0`
        3. Reason, impact, confidence, and action are missing, microtext, under fold, or behind **internal scrollbars**
        4. Provider Health shows literal Markdown / copy mismatches; Incident shows `Value #*` headers
        5. Zeros can read as failure or health without **applicability**

        This wave is **DUX5 = operator reading-order + typography + copy safety**.
        It is **not** a greenfield rewrite and **not** a reopen of DUX4 as failed — it is residual evidence from screenshots.

        ## Accepted decisions (normative)

        | # | Topic | Decision |
        | --- | --- | --- |
        | 1 | Portfolio | Keep **7 stable UIDs** |
        | 2 | SOT | Surgical edits to `grafana/dashboards/*.json` after live JSON validation |
        | 3 | Reading order | Context → Status → Reason → Impact → Action → Evidence |
        | 4 | Ownership | Run Explorer = forensic detail; domain boards = concise decisions; Overview = routing; Incident = ranked triage; Trust = replay confidence |
        | 5 | Semantics | Health / Execution / Evidence / Applicability vocabularies; Grafana renders bounded states only |
        | 6 | Metrics | No invent metrics; no Prom `run_id` labels |
        | 7 | Incident | Read-only |
        | 8 | Measurement | Screenshot + geometry/text-floor assertions (no MTT*) |

        ## Screenshot inventory

        | Group | Dashboard | File | Notes |
        | --- | --- | --- | --- |
        | SG-01 | Run Explorer | `Snag_8cefdb5.png` | Tall; Record accounting partially visible |
        | SG-02 | Incident Workspace | `Snag_8cefe90.png` | First-screen-like |
        | SG-03 | Data Quality | `Snag_8cefeee.png` | ~1366-class width capture |
        | SG-04 | Provider Health | `Snag_8ceffd8.png` | Top titles may be cropped (UNKNOWN evidence) |
        | SG-05 | Pipeline Diagnostics | `Snag_8cf0084.png` | Narrow stitched; density stress |
        | SG-06 | Overview | `Snag_8cf0268.png` | Tall; unused space around Workflow status |
        | SG-07 | Trust | `Snag_8cf0334.png` | Very narrow; worst-case identity tables |

        > Image size is not a guaranteed browser viewport. Live validation required for zoom/DPR/fonts.

        ## Critical conclusions (from audit)

        ### P0

        1. Replace bare `UNKNOWN`, `No data`, `VALID_EMPTY`, `N/A`, and context-free `0` with formal **Health / Execution / Evidence / Applicability** model
        2. Remove internal vertical scroll from mandatory triage panels; Status/Reason/Impact/Action simultaneous
        3. Fix literal Markdown, auto-generated `Value #*` headers, clipping, metric/copy mismatch (Provider Health + tables)
        4. Show **Not started** for inapplicable Silver/Gold; red only for confirmed violation

        ### P1

        1. Neutral surface + icon/badge/severity strip instead of full-color stat backgrounds by default
        2. Shorten IDs/paths; add Copy/Open; full values in tooltip/explorer/URL
        3. Unified typography tokens; forbid auto-shrink below minimums

        ## Issue matrix

        {matrix}

        ## Delivery order

        1. **PR-V1 (P0 safety)** DUX5-01 → DUX5-02 → DUX5-03 → DUX5-04 → DUX5-05 → DUX5-06
           (01 semantics first; 04/05 are small surgical wins; 02/03 layout+color; 06 density)
        2. **PR-V2 (system patterns)** DUX5-10 → DUX5-11 → DUX5-12 → DUX5-13 → DUX5-14
        3. **PR-V3 (polish)** DUX5-20 → DUX5-21 → DUX5-22 → DUX5-23
        4. **PR-V4 (governance)** DUX5-30 → DUX5-31

        ## Wave exit criteria

        ### V1 (P0)

        - [ ] No primary status card shows bare `UNKNOWN` / `No data` without reason+evidence class
        - [ ] Zero internal vertical scroll on first-screen status/reason/action/scope panels at 1366/1440/1920
        - [ ] Zero is red only on validated failure; Not started / Not available labelled neutrally
        - [ ] No literal Markdown markers, `Value #*` headers, or raw GET URLs in panel bodies
        - [ ] Run/Manifest IDs short-form + Copy; no new Prom high-cardinality labels

        ### V2 (P1)

        - [ ] Typography token floors enforced (body >=13px, secondary >=12px, table >=12px, axis >=11px at 1366)
        - [ ] First-screen status card pattern on domain boards (state+reason+action visible)
        - [ ] Titles <=2 lines; nav active state distinguishable without color alone
        - [ ] Non-explorer boards use compact run strip; forensic tables owned by Run Explorer

        ### V3 (P2)

        - [ ] Primary cards pass 5-second comprehension review
        - [ ] Dense tables limited to operator columns; full evidence one click away
        - [ ] Optional empty charts collapsed/below fold
        - [ ] Numeric precision/units consistent; denom=0 → Not available

        ### V4 (P3)

        - [ ] Copy dictionary + library-panel ownership documented
        - [ ] Screenshot/a11y regression matrix runnable; dark verified; light verified or documented unsupported

        ## Epic-level acceptance (audit)

        - Status, Reason, Impact, Action, Scope, Freshness visually distinct; mandatory action without tooltip/scrollbar
        - No bare developer tokens as primary empty states
        - Full-color backgrounds not default for OK/zero; color not sole state carrier
        - WCAG 2.2 AA contrast against real theme tokens (live measure)
        - Verdict semantics not invented only in Grafana transforms

        ## Constraints / risks

        | Risk | Mitigation |
        | --- | --- |
        | Semantic oversimplification | Caveats in description/runbook; show evidence/freshness on card |
        | Plugin limits | Library panels + field overrides first |
        | Business logic drift | API/recording-rule owners + contract tests |
        | Screenshot brittleness | Assert clipping/geometry/state text ranges, not pure pixels |
        | Responsive collapse | 1366/125% is blocking baseline |
        | Loss of forensic depth | Keep Run Explorer + Copy/Open paths |

        ## Assertions still UNKNOWN (require JSON/live)

        - Exact fontSize/lineHeight/gridPos/auto-size behavior
        - Whether each scrollbar is panel vs row vs capture artifact
        - Exact WCAG ratios and theme tokens
        - PromQL/transforms/value mappings behind each state
        - Root cause of each UNKNOWN/No data
        - Whether red Silver zeros are applicability vs real violation
        - Whether Provider top titles are hidden or cropped
        - Viewport/zoom/DPR of captures
        - Keyboard/focus/aria/copy-button behavior
        - Light-theme support

        ## Rejected

        - Greenfield rewrite / second monorepo
        - Delete Trust or DQ UID
        - Incident write-path
        - Invent metrics / Prom `run_id`
        - Causal MTT* claims

        ## Evidence anchors

        - Parsed roadmap: `reports/quality/_ux_audit_roadmap_parsed.json`
        - Bodies: `.github/ISSUES/_dux5_bodies/`
        - Publish script: `.github/ISSUES/_dux5_bodies/publish_dux5_issues.py`
        - Related docs: `docs/03-guides/dashboards/verdict-ontology.md`, `design-system.md`, `operator-ux-v2.md`, `dux3-residual-contracts.md`
        - Nav bus generator: `scripts/ops/observability/grafana/render_nav_bus.py`
        - Predecessor pack: `.github/ISSUES/DUX4-2026-07-29-DASHBOARD-VISUAL-ENFORCEMENT-ISSUE-PACK.md`

        ## Publish record

        - After publish: `reports/quality/dux5-2026-07-29-issue-publish.json`
        """
    )


def write_publish_script(meta: dict[str, tuple[str, str]]) -> str:
    meta_lines = ",\n".join(
        f'    "{code}": ("{pri}", "{wave}")' for code, (pri, wave) in meta.items()
    )
    return left_strip_block(
        f'''\
        #!/usr/bin/env python3
        """Publish DUX5 epic + children via GitHub CLI and write a publish record.

        Usage (from repo root, after valid GH auth):

            python .github/ISSUES/_dux5_bodies/publish_dux5_issues.py --dry-run
            python .github/ISSUES/_dux5_bodies/publish_dux5_issues.py

        Environment:
            GH  optional path to gh.exe (default: gh on PATH)
            Prefer CODEX_GITHUB_PERSONAL_ACCESS_TOKEN when configuring gh auth.
        """

        from __future__ import annotations

        import argparse
        import json
        import os
        import re
        import subprocess
        import sys
        from datetime import datetime, timezone
        from pathlib import Path
        from typing import TypedDict

        ROOT = Path(__file__).resolve().parents[3]
        BODIES = Path(__file__).resolve().parent
        PACK = ROOT / ".github" / "ISSUES" / "DUX5-2026-07-29-DASHBOARD-TYPOGRAPHY-READING-ORDER-ISSUE-PACK.md"
        PUBLISH = ROOT / "reports" / "quality" / "dux5-2026-07-29-issue-publish.json"
        TITLES_PATH = BODIES / "TITLES.md"


        class PublishedIssue(TypedDict):
            code: str
            number: int
            priority: str
            wave: str
            url: str
            title: str


        META: dict[str, tuple[str, str]] = {{
        {meta_lines}
        }}

        CHILD_ORDER = [c for c in META if c != "DUX5-00"]


        def load_titles() -> dict[str, str]:
            titles: dict[str, str] = {{}}
            for line in TITLES_PATH.read_text(encoding="utf-8").splitlines():
                m = re.match(r"- `(DUX5-\\d+)`: `(.*)`\\s*$", line)
                if m:
                    titles[m.group(1)] = m.group(2)
            missing = set(META) - set(titles)
            if missing:
                raise SystemExit(f"missing titles for: {{sorted(missing)}}")
            return titles


        def resolve_gh() -> str:
            explicit = os.environ.get("GH")
            if explicit:
                return explicit
            for candidate in (
                r"C:\\Program Files\\GitHub CLI\\gh.exe",
                "/c/Program Files/GitHub CLI/gh.exe",
                "gh",
            ):
                if candidate == "gh":
                    return candidate
                if Path(candidate).exists():
                    return candidate
            return "gh"


        def run_gh(gh: str, args: list[str], *, dry_run: bool) -> str:
            cmd = [gh, *args]
            if dry_run:
                print("DRY-RUN:", " ".join(cmd))
                return "https://github.com/example/repo/issues/0"
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                raise SystemExit(
                    f"gh failed ({{proc.returncode}}): {{proc.stderr or proc.stdout}}"
                )
            return (proc.stdout or "").strip()


        def create_issue(
            gh: str,
            *,
            title: str,
            body_path: Path,
            labels: list[str],
            dry_run: bool,
        ) -> tuple[int, str]:
            args = [
                "issue",
                "create",
                "--title",
                title,
                "--body-file",
                str(body_path),
            ]
            for label in labels:
                args.extend(["--label", label])
            url = run_gh(gh, args, dry_run=dry_run)
            if dry_run:
                return 0, url
            m = re.search(r"/issues/(\\d+)\\s*$", url)
            if not m:
                raise SystemExit(f"could not parse issue number from: {{url!r}}")
            return int(m.group(1)), url


        def main() -> int:
            parser = argparse.ArgumentParser(description=__doc__)
            parser.add_argument("--dry-run", action="store_true")
            args = parser.parse_args()

            titles = load_titles()
            gh = resolve_gh()
            labels_epic = ["grafana", "observability", "ux", "epic"]
            labels_child = ["grafana", "observability", "ux"]

            created: list[PublishedIssue] = []

            epic_num, epic_url = create_issue(
                gh,
                title=titles["DUX5-00"],
                body_path=BODIES / "DUX5-00.md",
                labels=labels_epic,
                dry_run=args.dry_run,
            )
            created.append(
                {{
                    "code": "DUX5-00",
                    "number": epic_num,
                    "priority": "meta",
                    "wave": "epic",
                    "url": epic_url,
                    "title": titles["DUX5-00"],
                }}
            )

            for code in CHILD_ORDER:
                pri, wave = META[code]
                body_path = BODIES / f"{{code}}.md"
                if not args.dry_run and epic_num:
                    text = body_path.read_text(encoding="utf-8")
                    if f"#{{epic_num}}" not in text:
                        body_path.write_text(
                            text.replace(
                                "DUX5 epic (`DUX5-00`)",
                                f"DUX5 epic (#{{epic_num}})",
                            ),
                            encoding="utf-8",
                        )
                num, url = create_issue(
                    gh,
                    title=titles[code],
                    body_path=body_path,
                    labels=labels_child,
                    dry_run=args.dry_run,
                )
                created.append(
                    {{
                        "code": code,
                        "number": num,
                        "priority": pri,
                        "wave": wave,
                        "url": url,
                        "title": titles[code],
                    }}
                )
                print(f"created {{code}} -> {{url}}")

            record = {{
                "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "owner": "SatoryKono",
                "repo": "BioactivityDataAcquisition",
                "wave": "dux5-dashboard-typography-reading-order-2026-07-29",
                "issue_pack": str(PACK.relative_to(ROOT)).replace("\\\\", "/"),
                "source_audit": "BIOETL-GRAFANA-UX-SCREENSHOT-AUDIT-2026-07-29-SG01-SG07",
                "predecessors": {{
                    "dux4_epic": 7088,
                    "dux3_epic": 7053,
                    "dsa_epic": 6982,
                    "ds2_epic": 6901,
                }},
                "epic": epic_num,
                "created": created,
                "dry_run": args.dry_run,
            }}
            if not args.dry_run:
                PUBLISH.parent.mkdir(parents=True, exist_ok=True)
                PUBLISH.write_text(
                    json.dumps(record, indent=2, ensure_ascii=False) + "\\n",
                    encoding="utf-8",
                )
                print(f"wrote {{PUBLISH}}")
            else:
                print(json.dumps(record, indent=2, ensure_ascii=False))
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        '''
    )


def main() -> None:
    if not ROADMAP.exists():
        raise SystemExit(f"missing roadmap JSON: {ROADMAP}")
    items = json.loads(ROADMAP.read_text(encoding="utf-8"))
    titles = build_titles(items)
    meta = build_meta(items)

    BODIES.mkdir(parents=True, exist_ok=True)
    (BODIES / "DUX5-00.md").write_text(write_epic_body(), encoding="utf-8")
    for it in items:
        dux = CODE_MAP[it["code"]]
        pri, wave = meta[dux]
        (BODIES / f"{dux}.md").write_text(
            write_child_body(it=it, dux=dux, pri=pri, wave=wave),
            encoding="utf-8",
        )

    title_lines = ["# DUX5 issue titles", ""]
    for code, title in titles.items():
        title_lines.append(f"- `{code}`: `{title}`")
    (BODIES / "TITLES.md").write_text("\n".join(title_lines) + "\n", encoding="utf-8")

    index_lines = [
        "# DUX5 issue bodies index",
        "",
        "| Code | Priority | Wave | File |",
        "| --- | --- | --- | --- |",
        "| DUX5-00 | meta | epic | [DUX5-00.md](./DUX5-00.md) |",
    ]
    for it in items:
        dux = CODE_MAP[it["code"]]
        pri, wave = meta[dux]
        index_lines.append(f"| {dux} | {pri} | {wave} | [{dux}.md](./{dux}.md) |")
    index_lines.append("")
    index_lines.append(
        "Publish: `python .github/ISSUES/_dux5_bodies/publish_dux5_issues.py --dry-run`"
    )
    (BODIES / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    PACK.write_text(
        write_pack(items=items, titles=titles, meta=meta),
        encoding="utf-8",
    )
    (BODIES / "publish_dux5_issues.py").write_text(
        write_publish_script(meta),
        encoding="utf-8",
    )

    print(f"wrote {PACK}")
    print(f"wrote {len(list(BODIES.glob('DUX5-*.md')))} bodies under {BODIES}")
    for code, title in titles.items():
        print(f"  {code}: {title}")


if __name__ == "__main__":
    main()
