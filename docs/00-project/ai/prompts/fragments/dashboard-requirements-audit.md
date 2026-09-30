---
id: prompt.fragment.dashboard-requirements-audit
version: 1.0.1
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

Roster snapshot: `origin/main` `50d92e502e16a424fc8a31a2f7860c28f89fa858` on 2026-09-30. Re-walk `grafana/dashboards/*.json` every cycle.

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
Verdict cards state `OK` / `WARN` / `CRIT` / `UNKNOWN` in the description. Trust gates `1. Trust` (`9422`) and runtime `9998` also state `INCOMPLETE` (`DASH-COPY-006`).
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

`role=chrome` below means no data target; Dashboard-datasource references are data even without their own PromQL `expr` or HTTP `url`. Re-check before calling a required answer panel non-data (`DASH-COPY-007`).

### 0. Run Explorer `bioetl-run-explorer-v1`
- Question: Which pipelines ran most recently, and where are their reports?
- Answer panel: 3010 Inspect Recent Runs (last 10)
- Next action token: opens the persisted Report
- Basis tokens: no exact run; VALID EMPTY
- Data: HTTP index. No Prometheus run_id label. Empty index is VALID EMPTY, not a healthy fleet. Picker 3010 only; identity/records are on destination dashboards.
- Snapshot panels: 2. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1 | 0 | first-window | text | (empty in JSON) |  | chrome |
| 3010 | 3 | first-window | table | Inspect Recent Runs (last 10) | BioETL Ops HTTP | data |

### 1. Trust `bioetl-control-plane-v1`
- Question: Can the selected run be exactly replayed from saved inputs?
- Answer panel: 9422 Review Exact Replay Readiness
- Next action token: View replay checks
- Basis tokens: CURRENT; processing_status; trust_status
- Data: Exact-run HTTP. CURRENT 9401 is not this answer. INCOMPLETE when checkpoint/scrape evidence is missing. processing_status is not trust_status.
- Snapshot panels: 27. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | (empty in JSON) |  | chrome |
| 9400 | 2 | first-window | text | (empty in JSON) |  | chrome |
| 9422 | 2 | first-window | stat | Review Exact Replay Readiness | BioETL Ops HTTP | data |
| 9418 | 5 | first-window | table | Review Selected-Run Trust | BioETL Ops HTTP | data |
| 9416 | 5 | first-window | table | Review Retention Compliance | BioETL Ops HTTP | data |
| 9419 | 14 | first-window | row | Review Lineage Validation |  | chrome |
| 9415 | 15 | first-window | table | Review Lineage Validation | BioETL Ops HTTP | data |
| 902 | 15 | first-window | row | Inspect Checkpoint and Replay Checks |  | chrome |
| 9413 | 16 | first-window | table | Review Checkpoint Validation | BioETL Ops HTTP | data |
| 901 | 16 | first-window | row | Inspect Manifest Validation |  | chrome |
| 9414 | 17 | first-window | table | Review Manifest Validation | BioETL Ops HTTP | data |
| 905 | 17 | first-window | row | Inspect Run Identity Evidence |  | chrome |
| 9407 | 18 | first-load | table | Inspect Identity Values | BioETL Ops HTTP | data |
| 9412 | 18 | first-load | row | Inspect Run Details |  | chrome |
| 9402 | 19 | first-load | table | Review Run Summary | BioETL Ops HTTP | data |
| 9420 | 19 | first-load | row | Inspect Complete Run Discovery |  | chrome |
| 9421 | 20 | first-load | table | Inspect Latest Complete Run | BioETL Ops HTTP | data |
| 9423 | 22 | first-load | table | Review Exact Replay Checks | BioETL Ops HTTP | data |
| 9410 | 26 | first-load | text | Explain Missing Identity Data |  | chrome |
| 9411 | 26 | first-load | text | Explain Missing Record Counts |  | chrome |
| 9403 | 27 | first-load | table | Review Processed Records | BioETL Ops HTTP | data |

Below-fold: walk the shipped JSON, not this fragment.

### 2. Overview `bioetl-overview-v2`
- Question: What is the saved assessment of the selected Run ID?
- Answer panel: 9603 Review Selected Run Status + 9002 Review Run Domains
- Next action token: Open Run Explorer
- Basis tokens: SELECTED RUN; QUERY ERROR
- Data: Saved HTTP evidence. CURRENT fleet chips must not replace 9603/9002. QUERY ERROR is not OK.
- Snapshot panels: 7. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | (empty in JSON) |  | chrome |
| 99 | 2 | first-window | text | (empty in JSON) |  | chrome |
| 9604 | 2 | first-window | stat | Review Overall Verdict | -- Dashboard -- | data |
| 9603 | 5 | first-window | table | Review Selected Run Status | -- Dashboard -- | data |
| 9002 | 5 | first-window | table | Review Run Domains | BioETL Ops HTTP | data |
| 9300 | 11 | first-window | table | Review Run Identity | BioETL Ops HTTP | data |
| 9301 | 11 | first-window | table | Review Processed Records | BioETL Ops HTTP | data |

### 3. Pipeline Diagnostics `bioetl-runtime`
- Question: What is the saved runtime assessment of the selected Run ID?
- Answer panel: 9998 Review Selected Run Status
- Next action token: Open Run Explorer
- Basis tokens: SELECTED RUN; QUERY ERROR
- Data: Saved HTTP evidence for the selected Run ID. Missing 9998 is DASH-FIT-003. INCOMPLETE on missing required evidence; QUERY ERROR is not OK.
- Snapshot panels: 10. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | (empty in JSON) |  | chrome |
| 9400 | 2 | first-window | text | (empty in JSON) |  | chrome |
| 9998 | 2 | first-window | table | Review Selected Run Status | BioETL Ops HTTP | data |
| 9402 | 7 | first-window | table | Inspect Pipeline Identity | BioETL Ops HTTP | data |
| 9403 | 7 | first-window | table | Inspect Processed Records | BioETL Ops HTTP | data |
| 9450 | 14 | first-window | row | Inspect Saved Run Evidence |  | chrome |
| 9460 | 15 | first-window | table | Inspect Selected Run Stages | BioETL Ops HTTP | data |
| 9451 | 23 | first-load | table | Inspect Selected Run Domains | BioETL Ops HTTP | data |

Below-fold: walk the shipped JSON, not this fragment.

### 4. Provider Health `bioetl-provider-health-v2`
- Question: Which provider is degraded/failing, and why?
- Answer panel: 9461 Review Provider Check
- Next action token: Pipeline Diagnostics
- Basis tokens: SELECTED RUN; QUERY ERROR
- Data: Saved HTTP evidence for the selected provider context. Legacy `9101` is not this answer; it lives on Incident below the fold.
- Snapshot panels: 6. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | (empty in JSON) |  | chrome |
| 9400 | 2 | first-window | text | (empty in JSON) |  | chrome |
| 9461 | 2 | first-window | stat | Review Provider Check | BioETL Ops HTTP | data |
| 9460 | 5 | first-window | table | Review Provider Evidence | BioETL Ops HTTP | data |
| 9402 | 10 | first-window | table | Inspect Run Identity | BioETL Ops HTTP | data |
| 9403 | 10 | first-window | table | Inspect Processed Records | BioETL Ops HTTP | data |

### 5. Data Quality `bioetl-dq-v2`
- Question: What is the DQ assessment of the selected Run ID?
- Answer panel: 9406 Review Selected Run Status
- Next action token: Open Run Explorer
- Basis tokens: SELECTED RUN; QUERY ERROR
- Data: Saved HTTP evidence. NOW / RUN / RANGE are not equal severity chips.
- Snapshot panels: 9. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | (empty in JSON) |  | chrome |
| 9400 | 2 | first-window | text | (empty in JSON) |  | chrome |
| 9406 | 5 | first-window | table | Review Selected Run Status | BioETL Ops HTTP | data |
| 9402 | 10 | first-window | table | Inspect Run Identity | BioETL Ops HTTP | data |
| 9403 | 10 | first-window | table | Inspect Processed Records | BioETL Ops HTTP | data |
| 9450 | 18 | first-load | row | Inspect Saved Run Evidence |  | chrome |
| 9460 | 19 | first-load | table | Inspect Selected Run Stages | BioETL Ops HTTP | data |
| 9451 | 27 | first-load | table | Inspect Selected Run Domains | BioETL Ops HTTP | data |

Below-fold: walk the shipped JSON, not this fragment.

### 6. Incident Workspace `bioetl-incident-v1`
- Question: What is the highest-confidence active suspect?
- Answer panel: 2010 Inspect Ranked Suspects
- Next action token: Open Pipeline Diagnostics
- Basis tokens: TIME RANGE; VALID EMPTY
- Data: Suspects are GLOBAL. VALID_EMPTY is not a healthy fleet. Scope status palette is OK/WARN/CRIT/UNKNOWN. CRIT is rule urgency, not confirmed cause.
- Snapshot panels: 100. Refresh `60s`, timezone `browser`.

| id | y | band | type | title | datasource | role |
| ---: | ---: | --- | --- | --- | --- | --- |
| 1000 | 0 | first-window | text | (empty in JSON) |  | chrome |
| 9400 | 2 | first-window | text | (empty in JSON) |  | chrome |
| 9401 | 2 | first-window | stat | Monitor Scope Status | prometheus | data |
| 2001 | 5 | first-window | text | (empty in JSON) |  | chrome |
| 2010 | 7 | first-window | table | Inspect Ranked Suspects | prometheus | data |
| 2005 | 12 | first-window | table | Monitor Global Alerts | prometheus | data |
| 2020 | 17 | first-window | row | Review Alert Evidence |  | chrome |

Below-fold: walk the shipped JSON, not this fragment.
