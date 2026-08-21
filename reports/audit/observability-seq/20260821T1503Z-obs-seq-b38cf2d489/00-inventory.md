# Step 0 — Shared inventory

**UTC:** 2026-08-21T15:03Z  
**BASE:** `origin/main` `b38cf2d4897d9eabf05db982faa8bcbb1c40d494`  
**WORK_BRANCH:** `fix/observability-seq-b38cf2d489` (worktree; `main` dirty — чужой WIP не трогали)  
**Grafana live:** 12.0.0 (`GET http://127.0.0.1:3000/api/health`)  
**JSON model:** Classic dashboard JSON, `schemaVersion` 30  
**Formula (этот прогон):** `panel_count` = leaf **+** row = `report-dashboard-inventory --check` = YAML `dashboard-inventory.yaml`

| uid | title | leaf | row | leaf+row | YAML | match |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| bioetl-control-plane-v1 | 0. Trust | 58 | 7 | 65 | 65 | yes |
| bioetl-overview-v2 | 1. Overview | 23 | 5 | 28 | 28 | yes |
| bioetl-runtime | 2. Pipeline Diagnostics | 37 | 6 | 43 | 43 | yes |
| bioetl-provider-health-v2 | 3. Provider Health | 32 | 5 | 37 | 37 | yes |
| bioetl-dq-v2 | 4. Data Quality | 33 | 4 | 37 | 37 | yes |
| bioetl-incident-v1 | 5. Incident Workspace | 12 | 3 | 15 | 15 | yes |
| bioetl-run-explorer-v1 | 6. Run Explorer | 11 | 2 | 13 | 13 | yes |

**FACT:** CONTRADICTION leaf vs leaf+row **не воспроизводится** на этом SHA. DASH-AUTO-017 PASS.

**Gates**

| Command | BASE `origin/main` | Candidate (this branch) |
| --- | --- | --- |
| `report-dashboard-inventory --check` | PASS | PASS |
| `check-dashboard-visual-semantics` | FAIL (9104 orange) | PASS |
| `check-dashboard-performance-budgets` | PASS | PASS |
| `report-dashboard-scalar-density --check` | PASS | PASS |

Issues: **none** (step 0).
