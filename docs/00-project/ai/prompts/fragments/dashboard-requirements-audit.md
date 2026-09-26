---
id: prompt.fragment.dashboard-requirements-audit
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Per-dashboard palette, copy, data, answer panels, and shipped panel roster for dashboard audits
---

## Dashboard requirements audit contract

Normative question and answer ids: `docs/01-requirements/DASHBOARD_REQUIREMENTS.md` §7 and §7.1.
Machine lock: `docs/03-guides/dashboards/contracts/requirement-coverage.yaml` and `layout-budgets.yaml` (`answer_panels`, `first_window_y=18`, `first_load_y_max=28`).
Palette and copy: `docs/03-guides/dashboards/verdict-ontology.md`, `design-system.md` §1–§3, §9.1.
Do not invent panels or `DASH-*` ids. If this roster and the audited JSON disagree, the JSON wins and the diff is recorded. A missing required answer id is `DASH-FIT-003`, not a roster update.

Roster snapshot: `origin/main` `1de34832856da16781f939cf10187cd99168354c` on 2026-09-26. Re-walk `grafana/dashboards/*.json` every cycle.

Older design-system sentences that still name Loki, Tempo, or an L0 "what is broken now" Overview question are not the shipping question when they disagree with §7.

### Shared palette

| State | Color | Rule |
| --- | --- | --- |
| OK | green | only with required evidence |
| WARN | orange | |
| CRIT | red | |
| UNKNOWN / INCOMPLETE | gray | null/absent is UNKNOWN, never green |
| ERROR | distinct | query/datasource failure, not a healthy zero |

Precedence: `ERROR > INCOMPLETE/UNKNOWN > CRIT > WARN > OK`.
First-window background `stat` `noValue` is a fail-closed `UNKNOWN…` string (`DASH-STATE-003`).
`CURRENT`, `SELECTED RUN`, and `TIME RANGE` are scope labels, not peer severity badges.
`VALID_EMPTY` / zero events are not OK and not UNKNOWN.
Area fill only for `gridPos.y < 18` and only with a textual state. Below the fold: `colorMode=value`, table `color-text` or neutral `auto`, `fillOpacity=0`, no authored background (`DASH-COLOR-001`).

### Shared text

| Surface | Floor |
| --- | --- |
| Authored body | `12pt` / `16px` |
| Authored heading | `14pt` / `18.6667px` |
| Grafana-managed title | pinned theme token, at least `14px` |

Clock text is `YYYY-MM-DD HH:MM`. Grafana unit is `time:YYYY-MM-DD HH:mm` (`MM` is months and is forbidden) (`DASH-TIME-001`).
Content titles start with `Monitor`, `Inspect`, `Track`, `Compare`, `Review`, or `Investigate` (`DASH-COPY-003`). Text, row, and shell titles may use `Navigate`, `Understand`, `Start`, `Assess`, `Explain`, `Continue`.
First-window `Monitor*` panels must not use `$__range` (`DASH-COPY-004`).
Verdict cards state `OK` / `WARN` / `CRIT` / `UNKNOWN` in the description. Trust gates `1. Trust` and runtime `9401` also state `INCOMPLETE` (`DASH-COPY-006`).
HTML copy roles (`DASH-COPY-008`): `<b>` numbered dashboard name, `<em>` panel title, CAPS status/scope without bold, `<code style="font-size:16px">` field token, regular `16px` body. Navigation chips are exempt.

### Shared data and layout

- Datasources: Prometheus, built-in Grafana, `BioETL Ops HTTP` only (`DASH-DATA-004`). No `loki`, `tempo`, or `:8081` (`DASH-DATA-003`).
- Prometheus labels must not carry `run_id`, hashes, or paths (`DASH-DATA-002`). Exact-run identity is Ops HTTP.
- `scope=selected_run` requires `evidence_source=ops_http` (`DASH-SCOPE-001`).
- Additional groups: `D_area >= 0.60` and `D_count >= 0.50` (`DASH-DENSITY-001`). Scalar `rho(group) > rho(first screen)` (`DASH-DENSITY-002`).
- `FIRST_WINDOW_Y=18` is the visual fold. `FIRST_LOAD_Y_MAX=28` is the PromQL/HTTP budget window. Do not merge them (`DASH-PERF-003`).
- Always-visible root non-row `max(y+h) <= 18` (`DASH-FIT-001`). No panel may straddle `y < 18 < y+h` (`DASH-FIT-002`).
- Navigation bus `0..6`, omit self-link, keep time, pass only allowlisted variables (`DASH-NAV-001`).
- Do not raise `performance-budgets.yaml` or tech-debt budgets.

### Static gates (§8)

| Check | Command or test |
| --- | --- |
| Presentation / density / fill | `tests/integration/test_dashboard_presentation_requirements.py` |
| Structural safety | `tests/integration/test_dashboard_structural_invariants.py` |
| Geometry, FIT, copy | `tests/integration/test_dashboard_geometry_and_purpose_contracts.py` |
| First-window containment | `tests/integration/test_dashboard_first_window_containment.py` |
| Operator readability | `tests/integration/test_dashboard_operator_readability.py` |
| No-scroll | `tests/integration/test_dashboard_first_window_noscroll.py` |
| Requirement coverage | `tests/integration/test_dashboard_requirement_coverage.py` |
| Requirement gates | `tests/integration/test_dashboard_requirement_gates.py` |
| Visual semantics | `python -m scripts.engineering.qa check-dashboard-visual-semantics` |
| Inventory | `python -m scripts.engineering.qa report-dashboard-inventory --check --json` |
| PromQL scope | `python -m scripts.engineering.qa report-dashboard-promql-scope --check` |
| Query duplicates | `python -m scripts.engineering.qa report-dashboard-query-duplicates --check --json` |
| Scalar density | `python -m scripts.engineering.qa report-dashboard-scalar-density --check` |
| Performance | `python -m scripts.engineering.qa check-dashboard-performance-budgets` |

`role=chrome` below means the snapshot target had neither a PromQL `expr` nor an HTTP `url`. Re-check before calling a required answer panel non-data (`DASH-COPY-007`).

### 0. Run Explorer `bioetl-run-explorer-v1`
- Question: Which pipelines ran most recently, and where are their reports?
- Answer panel: 3010 Inspect Recent Runs
- Next action token: Click a Run cell
- Basis tokens: SELECTED RUN; VALID EMPTY
- Data: HTTP index. No Prometheus run_id label. Empty index is VALID EMPTY, not a healthy fleet.
- Snapshot panels: 6. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | Navigate Dashboards |  | chrome |
| 1 | 2 | first-window | text | Understand Run Scope |  | chrome |
| 3010 | 5 | first-window | table | Inspect Recent Runs (last 10) | BioETL Ops HTTP | data |
| 9450 | 17 | first-window | row | Inspect Saved Run Evidence |  | chrome |
| 9451 | 18 | first-load | table | Inspect Selected Run Domains | BioETL Ops HTTP | data |
| 9452 | 30 | below | table | Inspect Selected Run Identity | BioETL Ops HTTP | data |

### 1. Trust `bioetl-control-plane-v1`
- Question: Can the selected run be exactly replayed from saved inputs?
- Answer panel: 9422 Review Exact Replay Readiness
- Next action token: Inspect Replay Safety State
- Basis tokens: CURRENT; processing_status; trust_status
- Data: Exact-run HTTP. CURRENT 9401 is not this answer. INCOMPLETE when checkpoint/scrape evidence is missing. processing_status is not trust_status.
- Snapshot panels: 30. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | Navigate Dashboards |  | chrome |
| 9400 | 2 | first-window | text | Inspect Scope & Evidence |  | chrome |
| 9422 | 2 | first-window | table | Review Exact Replay Readiness | BioETL Ops HTTP | data |
| 9416 | 5 | first-window | table | Review Retention Compliance | BioETL Ops HTTP | data |
| 9418 | 5 | first-window | table | Review Selected-Run Trust | BioETL Ops HTTP | data |
| 9419 | 17 | first-window | row | Review Lineage Validation |  | chrome |
| 902 | 18 | first-load | row | Inspect Replay & Checkpoint Evidence |  | chrome |
| 9415 | 18 | first-load | table | Review Lineage Validation | BioETL Ops HTTP | data |
| 901 | 19 | first-load | row | Inspect Manifest & Ledger Evidence |  | chrome |
| 9413 | 19 | first-load | table | Review Checkpoint Validation | BioETL Ops HTTP | data |
| 9414 | 20 | first-load | table | Review Manifest Validation | BioETL Ops HTTP | data |
| 905 | 22 | first-load | row | Inspect Run Identity Evidence |  | chrome |
| 9404 | 23 | first-load | table | Review Identity Anchors | BioETL Ops HTTP | data |
| 9412 | 23 | first-load | row | Inspect Run Details |  | chrome |
| 9402 | 24 | first-load | table | Review Run Summary | BioETL Ops HTTP | data |
| 9420 | 24 | first-load | row | Inspect Complete Run Discovery |  | chrome |
| 9421 | 25 | first-load | table | Inspect Latest Complete Run | BioETL Ops HTTP | data |
| 9450 | 25 | first-load | row | Inspect Saved Run Evidence |  | chrome |
| 9451 | 26 | first-load | table | Inspect Selected Run Domains | BioETL Ops HTTP | data |
| 9407 | 35 | below | table | Inspect Identity Values | BioETL Ops HTTP | data |
| 9403 | 36 | below | table | Review Processed Records | BioETL Ops HTTP | data |
| 9452 | 38 | below | table | Inspect Selected Run Identity | BioETL Ops HTTP | data |
| 9410 | 43 | below | text | Explain Missing Identity Data |  | chrome |
| 9411 | 43 | below | text | Explain Missing Record Counts |  | chrome |
| 9405 | 48 | below | table | Review Identity Gaps | BioETL Ops HTTP | data |
| 9417 | 48 | below | table | Review Bounded Failure Reasons | BioETL Ops HTTP | data |
| 9408 | 55 | below | table | Review Required Replay Anchors | BioETL Ops HTTP | data |
| 9406 | 67 | below | table | Compare Checkpoint Anchors | BioETL Ops HTTP | data |
| 9409 | 79 | below | table | Review Additional Forensic Anchors | BioETL Ops HTTP | data |
| 139 | 91 | below | text | Review Uncovered Replay Signals |  | chrome |

### 2. Overview `bioetl-overview-v2`
- Question: What is the saved assessment of the selected Run ID?
- Answer panel: 9603 Review Selected Run Status + 9002 Review Run Domains
- Next action token: Open Run Explorer
- Basis tokens: SELECTED RUN; QUERY ERROR
- Data: Saved HTTP evidence. CURRENT fleet chips must not replace 9603/9002. QUERY ERROR is not OK.
- Snapshot panels: 10. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | Navigate Dashboards |  | chrome |
| 99 | 2 | first-window | text | Inspect Scope & Evidence |  | chrome |
| 9002 | 5 | first-window | table | Review Run Domains | BioETL Ops HTTP | data |
| 9603 | 5 | first-window | table | Review Selected Run Status | datasource | chrome |
| 9602 | 11 | first-window | row | Inspect Run Context |  | chrome |
| 9300 | 12 | first-window | table | Review Run Identity | BioETL Ops HTTP | data |
| 9301 | 12 | first-window | table | Review Processed Records | BioETL Ops HTTP | data |
| 9450 | 12 | first-window | row | Inspect Saved Run Evidence |  | chrome |
| 9451 | 13 | first-window | table | Inspect Selected Run Domains | BioETL Ops HTTP | data |
| 9452 | 25 | first-load | table | Inspect Selected Run Identity | BioETL Ops HTTP | data |

### 3. Pipeline Diagnostics `bioetl-runtime`
- Question: What currently blocks runtime delivery?
- Answer panel: 9401 Monitor Pipeline Status
- Next action token: Open Runtime Blockers
- Basis tokens: CURRENT; UNKNOWN
- Data: Trust-gated current verdict. Missing 9401 in a snapshot is a DASH-FIT-003 gap, not a waiver. INCOMPLETE on telemetry gap.
- Snapshot panels: 10. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | Navigate Dashboards |  | chrome |
| 9400 | 2 | first-window | text | Understand Pipeline Scope |  | chrome |
| 9993 | 5 | first-window | row | Inspect Run Context |  | chrome |
| 9998 | 6 | first-window | table | Review Selected Run Status | BioETL Ops HTTP | data |
| 9402 | 10 | first-window | table | Inspect Pipeline Identity | BioETL Ops HTTP | data |
| 9403 | 10 | first-window | table | Inspect Processed Records | BioETL Ops HTTP | data |
| 9450 | 16 | first-window | row | Inspect Saved Run Evidence |  | chrome |
| 9451 | 17 | first-window | table | Inspect Selected Run Domains | BioETL Ops HTTP | data |
| 9452 | 25 | first-load | table | Inspect Selected Run Identity | BioETL Ops HTTP | data |
| 9460 | 33 | below | table | Inspect Selected Run Stages | BioETL Ops HTTP | data |

### 4. Provider Health `bioetl-provider-health-v2`
- Question: Which provider is degraded/failing, and why?
- Answer panel: 9101 (requirements title Monitor Fleet Severity; confirm shipped title)
- Next action token: Open selected provider context
- Basis tokens: CURRENT; GLOBAL
- Data: GLOBAL matrix vs SELECTED PROVIDER are not peer badges. Fleet CRIT with selected OK is allowed when copy says fleet vs selected.
- Snapshot panels: 40. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | Navigate Dashboards |  | chrome |
| 9400 | 2 | first-window | text | Understand Evidence Scope |  | chrome |
| 9401 | 2 | first-window | stat | Monitor Selected Provider | prometheus | data |
| 9002 | 5 | first-window | text | Start Provider Triage |  | chrome |
| 9101 | 7 | first-window | table | Monitor Fleet Status | prometheus | data |
| 9107 | 7 | first-window | table | Inspect Health Evidence | prometheus | data |
| 9104 | 15 | first-window | stat | Monitor Telemetry Presence | prometheus | data |
| 9106 | 18 | first-load | row | Inspect Fleet Non-OK and Causes |  | chrome |
| 9102 | 19 | first-load | table | Inspect Non-OK Providers | prometheus | data |
| 9105 | 19 | first-load | row | Inspect Full Fleet Evidence |  | chrome |
| 91 | 20 | first-load | row | Selected Provider Details |  | chrome |
| 9111 | 20 | first-load | table | Inspect Full Fleet Severity | prometheus | data |
| 106 | 21 | first-load | timeseries | Track Health Failures & Degradation | prometheus | data |
| 9404 | 21 | first-load | row | Range & Debug Evidence |  | chrome |
| 114 | 22 | first-load | table | Inspect Raw Health Status | prometheus | data |
| 9405 | 22 | first-load | row | Run Context |  | chrome |
| 9402 | 23 | first-load | table | Inspect Run Identity | BioETL Ops HTTP | data |
| 9450 | 23 | first-load | row | Inspect Saved Run Evidence |  | chrome |
| 9451 | 24 | first-load | table | Inspect Selected Run Domains | BioETL Ops HTTP | data |
| 9112 | 25 | first-load | table | Inspect Full Non-OK Providers | prometheus | data |
| 107 | 26 | first-load | table | Track Failure Share | prometheus | data |
| 9103 | 27 | first-load | table | Inspect Top Provider Causes | prometheus | data |
| 108 | 30 | below | table | Inspect Exhausted Retries | prometheus | data |
| 9113 | 30 | below | table | Inspect Full Provider Causes | prometheus | data |
| 1 | 32 | below | timeseries | Track Health-Check Latency p95 | prometheus | data |
| 109 | 34 | below | timeseries | Track Exhausted Retries | prometheus | data |
| 9403 | 35 | below | table | Inspect Processed Records | BioETL Ops HTTP | data |
| 9452 | 36 | below | table | Inspect Selected Run Identity | BioETL Ops HTTP | data |
| 102 | 39 | below | stat | Inspect Health p95 | prometheus | data |
| 2 | 42 | below | stat | Monitor Healthy Checks | prometheus | data |
| 105 | 45 | below | stat | Monitor Degraded Checks | prometheus | data |
| 104 | 48 | below | stat | Track Failure Rate | prometheus | data |
| 110 | 49 | below | timeseries | Track Request Latency p95 | prometheus | data |
| 7 | 51 | below | stat | Monitor Health Checks | prometheus | data |
| 111 | 59 | below | timeseries | Track Rate-Limit Errors | prometheus | data |
| 115 | 64 | below | timeseries | Track Network & Timeout Errors | prometheus | data |
| 112 | 69 | below | timeseries | Track Rate-Limiter Wait p95 | prometheus | data |
| 113 | 74 | below | bargauge | Monitor Available Rate-Limit Tokens | prometheus | data |
| 31 | 79 | below | stat | Monitor Global Circuit-Breaker State | prometheus | data |
| 32 | 84 | below | timeseries | Track Global Circuit-Breaker Trips | prometheus | data |

### 5. Data Quality `bioetl-dq-v2`
- Question: What is the DQ assessment of the selected Run ID?
- Answer panel: 9406 Review Selected Run Status
- Next action token: Open Run Explorer
- Basis tokens: SELECTED RUN; QUERY ERROR
- Data: Saved HTTP evidence. NOW / RUN / RANGE are not equal severity chips.
- Snapshot panels: 8. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | Navigate Dashboards |  | chrome |
| 9400 | 2 | first-window | text | Understand Evidence Scope |  | chrome |
| 9406 | 5 | first-window | table | Review Selected Run Status | BioETL Ops HTTP | data |
| 9402 | 10 | first-window | table | Inspect Run Identity | BioETL Ops HTTP | data |
| 9403 | 10 | first-window | table | Inspect Processed Records | BioETL Ops HTTP | data |
| 9450 | 15 | first-window | row | Inspect Saved Run Evidence |  | chrome |
| 9451 | 16 | first-window | table | Inspect Selected Run Domains | BioETL Ops HTTP | data |
| 9452 | 28 | below | table | Inspect Selected Run Identity | BioETL Ops HTTP | data |

### 6. Incident Workspace `bioetl-incident-v1`
- Question: What is the highest-confidence active suspect?
- Answer panel: 2010 Inspect Ranked Suspects
- Next action token: Open Pipeline Diagnostics
- Basis tokens: TIME RANGE; VALID_EMPTY
- Data: Suspects are GLOBAL. VALID_EMPTY is not a healthy fleet. Scope status palette is OK/WARN/CRIT/UNKNOWN. CRIT is rule urgency, not confirmed cause.
- Snapshot panels: 25. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | Navigate Dashboards |  | chrome |
| 9400 | 2 | first-window | text | Understand Incident Scope |  | chrome |
| 9401 | 2 | first-window | stat | Monitor Scope Status | prometheus | data |
| 2001 | 5 | first-window | text | Start Incident Triage |  | chrome |
| 2010 | 7 | first-window | table | Inspect Ranked Suspects | prometheus | data |
| 2005 | 12 | first-window | table | Monitor Global Alerts | prometheus | data |
| 2020 | 17 | first-window | row | Review Alert Evidence |  | chrome |
| 2006 | 18 | first-load | state-timeline | Track Alert State History | prometheus | data |
| 2099 | 18 | first-load | row | Domain Suspect Details · GLOBAL / CURRENT |  | chrome |
| 2002 | 19 | first-load | table | Inspect Runtime Suspects | prometheus | data |
| 2100 | 19 | first-load | row | Inspect Selected Run Summary |  | chrome |
| 2101 | 20 | first-load | table | Review Selected Run Status | BioETL Ops HTTP | data |
| 32010 | 20 | first-load | row | Browse Global Suspects |  | chrome |
| 22010 | 21 | first-load | table | Inspect Global Suspects (Full) | datasource | chrome |
| 32005 | 21 | first-load | row | Browse Global Alerts |  | chrome |
| 9450 | 22 | first-load | row | Inspect Saved Run Evidence |  | chrome |
| 22005 | 22 | first-load | table | Monitor Global Alerts (Full) | datasource | chrome |
| 9451 | 23 | first-load | table | Inspect Selected Run Domains | BioETL Ops HTTP | data |
| 9700 | 23 | first-load | row | Inspect Current Workflow Evidence |  | chrome |
| 9701 | 24 | first-load | table | Review Current Workflow Evidence | prometheus | data |
| 2003 | 26 | first-load | table | Inspect Provider Suspects | prometheus | data |
| 2004 | 30 | below | table | Inspect DQ Suspects | prometheus | data |
| 2007 | 32 | below | text | Assess Impact & Confidence |  | chrome |
| 9452 | 35 | below | table | Inspect Selected Run Identity | BioETL Ops HTTP | data |
| 22011 | 37 | below | table | Inspect Global Signal Measurements | prometheus | data |

