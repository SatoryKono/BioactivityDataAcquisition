"""Write observability sequential-run artifacts. One-shot."""

from __future__ import annotations

import json
from pathlib import Path

RUN = Path("reports/audit/observability-seq/20260814T160500Z-obs-seq-8ab59e23")


def main() -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "step": 0,
            "card": "inventory",
            "findings": [],
            "issues": [],
            "created": [],
            "verdict": "ok",
            "sha": "8ab59e2395",
            "formula": "leaf+row",
            "leaf": 198,
            "rows": 28,
            "leaf_plus_row": 226,
            "inventory_check": "PASS",
            "perf": "PASS",
            "matrix": "FAIL 223 vs 226",
        },
        {
            "step": 1,
            "card": "grafana-audit.master",
            "findings": ["F-MATRIX-226", "NAV-ADAPTER", "NAV-CLIP"],
            "issues": [8811, 8803, 8804],
            "created": [],
            "verdict": "deduped-8811-8803-8804",
            "sha": "8ab59e2395",
        },
        {
            "step": 2,
            "card": "grafana-audit.visual",
            "findings": [],
            "issues": [8805],
            "created": [],
            "verdict": "NO_ACTIONABLE_FINDINGS",
            "visual_semantics": "PASS",
        },
        {
            "step": 3,
            "card": "grafana-audit.layout",
            "findings": ["NAV-CLIP", "RE-ROOT-GAP"],
            "issues": [8804],
            "created": [],
            "verdict": "deduped-8804",
        },
        {
            "step": 4,
            "card": "grafana-audit.data-integrity",
            "findings": ["NAV-ADAPTER"],
            "issues": [8803],
            "created": [],
            "verdict": "deduped",
            "live": "SKIP MONITORING=false",
        },
        {
            "step": 5,
            "card": "bi-dashboard-acceptance",
            "findings": ["F-MATRIX-226", "NAV-ADAPTER", "NAV-CLIP"],
            "issues": [8811, 8803, 8804],
            "created": [],
            "verdict": "deduped",
            "depth": "detailed",
        },
        {
            "step": 6,
            "card": "dashboard-panel-audit",
            "findings": ["F-MATRIX-226"],
            "issues": [8811, 8803, 8804, 8805, 8806],
            "created": [],
            "verdict": "native-dedupe",
            "live": "NOT_VERIFIABLE",
            "cycle_count": 1,
        },
        {
            "step": 7,
            "card": "dashboard-audit-cycle",
            "findings": ["F-MATRIX-226"],
            "issues": [8811],
            "created": [],
            "verdict": "native-dedupe-8811",
            "contours": "density,fill,pipeline",
            "pipeline": "FAIL-on-BASE expected 223 got 226",
        },
        {
            "step": 8,
            "card": "grafana-audit.regression",
            "findings": ["F-MATRIX-226"],
            "issues": [8811],
            "created": [],
            "verdict": "candidate=PR8812 != BASE; no empty r2 push",
            "candidate": "https://github.com/SatoryKono/BioactivityDataAcquisition/pull/8812",
        },
        {
            "step": 9,
            "card": "final-sweep",
            "findings": ["F-MATRIX-226"],
            "issues": [8811],
            "created": [],
            "closed": [],
            "blocked": [8811],
            "verdict": "this-run created=0; open this-program=#8811 BLOCKED",
        },
    ]
    (RUN / "ledger.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    findings = {
        "surface_score": 2,
        "surface_score_legend": "0 unacceptable / 1 weak / 2 acceptable / 3 good",
        "findings": [
            {
                "id": "F-MATRIX-226",
                "priority": "P1",
                "severity": "High",
                "confidence": "high",
                "confidence_score": 0.95,
                "status": "PROVEN",
                "category": "inventory-pipeline",
                "path": "scripts/engineering/qa/report_dashboard_panel_audit_matrix.py",
                "observation": (
                    "On origin/main 8ab59e2395, panel-audit-matrix --check "
                    "expected 223 got 226 (leaf+row)."
                ),
                "method": (
                    "worktree origin/main; python -m scripts.engineering.qa "
                    "report-dashboard-panel-audit-matrix --check"
                ),
                "expected": "EXPECTED_PANEL_COUNT == shipped leaf+row (226)",
                "actual": "expected 223, got 226, rc=1",
                "impact": "Release inventory gate red while yaml inventory is already 226.",
                "root_cause": "Stale matrix constant after #8774/#8783 leaf+row unification",
                "remediation": (
                    "Already on PR #8812; close #8811 only after merge to origin/main"
                ),
                "effort": "S",
                "automation": "report-dashboard-panel-audit-matrix --check",
                "automated_fix_possible": False,
                "evidence": [
                    {
                        "path": "scripts/engineering/qa/report_dashboard_panel_audit_matrix.py",
                        "command": (
                            "python -m scripts.engineering.qa "
                            "report-dashboard-panel-audit-matrix --check"
                        ),
                        "observation": "panel count mismatch: expected 223, got 226",
                    }
                ],
                "validation": [
                    "python -m scripts.engineering.qa report-dashboard-panel-audit-matrix --check"
                ],
                "issues": [8811],
                "pr": 8812,
            }
        ],
    }
    (RUN / "findings.json").write_text(
        json.dumps(findings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    docs = {
        "00-inventory.md": """# 00 inventory

BASE: origin/main 8ab59e2395
Formula this program: **leaf+row** (one formula). Do not move yaml to leaf.

| UID | yaml panel_count |
| --- | ---: |
| bioetl-control-plane-v1 | 63 |
| bioetl-overview-v2 | 26 |
| bioetl-runtime | 42 |
| bioetl-provider-health-v2 | 31 |
| bioetl-dq-v2 | 36 |
| bioetl-incident-v1 | 13 |
| bioetl-run-explorer-v1 | 15 |
| **sum** | **226** |

Walk of shipped JSON: leaf=198, row=28, leaf+row=226.

- report-dashboard-inventory --check: PASS
- check-dashboard-visual-semantics: PASS
- check-dashboard-performance-budgets: PASS
- report-dashboard-panel-audit-matrix --check: FAIL expected 223 got 226

CONTRADICTION resolved as: yaml and inventory-check already leaf+row 226; matrix constant stale. Tracked #8811 / PR #8812.
Issues created this step: 0
""",
        "01-grafana-audit-master.md": """# 01 grafana-audit.master

Read-only. MONITORING=false. grafana-six not launched.

FACT: matrix gate red on BASE (223 vs 226). Deduped to #8811 (open) + PR #8812 (open).
FACT: nav adapter=unknown still in generator on BASE. Deduped #8803.
FACT: Run Explorer nav h=2. Deduped #8804.

ISSUE GATE: created=0 (already tracked).
CLOSEOUT: #8811 BLOCKED (acceptance not on origin/main).
""",
        "02-grafana-audit-visual.md": """# 02 grafana-audit.visual

check-dashboard-visual-semantics: PASS on BASE.
Lesson 3: gate PASS does not prove absence of all visual defects. JSON DASH-AUTO-002: no table-wide color-background (closed #8782/#8750).
#8805 typography needs render; MONITORING=false -> NOT_VERIFIABLE as new defect this step.

DASH-AUTO: 001 PASS (allValue .*); 002 PASS; 012/013 no new PROVEN hits.
ISSUE GATE: created=0. NO_ACTIONABLE_FINDINGS for new visual P0-P2.
""",
        "03-grafana-audit-layout.md": """# 03 grafana-audit.layout

DASH-AUTO-007/008 PASS (unique ids, no top-level overlap, grid bounds).
DASH-AUTO-009: Run Explorer root y gap 18->56 before row 3098. Same first-screen geometry cluster as #8804 (not a new issue).
First-screen contract flags (18,55) on origin/main JSON.

ISSUE GATE: created=0 (dedupe #8804).
""",
        "04-grafana-audit-data-integrity.md": """# 04 grafana-audit.data-integrity

Live PromQL SKIP (MONITORING=false). Not treated as dashboard defect.
DASH-AUTO-005: first-window Monitor 9401 expr has no dollar-__range (FACT: trusted current-status recording rule).
#8803 remains the data-handoff residual (adapter=unknown).

ISSUE GATE: created=0.
""",
        "05-bi-dashboard-acceptance.md": """# 05 bi-dashboard-acceptance

DEPTH=detailed, MONITORING=false. Live/KPI values NOT_PROVEN.
Structural BI checks reuse inventory+visual+layout facts above.
score_1_5 typical 4 -> surface_score 2.

ISSUE GATE: created=0 (deduped).
""",
        "06-dashboard-panel-audit.md": """# 06 dashboard-panel-audit

CYCLE_COUNT=1. Native create skipped: REQUIRE_GH_TRACKING + already-open #8811/#8803-8806.
198 leaf panels: live query NOT_VERIFIABLE.

ISSUE GATE: native-dedupe, created=0.
""",
        "07-dashboard-audit-cycle.md": """# 07 dashboard-audit-cycle

N=1 CONTOURS=density,fill,pipeline (not render/visual/layout/data).
- density: no new P0-P2 beyond matrix on BASE.
- fill: visual-semantics PASS; DASH-AUTO-002 PASS.
- pipeline: matrix FAIL 223 vs 226 = #8811.

ISSUE GATE: native-dedupe #8811, created=0.
""",
        "08-grafana-audit-regression.md": """# 08 grafana-audit.regression

Candidate != BASE: PR #8812 (fix/observability-seq-8ab59e23) pins EXPECTED_PANEL_COUNT=226.
8781/8783 already on BASE.
r2 without unique new commits: no push this run.
""",
        "09-final-sweep.md": """# 09 final sweep

This-run created issues: none.
This-program open: #8811 BLOCKED until origin/main or operator accepts PR-head.
Pre-existing open (not created here): #8803 #8804 #8805 #8806.
Closed not reopened: #8774 #8779 #8780 #8782 #8741 #8750 #8738.
grafana-six: not launched.
""",
        "report.md": """# Sequential observability run report

run_id: `20260814T160500Z-obs-seq-8ab59e23`
MONITORING: false
WORK_BRANCH: `fix/observability-seq-8ab59e23` (existing; local dirty WIP not used as BASE)
BASE: `origin/main` `8ab59e2395`
grafana-six: SKIP (deprecated; not launched)

## Executed

| Step | Card | outcome | issues created | close |
| ---: | --- | --- | ---: | --- |
| 0 | inventory | 7 UID / 198 leaf / 226 leaf+row; inventory+visual+perf PASS; matrix FAIL | 0 | n/a |
| 1 | grafana-audit.master | residuals tracked | 0 | #8811 BLOCKED |
| 2 | grafana-audit.visual | JSON-only; semantics PASS | 0 | n/a |
| 3 | grafana-audit.layout | geometry OK; RE gap deduped #8804 | 0 | n/a |
| 4 | grafana-audit.data-integrity | live SKIP; #8803 deduped | 0 | n/a |
| 5 | bi-dashboard-acceptance | DEPTH=detailed; live na | 0 | n/a |
| 6 | dashboard-panel-audit | native dedupe | 0 | n/a |
| 7 | dashboard-audit-cycle N=1 density/fill/pipeline | pipeline=#8811 | 0 | BLOCKED |
| 8 | regression | candidate PR #8812 != BASE; no empty r2 push | 0 | n/a |
| 9 | sweep | this-run open = #8811 BLOCKED | 0 | 0 |

## Deduped (not recreated)

- #8774 / #8779 / #8780 / #8782 / #8741 / #8750 / #8738 — closed on origin/main; not reopened
- #8803 adapter=unknown — open pre-existing
- #8804 Run Explorer nav h=2 / first-screen geometry — open pre-existing
- #8805 typography — open; render NOT_VERIFIABLE (MONITORING=false)
- #8806 keyboard focus — open; not shipped JSON
- #8811 matrix 223 vs 226 — open; PR #8812

## Created this run

None.

## Closeout

#8811 stays BLOCKED: acceptance not on origin/main.
PR: https://github.com/SatoryKono/BioactivityDataAcquisition/pull/8812

ALLOW_MERGE=false. ALLOW_PUSH: no unique commit this run (do not push dirty density/prompt WIP as r2).

## DASH-AUTO vs SSOT (steps 2/3/4/7)

| ID | Result | Note |
| --- | --- | --- |
| 001 | PASS | includeAll allValue `.*` |
| 002 | PASS | no table-wide color-background |
| 003-004 | PASS | data-bearing titles/descriptions |
| 005 | PASS | first-window Monitor 9401 has no range var |
| 006 | GAP | proposal only |
| 007-008 | PASS | unique ids; no top-level overlap |
| 009 | PASS | RE y=18->56 clustered with #8804 |
| 010-014 | PASS | |
| 015 | GAP | 800-char cap not SSOT |
| 016 | GAP | not re-counted this run |
| 017 | PASS | one formula leaf+row; yaml=check=226; matrix stale |
| 018 | GAP | tooltip mode not SSOT |

## Surface score

**2** (acceptable): core structure/gates green; one pipeline constant drift already ticketed; live data not verified.

No commit to main. No `.env` edits.
""",
    }
    for name, text in docs.items():
        (RUN / name).write_text(text, encoding="utf-8")
    print("wrote", RUN)
    print([path.name for path in sorted(RUN.iterdir())])


if __name__ == "__main__":
    main()
