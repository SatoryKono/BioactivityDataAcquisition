# Observability fill-audit correction plan — 2026-08-17

Status: active execution plan (not a metric catalog).
Program: OBS-LIFE-001 / OBS-PROV-001 / OBS-DQ-001.
GitHub epic: [#8927](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8927)
(children #8930, #8928, #8929, #8931, #8932).
Companion: [`baseline.md`](baseline.md).
Trust / exact-run follow-on (D0 `bioetl-control-plane-v1`, not this fill
pass): [`plan_grafana_trust_rf_audit.md`](plan_grafana_trust_rf_audit.md).
Normative: `docs/00-project/RULES.md` §3.2, ADR-010, ADR-017,
`docs/01-requirements/DASHBOARD_REQUIREMENTS.md`,
`docs/03-guides/dashboards/contracts/synthetic-zero-policy.yaml`.

Do **not** invent new Prometheus series names. Restore emission, publication,
and (where the contract already requires it) explicit zero samples of existing
families. Do **not** mask absence with PromQL `or vector(0)` on first-screen
verdicts.

## 1. Verified fill-audit snapshot

Date: 2026-08-17. Scope: six operator boards (Trust / `bioetl-control-plane-v1`
is out of this fill pass).

Selectors used by the audit: `pipeline=chembl_assay`, `run_type=backfill`,
`workflow=chembl_baseline`, `run_id=64927f44-df86-533f-bcaa-1554d5105473`,
range `now-12h..now`, timezone `Europe/Kiev`.

| Category | Count | Meaning |
| --- | ---: | --- |
| Surfaces | 148 | Non-row panels on the six boards |
| Data-backed | 122 | At least one enabled query target |
| Filled data-backed | 43 | ≥1 Prometheus series or Ops HTTP row |
| Empty data-backed | 79 | Successful query, no series/rows |
| Query execution errors after Grafana variable normalization | 0 | No panel HTTP/PromQL errors |
| Static / text / nav | 26 | No metrics required |

Per-board (audit, matches current `grafana/dashboards/*.json` non-row counts):

| Board | uid | Total | Filled | Empty | Static | Verdict |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1. Overview | `bioetl-overview-v2` | 22 | 15 | 4 | 3 | Incomplete: Fleet Health + four domains UNKNOWN |
| 2. Pipeline Diagnostics | `bioetl-runtime` | 36 | 8 | 22 | 6 | INCOMPLETE + RULE/SERIES GAP |
| 3. Provider Health | `bioetl-provider-health-v2` | 31 | 2 | 26 | 3 | UNKNOWN: no chembl health/freshness evidence |
| 4. Data Quality | `bioetl-dq-v2` | 32 | 4 | 23 | 5 | UNKNOWN current DQ; exact-run accounting present |
| 5. Incident Workspace | `bioetl-incident-v1` | 11 | 3 | 4 | 4 | UNKNOWN; alerts present, suspects empty |
| 6. Run Explorer | `bioetl-run-explorer-v1` | 16 | 11 | 0 | 5 | Fully filled exact-run / recent-runs |

Headline: **exact-run Ops HTTP is healthy; current Prometheus operational
layer is not trustworthy.** Fail-closed UNKNOWN / INCOMPLETE / RULE/SERIES GAP
are correct, not UI defects.

## 2. Live re-verification (same day, after monitoring start)

Re-checked against the running local stack (`bioetl` scrape + Pushgateway +
Grafana bootstrap `ops_http=ready`).

| Probe | Result | Matches audit? |
| --- | --- | --- |
| `up{job="bioetl"}` | `1` (`instance=bioetl:8000`) | yes |
| `bioetl_health_server_scrape_up` | `1` | yes (transport + liveness) |
| `GET :8000/metrics` `bioetl_pipeline_runs_total` | HELP/TYPE only, **no samples** | yes |
| `count(bioetl_pipeline_runs_total)` | empty vector | yes |
| `bioetl_runtime_trust_gap_status_10m` | `1` | yes |
| `bioetl_runtime_trust_gap_active_10m` | `1` | yes |
| `count(bioetl_runtime_current_status)` | empty | yes (cascade) |
| `count(bioetl_provider_current_status)` | empty | yes |
| `count(bioetl_dq_current_status)` | empty | yes |
| `count(bioetl_l0_status)` | empty | yes |
| `count({job="pushgateway",__name__=~"bioetl_.*"})` | empty | **new fact** |
| Ops HTTP `pipeline-run-reports?pipeline=chembl_assay` | `index_state=ok`, recent `success` | yes (exact-run layer) |

`BioETLMetricsEndpointUnavailable` (`absent_over_time(bioetl_pipeline_runs_total[10m])`)
is therefore a **domain-metric absence** alert, not a TCP/HTTP scrape failure.
`BioETLDockerRuntimeProbeMissing` remains a separate Docker-runtime probe signal.

## 3. Root cause (refined)

`baseline.md` already names the canonical increment site:
`PipelineObserver._record_pipeline_run_metrics` →
`bioetl_pipeline_runs_total{pipeline,run_type,status}` and forbids a second
increment in `PipelineRunnerService`. That increment contract is still correct.

The fill-audit gap is **publication topology**, not a missing increment call in
the observer:

1. Docker default surface is `bioetl health server` on `:8000`. Its process
   registry registers the Counter (HELP/TYPE) but never calls `labels(...).inc()`
   unless a pipeline runs **in that same process**. Prometheus client therefore
   emits no sample.
2. Real `chembl_assay` / `backfill` runs happen in a **separate CLI process**.
   They write durable artifacts (Run Explorer / Ops HTTP) and may best-effort
   `publish_metrics_safely` → Pushgateway.
3. Live Pushgateway has **zero** `bioetl_*` series. So the second intended
   trust path is also empty.
4. Recording rules (`bioetl_runtime_trust_gap_status_10m`, current status /
   universe / L0) all key off `bioetl_pipeline_runs_total` or downstream
   current-* recordings. Absence cascades to Overview, Runtime, Provider, DQ,
   and Incident.

Exact-run HTTP (identity, accounting Bronze 1000 / Silver valid 1000 / Gold
valid 983 / Gold quarantined 0) is independent and already works.

## 4. What not to change

- Do not treat the 79 empty data-backed panels as 79 bugs. Classify each as
  **missing required telemetry**, **semantic empty** (no events), or
  **not applicable**.
- Do not add PromQL `or vector(0)` on first-screen verdicts
  (`synthetic-zero-policy.yaml`). Explicit emit-time zero samples for an
  **existing scope** are allowed; masking absence as OK is not.
- Do not invent new metric names or `run_id` Prometheus labels.
- Do not start from dashboard JSON rewrites. Fix emission + publication first.
- Do not raise tech-debt budgets.

## 5. Work packages

### P0 — Restore the current-metrics contract on the scraped surface

**Owner lane:** application observability + health server + composition publish.

1. Keep a single increment of `bioetl_pipeline_runs_total` in
   `PipelineObserver` on terminal outcome (`success` / `failed` / `shutdown`).
2. Make publication to the **scraped** surface reliable after every terminal
   run:
   - either Pushgateway push must succeed and stay visible to Prometheus
     (`job=pushgateway`, grouping `pipeline` + `run_type`);
   - or the long-lived health server must adopt the same samples (shared
     registry / scrape federation / explicit republish). Best-effort
     `publish_metrics_safely` that returns `False` is not enough for P0.
3. After health-server restart, **rehydrate** the trust-anchor series from
   durable manifest/ledger (last terminal outcomes per known
   `pipeline`×`run_type`) so `absent_over_time(...[10m])` does not flip to 1
   solely because the process restarted.
4. Guarantee the minimum current families already consumed by the six boards:
   runtime activity/status, DQ current status/reasons, provider health
   universe/status, control-plane manifest/ledger/checkpoint signals. For
   in-scope entities, zero-event cases MUST emit a zero sample so “no
   problems” ≠ “no telemetry”.

**Done when:**

- `count(bioetl_pipeline_runs_total{pipeline="chembl_assay",run_type="backfill"}) > 0`
  on Prometheus after a terminal run **and** after health-server restart
  (within the 10m window).
- `bioetl_runtime_trust_gap_status_10m == 0`.
- Runtime `Monitor Pipeline Status` is not INCOMPLETE solely due to missing
  anchor; `Monitor Metrics Coverage` is not RULE/SERIES GAP.
- `BioETLMetricsEndpointUnavailable` is clear.

### P0 — Contract tests for the chembl_assay / backfill surface

Add regression coverage (unit + focused integration / promtool where already
used):

1. Terminal run increments `bioetl_pipeline_runs_total` exactly once with
   labels `pipeline`, `run_type`, `status`.
2. Process restart of the health server still exposes the rehydrated sample
   before 10m elapse.
3. Prometheus instant/range queries and Grafana scoped queries agree for the
   fixture (`chembl_assay` / `backfill`, Bronze 1000 / Silver 1000 / Gold 983 /
   excluded_by_contract 17 / quarantine 0).
4. Required panel labels exist: `pipeline`, `run_type`, `provider`, `stage`,
   `status`, `outcome`, `severity` as already declared by each family.
5. Existing tests that forbid `PipelineRunnerService` from incrementing the
   counter stay red if that regression returns.

Reuse `grafana/prometheus-rules/tests/bioetl_observability.test.yml` trust-gap
cases; add a live-or-fixture scrape assertion rather than only promtool input
series.

### P1 — Separate semantic zero from telemetry absence

Follow `synthetic-zero-policy.yaml` and `verdict-ontology.md`:

- Required current surfaces: emit explicit zero series bound to the known
  universe (pipeline / provider / stage). Empty PromQL remains UNKNOWN /
  INCOMPLETE / telemetry_missing.
- Optional / event tables (quarantine, rejects, ranked suspects): keep empty
  as “no active events” **only when** the parent trust/coverage verdict is
  OK/PRESENT. Otherwise show the parent gap, not a fake “None observed”.
- Prefer existing incomplete encodings (`trusted status=3`,
  `telemetry_missing`) over new copy-only states. If a panel needs
  VALID_EMPTY / NOT_APPLICABLE, add it as **panel contract / noValue /
  description**, not as a new Prom series.

Especially Provider Health (`Inspect Non-OK Providers` / `Top Causes` are
valid empty only with Fleet Severity=OK and Telemetry Presence=PRESENT), DQ
current reasons, and Incident suspect tables.

### P1 — Reconcile exact-run HTTP with current Prometheus

Ops HTTP already proves durable success. Add a self-check that compares the
latest successful manifest/ledger for a pipeline with Prometheus presence of
the minimum current families. If a durable success exists and the trust
anchor is absent, emit an explicit reason/alert (reuse
`BioETLMetricsEndpointUnavailable` or a sibling recording already in
`bioetl_observability.yml` — do not invent a parallel name without an ADR).

This closes the operator contradiction: Run Explorer = success, Overview =
UNKNOWN.

### P2 — Repeat the six-board acceptance audit

After P0/P1, re-run the 148-surface pass with the same selectors.

Target: every one of the 79 previously empty data-backed panels is either
filled or classified semantic-empty / not-applicable in a checked registry
(panel id, query, expected state). No required fail-closed series may remain
indistinguishable from “no events”.

Keep the row-level registry next to this plan
(`panel_audit_detail.md` when produced). `docs/03-guides/dashboards/metrics-readiness-matrix.md`
currently marks first-screen series `Ready? yes`; refresh that matrix only
after P0 is proven live.

## 6. Suggested implementation order

1. Prove Pushgateway publication from a real `chembl_assay` backfill (or
   explain why it is empty today: URL, grouping, metric_names filter).
2. Add health-server rehydrate from ledger for `bioetl_pipeline_runs_total`.
3. Seed/emit remaining current-* families already defined in
   `grafana/prometheus-rules/bioetl_observability.yml`.
4. Contract tests (restart + labels + fixture accounting).
5. Reconciliation check vs Ops HTTP latest success.
6. Semantic-empty panel contracts + six-board re-audit.

## 7. Out of scope for this plan

- Dashboard System 2.0 Phase-2 visual residual (`#6828` / DUX2-*).
- Reintroducing Loki / Tempo / Silver Reject Explorer (ADR-010).
- New boards, `run_id` Prom labels, or invented series.
- Changing fail-closed first-screen policy to synthetic zeros.
