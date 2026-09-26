# BioETL Run Explorer - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-run-explorer-v1.json`
**UID:** `bioetl-run-explorer-v1`

## Scope and layout

The page contains a two-line scope banner (y=0/h=2) and Inspect Recent Runs
(last 10), y=2/h=14. Workflow=All, Pipeline=All, Run Type=All and Run ID=-
are the defaults. The newest ten launches are shown together without pagination,
independently of the dashboard time range. Filters and exact Run ID lookup apply
before the global ten-row limit. No dashboard navigation band is shown here.

## Columns and links

| Column | Value | Destination |
| --- | --- | --- |
| Workflow | Workflow name; — when absent | Workflow passport |
| Pipeline | Pipeline name | Pipeline passport |
| Provider | Recorded provider; N/A when absent | Provider Health |
| Run ID | Short UUID; full UUID in report link title | Exact persisted Report |
| Started | YY-MM-DD:HH:mm; N/A when absent | None; descending sort |
| Duration | Compact elapsed duration, e.g. 2m 32s; N/A when unavailable | None |
| Overview | Execution status | Run Overview |
| Saved Evidence | Verified saved-evidence status | Selected-run Pipeline Diagnostics |
| Data Quality | Saved exact-run quality verdict | Data Quality |
| Replay Readiness | Exact replay assessment | Replay Readiness |

Dashboard UIDs and existing URL slugs remain stable. Display names are
Replay Readiness, Run Overview and Data Quality. Row links use the full Run ID,
pipeline, workflow and run type from that row. Provider Health additionally
receives the recorded provider. Passport links target generated documentation.
Missing reports have no report URL; they must not open another run's report.

## Evidence semantics

The recent-list API verifies assessments only for the bounded result page.
Processing success never implies quality, evidence or replay OK. Nonterminal
ledger entries remain unfinished; their age is not evidence of current liveness.

- OK: the relevant checks passed.
- WARN: recorded noncritical findings.
- ERROR: a failed assessment or corrupt/mismatched evidence.
- INCOMPLETE: required evidence, checks or verification is missing.
- N/A: explicitly unsupported assessment or legacy report without that evaluation.
- IN PROGRESS: reserved for a confirmed assessment queue/running signal. The
  current API does not infer this state from a missing report or running pipeline.
- QUERY ERROR: source/read failure, distinct from a run's assessment failure.

Saved Evidence checks artifact presence and integrity. Legacy reports without a
snapshot show N/A; missing modern evidence shows INCOMPLETE. Replay maps READY to
OK, BLOCKED to ERROR, INSUFFICIENT to INCOMPLETE and UNSUPPORTED to N/A.
Missing quality evidence on a modern report is INCOMPLETE; it never becomes OK.

Status text colors: OK/success #73BF69; warn/partial/shutdown #F2CC0C;
ERROR/failed/query error #F2495C; incomplete/unfinished #FF9830;
in progress/running #5794F2; N/A/unknown #9CA3AF; dry_run #B877D9.
Cells keep the normal row background. Only OK, N/A and ERROR remain uppercase
in the table; API assessment values retain their original spelling.
Replay Readiness has a 125px column. The installed native table has no per-column
font-size option, so Started and Replay Readiness retain the native font size.
Ordinary links use #93C5FD and ordinary values #E5E7EB.

## Generation and verification

`python -m scripts.ops.observability.grafana._run_explorer_columns` applies only
this presentation contract; `--check` detects drift. The full navigation generator
also invokes this contract last, after older layout migrations.

Run the recent-run API tests, presentation tests, dashboard operator-readability,
first-window no-scroll and selection-action tests. Verify ten populated rows,
status links and passport/report targets in the browser. A source-bound API with
matching row fields is required; an old runtime image is not acceptance.
