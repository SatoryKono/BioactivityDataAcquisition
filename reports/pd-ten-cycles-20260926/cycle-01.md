# Pipeline Diagnostics — cycle 01

Date: 2026-09-26. Baseline: 5f2fb6d10779. Selected run:
ed16a540-12f6-5c7d-a752-45fbf32a1972, uniprot_protein, incremental.
Browser: 1151 x 920, Europe/Kiev, all saved-evidence panels expanded.

## Panel audit

| Panel | Population and design finding |
| --- | --- |
| 1000 navigation | Seven destinations render; current dashboard has a distinct label. |
| 9400 scope | Correct saved-run scope; long single-line explanation at narrow widths. |
| 9998 status | SUCCESS / OK / COMPLETE populated; terms require explanation. |
| 9402 identity | Exact UUID and manifest present; pagination hides contract/execution fields. |
| 9403 records | Bronze 1500, Silver 1478; generic backend-health cell links interrupt investigation. |
| 9450 disclosure | Four child panels; description does not mention total duration. |
| 9463 duration | Total duration exists; must remain distinct from absent stage timings. |
| 9460 stages | Four saved stages; Not recorded timing and report links; raw field names already covered by issue 11573. |
| 9451 domains | Six domains; reason cells expose execution_success, standalone_pipeline and other implementation codes. |
| 9452 saved identity | Completed time readable; revision hash wraps across four lines. |

## Ranked proposals

1. P1: Translate known domain reason codes into precise English explanations; preserve unknown codes. Selected.
2. P1: Make record cell links open the exact saved run report instead of backend health. Selected.
3. P1: Replace the obsolete runtime panel guide, which describes CURRENT Prometheus panels absent from this dashboard. Selected.
4. P2: Name and order stage fields; reuse existing issue 11573, avoid duplicate work.
5. P2: Keep long revision identifiers inspectable without forcing four-line rows.
6. P2: Explain Result, Status and Evidence in the status panel description; coordinate existing issue 11576.
7. P2: Explain what stage counters exclude and preserve missing versus zero; coordinate issue 11574.
8. P2: Update disclosure text to mention total duration before stages.
9. P2: Improve record-row visibility without exceeding the first-window budget.

## Acceptance

Verify selected-run values in the live browser, generated JSON idempotence,
operator-readability and first-window tests, targeted regression tests and Ruff.
No raw report data, verdict calculation or evidence state is changed.
Issue closure and main merge require their actual GitHub lifecycle evidence.

## Implementation and validation

- Issues: 11681 (reason labels), 11682 (report links), 11683 (panel guide).
- Implemented scoped corrections in the canonical renderer helper and generated JSON.
- Targeted tests: 22 passed; Ruff: passed; diff whitespace: passed.
- Live 1151 x 920: all six domains retained; five known reasons render in English;
  Workflow remains N/A. Verdicts and report queries unchanged.
- Report artifact endpoint returned the selected uniprot_protein report with the
  exact UUID in its artifact path; raw counters and reasons are retained.
- Docs links/specs/configs: 5 pre-existing broken archive references outside this
  guide (00-map.md, ADR-051, ADR-052). No local Markdown links/metadata were changed
  by the guide rewrite, so cleanup inventory regeneration is not applicable.
- GitHub main Tests run 36253295783: jobs never started; account billing lock.
  CI=BLOCKED_EXTERNAL, not a test assertion failure or a local PASS.
- Runtime mirrors and src/bioetl were not changed. Debt budgets unchanged.
- Proof-or-Stop plan invocation resolved the shared main checkout rather than this
  worktree; that plan is not accepted as source-bound evidence for this PR.
- Cycle 01 is not closed until main/CI acceptance is established. Cycles 02–10
  have not been represented as completed or replaced with artificial repeat checks.
