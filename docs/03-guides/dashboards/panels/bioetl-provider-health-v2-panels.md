# BioETL Provider Health v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-provider-health-v2.json`

## Overview

Dashboard `3. Provider Health` monitors provider current status, health-check latency/outcomes, adapter retry exhaustion, HTTP errors, rate limiting, and circuit breaker state. Shipped dashboard JSON is the source of truth.

Failure-rate, degraded-check, network/timeout, and rate-limit diagnostics retain
empty Prometheus results as `No data`/`UNKNOWN`; metric absence is never rendered
as a synthetic green zero.

## Key Panels

### 2. Understand Evidence Scope
- **Type:** Text
- **Purpose:** Distinguish provider-global fleet evidence from the selected
  provider scope and explain that missing current status requires a Runtime
  telemetry check.
- **Data sources:** Dashboard variables and operator copy; no datasource query.

### 3. Monitor Selected Provider
- **Type:** Stat
- **Purpose:** Current provider severity for the selected scope.
- **Data sources:** `bioetl_provider_current_status`

### 4. Inspect Run Identity
- **Type:** Table
- **Purpose:** Show run ID, pipeline, run type, and timestamp.
- **Data sources:** BioETL Ops HTTP control-plane identity endpoint
  `/ops/control-plane/identity-table`; this is not a Prometheus panel.

### 5. Inspect Processed Records
- **Type:** Table
- **Purpose:** Show Bronze/Silver/Gold counts and denominator-explicit percentages; both numeric columns are right-aligned.
- **Data sources:** BioETL Ops HTTP
  `/ops/observability/processed-records`; this is not a Prometheus panel.

### 6. Monitor Fleet Severity
- **Type:** Table
- **Purpose:** Show global provider severity matrix, sorted worst-first.
- **Data sources:** `bioetl_provider_current_status`

### 7. Inspect Non-OK Providers
- **Type:** Table
- **Purpose:** Show critical providers with issues.
- **Data sources:** `bioetl_provider_current_status`

### 8. Inspect Top Provider Causes
- **Type:** Table
- **Purpose:** Show top provider failure causes.
- **Data sources:** `bioetl_provider_current_cause`

### 9. Monitor Telemetry Presence
- **Type:** Stat
- **Purpose:** Show `PRESENT` only when current selected-provider telemetry
  exists; missing evidence is fail-closed `UNKNOWN`, not green zero. This is
  a presence bit, not sample age. On 1366 the chip sits below the conservative
  fold (`y=15`).
- **Data sources:** `bioetl_provider_current_status`

Selected-provider, range/debug, and run-context panels ship in three collapsed
rows. Expand them only after the fleet severity/cause/presence row identifies
the relevant provider or evidence gap.

### 10. Start Provider Triage
- **Type:** Text
- **Purpose:** Guide operator to next triage action.
- **Data sources:** Dashboard variables and operator copy.

### 11. Track Health-Check Latency p95
- **Type:** Timeseries
- **Purpose:** Show health check latency p95 by provider.
- **Data sources:** `bioetl_health_check_latency_seconds_bucket`

### 12. Inspect Raw Health Status
- **Type:** Table
- **Purpose:** Show raw provider health enum values.
- **Data sources:** `bioetl_health_check_provider_universe_15m`

### 13. Monitor Healthy Checks
- **Type:** Stat
- **Purpose:** Count healthy health checks.
- **Data sources:** `bioetl_health_check_success_total`

### 14. Track Failure Rate
- **Type:** Stat
- **Purpose:** Show provider failure rate as neutral selected-range supporting
  evidence at 0%; WARN `>=5%`, CRIT `>=20%`.
- **Data sources:** `bioetl_health_check_failures_total`

### 15. Monitor Health Checks
- **Type:** Stat
- **Purpose:** Count total health checks.
- **Data sources:** `bioetl_health_check_success_total`, `bioetl_health_check_degraded_total`, `bioetl_health_check_failures_total`

### 16. Monitor Degraded Checks
- **Type:** Stat
- **Purpose:** Count degraded health checks.
- **Data sources:** `bioetl_health_check_degraded_total`

### 17. Track Health Failures & Degradation
- **Type:** Timeseries
- **Purpose:** Show failure and degraded trend by provider.
- **Data sources:** `bioetl_health_check_failures_total`, `bioetl_health_check_degraded_total`

### 18. Track Failure Share
- **Type:** Table
- **Purpose:** Show provider failure share; an empty vector is a visible neutral `No data` state rather than a blank gauge or measured zero.
- **Data sources:** `bioetl_health_check_failures_total`

### 19. Inspect Exhausted Retries
- **Type:** Table
- **Purpose:** Show retry exhaustion by provider and operation.
- **Data sources:** `bioetl_data_source_retry_exhausted_total`

### 20. Track Exhausted Retries
- **Type:** Timeseries
- **Purpose:** Show retry exhaustion trend.
- **Data sources:** `bioetl_data_source_retry_exhausted_total`

### 21. Selected Provider Details
- **Type:** Row
- **Purpose:** Collapsed-by-default provider forensics. Expand when current
  severity or a non-zero selected-range failure signal requires localization.
- **Data sources:** `bioetl_adapter_request_duration_seconds_bucket`, `bioetl_http_request_errors_total`

### 22. Inspect Health-Check Latency p95
- **Type:** Gauge
- **Purpose:** Show health check latency p95 for selected provider.
- **Data sources:** `bioetl_health_check_latency_seconds_bucket`

### 23. Track Request Latency p95
- **Type:** Timeseries
- **Purpose:** Show adapter request latency p95 by endpoint.
- **Data sources:** `bioetl_adapter_request_duration_seconds_bucket`

### 24. Track Rate-Limit Errors
- **Type:** Timeseries
- **Purpose:** Show rate limit errors by method.
- **Data sources:** `bioetl_http_request_errors_total`

### 25. Track Network & Timeout Errors
- **Type:** Timeseries
- **Purpose:** Show network timeout errors by method.
- **Data sources:** `bioetl_http_request_errors_total`

### 26. Track Rate-Limiter Wait p95
- **Type:** Timeseries
- **Purpose:** Show rate limiter wait time p95.
- **Data sources:** `bioetl_rate_limiter_wait_seconds_bucket`

### 27. Monitor Available Rate-Limit Tokens
- **Type:** Bargauge
- **Purpose:** Show minimum rate limiter tokens available.
- **Data sources:** `bioetl_rate_limiter_tokens_available`

### 28. Monitor Circuit-Breaker State
- **Type:** Stat
- **Purpose:** Show cross-scope circuit breaker state.
- **Data sources:** `bioetl_circuit_breaker_state`

### 29. Track Circuit-Breaker Trips
- **Type:** Timeseries
- **Purpose:** Show circuit breaker trips over time.
- **Data sources:** `bioetl_circuit_breaker_trips_total`

### 30. Range & Debug Evidence
- **Type:** Row
- **Purpose:** Group selected-range provider health and transport diagnostics.
- **Data sources:** Prometheus range evidence from the nested panels.

### 31. Run Context
- **Type:** Row
- **Purpose:** Group selected-run identity and processed-record HTTP evidence.
- **Data sources:** BioETL Ops HTTP.

## Variables

- `provider` is the primary selector.
- `pipeline_context` is a hidden handoff context from pipeline-scoped dashboards.

## Notes

- Provider health uses the health-check, adapter, HTTP, rate-limiter, and circuit-breaker families above.
- Failure/degraded trends and provider failure-share stay inside `Selected
  Provider Detail`; zero-range evidence no longer occupies the headline path or
  renders as a dominant red gauge arc.
- Legacy provider request-success/rate-limited placeholders are intentionally not documented here.

### Inspect Full Fleet Evidence

Docs for Inspect Full Fleet Evidence.

### Inspect Full Fleet Severity

Docs for Inspect Full Fleet Severity.

### Inspect Full Non-OK Providers

Docs for Inspect Full Non-OK Providers.

### Inspect Full Provider Causes

Docs for Inspect Full Provider Causes.

### 99. Inspect Full Fleet Evidence

Docs for Inspect Full Fleet Evidence.

### 99. Inspect Full Fleet Severity

Docs for Inspect Full Fleet Severity.

### 99. Inspect Full Non-OK Providers

Docs for Inspect Full Non-OK Providers.

### 99. Inspect Full Provider Causes

Docs for Inspect Full Provider Causes.
