# BioETL Provider Health v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-provider-health-v2.json`

## Overview

Dashboard `4. Provider Health` monitors provider current status, health-check latency/outcomes, adapter retry exhaustion, HTTP errors, rate limiting, and circuit breaker state. Shipped dashboard JSON is the source of truth.

The current first-window answer `9461` reports the saved provider check for the
selected Run ID. `SELECT RUN` means a Run ID has not been selected; `VALID EMPTY`
means no saved provider check; `QUERY ERROR` means backend or request failure.
A missing verdict stays `UNKNOWN`. The saved verdict does not assess live fleet
health, and a failed request must not be interpreted as an empty successful check.

Failure-rate, degraded-check, network/timeout, and rate-limit diagnostics retain
empty Prometheus results as `No data`/`UNKNOWN`; metric absence is never rendered
as a synthetic green zero.

Provider defaults to All and lists observed provider identities. GLOBAL fleet
tables ignore the Provider selector; selected-provider status and request
diagnostics use it. Navigation without provider context resets Provider=All.

## Key Panels

### Review Provider Evidence

The saved-run table shows Provider, Data source, Check performed, Check result,
Reason, Observed at, and Evidence. Confirmed cached Bronze means `No` check,
with `—` for its result and timestamp; `Open report` opens the saved run report.
`UNKNOWN` means the saved evidence cannot establish the value. A saved provider
probe does not by itself prove that the run fetched its input from the remote API.
Reasons wrap within the table. Observed timestamps retain their recorded timezone.
Expand Inspect Provider HTTP Details to see recorded Response time, ms, HTTP
status and Checked endpoint. Only saved non-null facts create detail rows;
missing HTTP diagnostics are not inferred.

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

### 4–5. Run identity and processed records — removed

These panels are no longer shown on Provider Health. Review Provider Check
uses nine of 24 grid columns, leaving fifteen columns for the scope explanation.

### 6. Monitor Fleet Status
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

### 22. Inspect Health p95
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

### 28. Monitor Global Circuit-Breaker State
- **Type:** Stat
- **Purpose:** Show cross-scope circuit breaker state.
- **Data sources:** `bioetl_circuit_breaker_state`

### 29. Track Global Circuit-Breaker Trips
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

## Additional shipped panels
### 32. Inspect Health Evidence

Shipped in `bioetl-provider-health-v2.json`.
### 33. Inspect Fleet Non-OK and Causes

Shipped in `bioetl-provider-health-v2.json`.
### 34. Inspect Full Fleet Evidence

Shipped in `bioetl-provider-health-v2.json`.
### 35. Inspect Full Fleet Severity

Shipped in `bioetl-provider-health-v2.json`.
### 36. Inspect Full Non-OK Providers

Shipped in `bioetl-provider-health-v2.json`.
### 37. Inspect Full Provider Causes

Shipped in `bioetl-provider-health-v2.json`.

Circuit-breaker panels are GLOBAL ADAPTER evidence, independent of the Provider selector. Navigation preserves the visible Pipeline selection; legacy pipeline_context is not its authority. Absent health-check series are TELEMETRY MISSING, not a measured zero.

## Saved evidence and discovery panels

| ID | Title | Purpose |
| --- | --- | --- |
| 9450 | Inspect Saved Run Evidence | Saved exact-run evidence; expand for identity, version, reasons and actions. |
| 9451 | Inspect Selected Run Domains | Saved exact-run evidence; expand for identity, version, reasons and actions. |
| 9452 | Inspect Selected Run Identity | Saved exact-run evidence; expand for identity, version, reasons and actions. |

<!-- BEGIN SHIPPED PANEL INVENTORY -->
## Current shipped panel inventory

Generated from the dashboard JSON. Earlier sections explain panel semantics; this table identifies the panels shipped in the current dashboard.

| ID | Title | Type |
| --- | --- | --- |
| 9400 | Understand Selected Run | text |
| 9461 | Review Provider Check | stat |
| 9460 | Review Provider Evidence | table |
| 9471 | Inspect Provider HTTP Details | row |
| 9462 | Inspect Provider HTTP Details | table |
<!-- END SHIPPED PANEL INVENTORY -->
