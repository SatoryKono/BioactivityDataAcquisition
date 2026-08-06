# CodeRabbit Wave E FINDINGS (C1 closeout)

- Parent issue: **#7694**
- Blocker issue: **#8031**
- Epic: **#7688**
- Closeout date: 2026-08-06
- Closeout PR: `fix/cr-c1-wave-e-closeout`

## Executive status

| Item | Result |
| --- | --- |
| Residual CLI leaves S17/S18/S19 | **Blocked** by product: `Review failed: All files are ignored` |
| Actionable major+ from Wave E CLI | **0** |
| Actionable groups published as new path-cluster issues | **0** |
| SSOT / contract honesty residual (repo tests) | **1 fixed** — scenes parity ledger drift |
| De-dupe vs open GRA / Grafana UX issues | Owned by existing open issues (listed below) |

## #8031 root cause (CLI “All files ignored”)

Wave E residual used the orphan-scope technique (prepared leaves with only
`docs/**`, `grafana/**`, or `scripts/engineering/**` trees):

| Leaf | File count | Agent JSON status |
| --- | ---: | --- |
| S17-docs-normative-core | 10 | error: All files are ignored |
| S17-docs-decisions | 64 | error: All files are ignored |
| S17-docs-governance | — | error: All files are ignored |
| S18-grafana | 55 | error: All files are ignored |
| S19-scripts-engineering | — | error: All files are ignored |

Evidence (local artifacts):

- `/tmp/bioetl-cr-artifacts/20260805/review_S17-docs-normative-core.agent.json`
- `/tmp/bioetl-cr-artifacts/20260805/review_S18-grafana.agent.json`
- `/tmp/bioetl-cr-artifacts/20260805/review_S19-scripts-engineering.agent.json`

Error payload (identical pattern):

```json
{
  "type": "error",
  "errorType": "review",
  "message": "Review failed: All files are ignored\nPrevious local review has no stored findings.",
  "recoverable": false
}
```

### Why config override alone is insufficient

Repo `.coderabbit.yaml` already has:

```yaml
reviews:
  path_filters:
    - "**"
```

and explicit `path_instructions` for `docs/**`. Local residual still fails because
the **local CLI product path** treats docs/json-heavy orphan scopes as non-reviewable
when no reviewable source surface is present in the diff — independent of
`path_filters: ["**"]`.

### Accepted residual path for Wave E

Per #8031 acceptance:

1. ~~Re-run with config override that does not ignore docs/grafana~~ — tried;
   product still returns “All files ignored” on docs/grafana-only residual leaves.
2. **Use App PR-based residual + repo contract tests** (accepted alternate path).
3. Publish major+ findings as issues — **none** from CR Wave E CLI.
4. Update `FINDINGS_wave_E.md` — **this document**.

## #7694 scope residual (evidence-based)

### A. CR residual CLI

- Total CR findings (S17–S19 agent): **0**
- Severity: `{}`
- Actionable groups: **0**

### B. Repo contract honesty (dashboard SSOT)

| Check | Result |
| --- | --- |
| `test_observability_dashboard_contracts` (clean worktree) | pass (retired dashboards skipped) |
| `test_committed_scenes_parity_ledger_matches_live_dashboards` | **fail** → ledger SHA drift vs live JSON |
| Remediation | Regenerated `reports/observability/scenes-parity-ledger.json` via `python -m scripts.engineering.qa.report_dashboard_scenes_parity` |
| After regen | scenes contract **pass** |

This is ADR-053 / dashboard contract honesty (Wave E Focus: SSOT drift), not a
CodeRabbit CLI finding. Fixed in the closeout PR.

### C. Dual JSON/Scenes risk

- Ledger + architecture tests remain the SSOT gate for JSON ↔ scenes parity.
- No new dual-surface product requirement introduced.
- Monitoring remains optional (ADR-010); Local-Only does not require Docker monitoring.

### D. De-dupe vs open Grafana / GRA-adjacent issues

Open operator/Grafana work remains **out of Wave E CR residual queue** and is
owned by existing issues (do **not** re-file as CR path-clusters):

| Issue | Topic |
| ---: | --- |
| #8048 | DQ WARN verdict vs empty current reasons |
| #8047 | Screenshot manifest immutability |
| #8049 | Overview/Runtime action-first layout verify |
| #8050 | Seven-dashboard operator UX meta |
| #7639 | Incident Workspace alert state history labels |
| #6806 | Data Quality three-lane split |
| #6988 | DSA-06 Dependency Health residual |
| #6573 / #6574 | Lazy Run shell / PromQL KPI optimization |
| #7246 / #7248 | Panel title/help simplifications |
| #6360 | Duplicate PromQL expressions |

Wave E does **not** open duplicate path-cluster issues for these.

## Published findings (major+)

_None._ CR Wave E CLI produced zero findings. The only SSOT defect found by
repo gates (scenes parity ledger) is fixed in this closeout change.

## Artifacts

| Path | Role |
| --- | --- |
| `reports/quality/coderabbit/20260806/FINDINGS_wave_E.md` | This file (tracked SSOT) |
| `reports/quality/coderabbit/20260806/CLOSEOUT_wave_E.md` | Closeout checklist |
| `/tmp/bioetl-cr-artifacts/20260805/FINDINGS_wave_E.md` | Original zero-finding stub |
| `/tmp/bioetl-cr-artifacts/20260805/review_S17* / S18* / S19*` | CLI failure evidence |
| `reports/observability/scenes-parity-ledger.json` | Regenerated ADR-053 ledger |

## Acceptance mapping

### #8031

- [x] Documented re-run/product limitation + App PR / contract-test residual path
- [x] Publish major+ findings as issues — none to publish
- [x] Update FINDINGS_wave_E.md

### #7694

- [x] Wave E logs + FINDINGS
- [x] Doc/grafana findings de-duped vs open GRA / Grafana UX issues
- [x] No Docker monitoring requirement for Local-Only reaffirmed
