# Observability fill-audit issue pack — 2026-08-17

**Wave code:** OBS-FILL  
**Date:** 2026-08-17  
**Plan:** `reports/observability/remediation/20260817/plan.md`  
**Baseline:** `reports/observability/remediation/20260817/baseline.md`

**Prior closed issues (not live-proven):** [#8920](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8920),
[#8921](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8921).
Those closed `completed` the same day. A later live re-check still shows
`count(bioetl_pipeline_runs_total)=empty`,
`bioetl_runtime_trust_gap_status_10m=1`, and zero Pushgateway `bioetl_*`
series. This wave owns the remaining **publication topology** gap.

## Context

Six-board fill audit (`chembl_assay` / `backfill` / `chembl_baseline` /
`64927f44-df86-533f-bcaa-1554d5105473` / `now-12h..now`):

| Surfaces | Data-backed | Filled | Empty | Query errors | Static |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 148 | 122 | 43 | 79 | 0 | 26 |

Exact-run Ops HTTP is healthy. Current Prometheus operational layer is not.
Fail-closed UNKNOWN / INCOMPLETE / RULE/SERIES GAP are correct.

Live re-check (health server + monitoring up):

- `up{job="bioetl"}=1`, `bioetl_health_server_scrape_up=1`
- `/metrics` has HELP/TYPE for `bioetl_pipeline_runs_total` but **no samples**
- Pushgateway has **zero** `bioetl_*` series
- Ops HTTP `pipeline-run-reports` `index_state=ok`

Root cause: CLI run and `bioetl health server` are different processes.
Increment in `PipelineObserver` is canonical; the scraped surface never
receives a sample, and restart does not rehydrate from ledger.

## Constraints (all children)

- No invented Prometheus series names
- No `run_id` Prom labels
- No PromQL `or vector(0)` on first-screen verdicts
- No dashboard JSON rewrite before emission/publication is fixed
- No tech-debt budget increases
- Grafana remains optional (ADR-010)

## Issue matrix

| Code | Pri | Issue | Title |
| --- | --- | --- | --- |
| OBS-FILL-00 | meta/P0 | [#8927](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8927) | Restore current Prometheus truth after six-board fill audit |
| OBS-FILL-01 | P0 | [#8930](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8930) | Publish and rehydrate `bioetl_pipeline_runs_total` on the scraped surface |
| OBS-FILL-02 | P0 | [#8928](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8928) | Contract-test chembl_assay/backfill metric surface across restart |
| OBS-FILL-03 | P1 | [#8929](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8929) | Separate semantic empty from telemetry absence on Provider/DQ/Incident |
| OBS-FILL-04 | P1 | [#8931](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8931) | Reconcile exact-run Ops HTTP success with current Prometheus presence |
| OBS-FILL-05 | P2 | [#8932](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8932) | Repeat six-board 148-surface acceptance audit |

## Dependency order

1. [#8930](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8930) (publication + rehydrate)
2. [#8928](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8928) (tests; can start fixtures in parallel, must prove 01)
3. [#8929](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8929) and [#8931](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8931) after the trust anchor is present
4. [#8932](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8932) last
