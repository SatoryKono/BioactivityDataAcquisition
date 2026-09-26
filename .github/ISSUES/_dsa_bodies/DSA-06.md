## Parent

_TBD_ (DSA-00)

## Problem

Provider Health (`bioetl-provider-health-v2`) still has low information yield:

- Status + fleet matrix + freshness simultaneously UNKNOWN without composite explanation
- Critical Providers No data vs Top Causes VALID_EMPTY — operator cannot tell “no problems” vs “no signal”
- First Action may still leak raw markdown chrome
- Empty trends / 0.00% / optional latency no-data consume first-screen height
- Selected-provider detail remains large when selector empty
- Little propagation view (provider → affected pipelines)

## Scope

- [ ] Fleet verdict = **state × freshness/confidence** (single strip)
- [ ] Matrix sort: critical → degraded → unknown/stale → healthy
- [ ] Top causes always paired with freshness/VALID_EMPTY taxonomy
- [ ] Selected-provider detail **conditional** (after selection), optional latency not first-screen
- [ ] Compact small multiples for error/retry only when useful; collapse empty trends
- [ ] Handoffs to Incident / Runtime / Run Explorer with scope

## Out of scope

- Native node graph topology (DSA-10)
- Inventing dependency edges without data contract
- New high-cardinality labels

## Acceptance

- [ ] 5s: confirmed degradation vs telemetry blind spot distinguishable
- [ ] First-screen decision objects ≤5
- [ ] Empty selector does not dominate with empty detail tables
- [ ] Provider dashboard integration tests green

## Files

- `grafana/dashboards/bioetl-provider-health-v2.json`
- `docs/03-guides/dashboards/panels/*provider*`
- `tests/integration/test_grafana_*.py`
