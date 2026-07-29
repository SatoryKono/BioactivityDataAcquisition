## Parent

_TBD_ (DSA-00)

## Problem

Pipeline Diagnostics (`bioetl-runtime`) still mixes runtime blockers with data-path accounting and giant telemetry peers:

- Giant green **SCRAPING** reads as “pipeline healthy”
- Empty Runtime Blockers dominate first screen when healthy
- Wide tables with technical Value # columns
- Exact-run Bronze/Silver accounting appears without automatic Data Trust / Run Explorer handoff

Audit narrative target:

`Run state → Telemetry confidence → Stage flow → Bottleneck → Duration/throughput → Stage evidence → handoff`

## Scope

- [ ] Telemetry/scrape state → compact **confidence chip** (not peer KPI card)
- [ ] Healthy blockers state compact; expand list when non-empty
- [ ] Keep stage lag timeseries contract from DS2-01 (do not reintroduce broken state-timeline on continuous lag)
- [ ] Explicit handoff panels/links for data-path accounting (DQ / Run Explorer)
- [ ] Compress peer error/lag/failed-run giant cards into escalation strip/matrix residual
- [ ] Same-PR test + panel doc updates

## Out of scope

- Waterfall/Sankey (DSA-10 gate)
- Merging Runtime with Run Explorer UID

## Acceptance

- [ ] 5s question: “runtime blocker or data-path handoff?” answerable without scroll essay
- [ ] First-screen decision objects ≤5
- [ ] No continuous metric on state-timeline without frame contract
- [ ] `test_pipeline_runtime_dashboard` + related grafana tests green

## Files

- `grafana/dashboards/bioetl-runtime.json`
- `docs/03-guides/dashboards/panels/bioetl-runtime-panels.md`
- `tests/integration/test_pipeline_runtime_dashboard.py`
