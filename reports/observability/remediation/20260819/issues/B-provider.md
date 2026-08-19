## Problem

`bioetl_provider_current_status` is still synthesized with a NaN identity

```
(universe * 0) / (universe * 0)
```

D3 can show UNKNOWN while Fleet Severity / Non-OK / Causes stay blank. The operator cannot tell missing telemetry vs stale vs failing. Hidden `$adapter` makes circuit-breaker panels look provider-filtered.

## Proposed solution

**B1.** Publish current status as enum `0=OK, 1=WARN, 2=CRIT, 3=UNKNOWN`. Non-finite / absent source maps to `3`. No NaN in the published current-status series.

**B2.** Export `bioetl_provider_current_status_info{provider,reason,last_success_at,last_attempt_at,source_state}` (or equivalent low-cardinality info metric). D3 first window shows reason + age without reading the panel description.

**B3/B4 (same issue, P1 follow-through in the same PR if cheap):** freshness seconds + stale threshold; adapter-scoped panels titled/labeled as adapter, with `adapter=All` asserted.

Do not invent a control-plane bridge for live provider health.

## Scope

`grafana/prometheus-rules/bioetl_observability.yml`, exporter/recording tests, `bioetl-provider-health-v2.json`, metric declarations.

## Alternatives considered

Leave NaN and document it — rejected; Grafana tables render NaN as empty.

## Acceptance criteria

- [ ] Unit/promtool test: non-finite source → 3, never NaN in `bioetl_provider_current_status`.
- [ ] D3 first window shows status + reason + freshness for UNKNOWN.
- [ ] Cause tables share one empty-state contract (no three independent blanks).
- [ ] Adapter panels do not look like a provider filter when `adapter=All`.
- [ ] No `run_id` Prometheus label; no tech-debt budget increase.

Parent: DASH-SCOPE epic.
