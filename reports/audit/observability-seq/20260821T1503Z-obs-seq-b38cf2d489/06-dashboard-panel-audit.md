# Step 6 — dashboard-panel-audit

CYCLE_COUNT=1. REQUIRE_GH_TRACKING=true (native 3–5). MONITORING=true.

## Phase 1 inventory

Seven UIDs — see `00-inventory.md`. §8 gates: inventory PASS; visual-semantics FAIL on BASE; perf PASS; density PASS.

## Phase 2 sample statuses

| uid | panel | type | ds | band | status | DASH-* |
| --- | --- | --- | --- | --- | --- | --- |
| provider-health | 9104 | stat | prometheus | first_window | Defect on BASE / OK on candidate | DASH-STATE-002 |
| dq-v2 | 9103 | text | grafana | first_window | Defect on BASE / OK on candidate | DASH-TYPOGRAPHY-001 |
| all | 1000 | text | grafana | first_window | Defect Dark 200% (prior live) | DASH-FIT-004 #9340 |
| run-explorer | 3010 | table | BioETL Ops HTTP | first_window | OK live `index_state=ok` | — |

## Phases 3–5

Issues: **#9342**, **#9343** (created); **#9340** reused. Fixes on WORK_BRANCH for 9342/9343. Closeout BLOCKED until origin/main (`ALLOW_MERGE=false`).
