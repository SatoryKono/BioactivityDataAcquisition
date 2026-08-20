---
id: prompt.fragment.dashboard-requirements-audit
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Bind dashboard audits to DASHBOARD_REQUIREMENTS.md — IDs, bands, gates, ontology
---

## Dashboard requirements audit contract

Normative SSOT for the seven shipped Grafana dashboards:
`docs/01-requirements/DASHBOARD_REQUIREMENTS.md`. Constants:
`docs/03-guides/dashboards/contracts/layout-budgets.yaml`.
Do **not** invent `DASH-*` IDs. Map findings to an existing ID or mark `GAP`.

### Finding binding

Every PROVEN finding MUST include `requirement_id` (`DASH-FIT-004`,
`DASH-DENSITY-002`, …) or `requirement_id: GAP`. Issue title:

`[<uid>][<DASH-id>][P#] one checkable outcome`

`check-dashboard-visual-semantics` PASS ≠ no visual defects (table-wide
`color-background`, PromQL `allValue=$__all` have passed that gate).

### Orchestrator routing (do not double-run)

| Host | Dashboard card contours |
| --- | --- |
| `prompt.audit.sequential-run` step 9 | full set below (presentation-plane) |
| `prompt.observability.sequential-run` step 7 | `density-area,density-scalar,fill,pipeline,fit` only — do **not** repeat render/visual/layout/data |
| `grafana-six/*` | STOP; map to `grafana-audit.*` |

One evidence pack per checkout SHA. Dedupe `uid+panel_id+requirement_id+root_cause`.

### MONITORING — fail-closed

Default **`MONITORING=false`** (ADR-010). Do not start
`docker-compose.monitoring.yml` unless the operator set `true` **and** a live
render/query is required.

| Evidence class | When `MONITORING=false` |
| --- | --- |
| Static JSON / contract tests / QA `--check` | always run; FAIL is a dashboard defect |
| Live PromQL / Playwright / screenshot / DOM | `Not Verifiable` + blocker, **not** a defect |
| Data correctness | never from screenshot; need query/HTTP/JSON |

### Portfolio (DASH-PORTFOLIO-001 / DASH-FIT-003)

Audit exactly these UIDs. Canonical answer panel must be root, non-row,
`gridPos.y < FIRST_WINDOW_Y` (`18`).

| UID | Answer panel |
| --- | --- |
| `bioetl-control-plane-v1` | `Monitor Replay Readiness` (`9401`) |
| `bioetl-overview-v2` | `Monitor Fleet Health` (`214`) + `Review First Action` (`215`); `9603` is SELECTED RUN context — do not replace 214/215 |
| `bioetl-runtime` | `Monitor Pipeline Status` (`9401`) |
| `bioetl-provider-health-v2` | `Monitor Fleet Severity` (`9101`) |
| `bioetl-dq-v2` | `Monitor Current DQ Status` (`9401`) |
| `bioetl-incident-v1` | `Inspect Ranked Suspects` (`2010`) |
| `bioetl-run-explorer-v1` | `Inspect Recent Runs` (`3010`); identity/accounting are collapsed `3022`/`3023` |

Default `USER_ROLE=operator` (not analyst / SRE / BI / NOC).

### Bands (do not conflate)

| Band | Rule |
| --- | --- |
| First window (visual fold) | root non-row, `y < FIRST_WINDOW_Y` (`18`) |
| First-load budget | root non-row, `y < FIRST_LOAD_Y_MAX` (`28`) — PromQL/HTTP only (`DASH-PERF-003`) |
| Additional group | Grafana `row` + children |

Inventory columns: `uid \| panel_id \| y \| band=first_window\|first_load\|below\|row`.

### Density (two metrics)

1. **`density-area`** (`DASH-DENSITY-001`): per additional group
   `D_area = A_data/A_total ≥ 0.60` and `D_count ≥ 0.50`.
2. **`density-scalar`** (`DASH-DENSITY-002`): `ρ = values/(w×h)` over
   `stat`/`gauge`/`bargauge` only. Every row with ≥1 scalar:
   `ρ_group > ρ_first_screen`. Exclude `timeseries`/`table`/`text`/`row`.
   A large single-value stat is sparse, not “100% data”.
   Command: `python -m scripts.engineering.qa report-dashboard-scalar-density --check`.

### Ontology (fill / data)

| Signal | Green/OK allowed? |
| --- | --- |
| Documented valid zero (event counter) | yes (`DASH-ZERO-001`) |
| Expected Empty / `valid_empty` | yes — not a coverage gap |
| Missing required CURRENT evidence | no — UNKNOWN/INCOMPLETE (`DASH-STATE-001`) |
| `$__range` on first-window `Monitor*` | FAIL (`DASH-COPY-004`) |
| `run_id` in Prometheus labels/filters | P0 (`DASH-DATA-002`) |
| NULL/absent rendered as healthy 0 | FAIL (`DASH-STATE-001`) |

Verdict cards: `noValue` fail-closed `UNKNOWN…`; mappings encode
`OK/WARN/CRIT/UNKNOWN` (+ `INCOMPLETE` on trust gates). CURRENT vs RANGE vs
exact-run HTTP are not peer badges (`DASH-STATE-004`).

### Geometry / FIT / reflow

- `DASH-FIT-001`: root non-row `max(y+h) ≤ VIEWPORT_ROWS` (`18`)
- `DASH-FIT-002`: no fold straddle `y < 18 < y+h` unless governed-allowlisted
- `DASH-FIT-004`: first-window `text`/`stat`/`table` — in-panel
  `scrollHeight>clientHeight` or `scrollWidth>clientWidth` is FAIL (not page
  scroll). No overflow-clip; do not raise `first_screen_max_panels`
- `DASH-FIT-005`: first-window tables have a bounded row cap
- `DASH-REFLOW-001`: Dark + Light at **browser** 100% and 200% on 1366×768.
  CSS `zoom` on the root is not browser-zoom evidence

### Copy / safety

- `DASH-FIRST-001`: first window answers `state × confidence × basis × next_action`
- `DASH-COPY-003/005`: action-verb titles; unique; no placeholders
- `DASH-COPY-006/002`: verdict description + explicit mappings
- `DASH-COPY-008`: five inline HTML copy roles
- `DASH-TIME-001`: `YYYY-MM-DD HH:mm` (`mm` minutes; `MM` months forbidden)
- `DASH-SEC-001`: no `<script>` / `<iframe>` / `javascript:` / `on*=` in HTML
- `DASH-DATA-003/004`: no loki/tempo/`:8081`/`${DS_*}`; datasource ∈
  Prometheus, `BioETL Ops HTTP`, Grafana
- `DASH-STATE-005`: if Ops HTTP not provisioned — static Prometheus-only
  profile, no query targets, no retention/replay/run verdict

### Executable gates (REQUIREMENTS §8)

Windows: `.\.venv-win\Scripts\python.exe`. Run on preflight and after fixes:

```text
python -m scripts.engineering.qa report-dashboard-inventory --check --json
python -m scripts.engineering.qa check-dashboard-visual-semantics
python -m scripts.engineering.qa check-dashboard-performance-budgets
python -m scripts.engineering.qa report-dashboard-scalar-density --check
python -m pytest tests/integration/test_dashboard_geometry_and_purpose_contracts.py tests/integration/test_dashboard_first_window_containment.py tests/integration/test_dashboard_operator_readability.py tests/integration/test_dashboard_structural_invariants.py tests/integration/test_dashboard_presentation_requirements.py
```

Static gates prove repository structure. They do not replace live datasource
or human usability evidence when `MONITORING=true`.
