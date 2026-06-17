# BioETL Provider Health v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-provider-health-v2.json`

## Обзор

Dashboard `3. Provider Health` monitors provider current status, health-check
latency/outcomes, adapter retry exhaustion, HTTP errors, rate limiting, and
circuit breaker state. Shipped dashboard JSON is the source of truth.

## Key Panels

### 1. Provider Status Matrix
- **Type:** Table / Stat
- **Purpose:** Show current provider severity, top causes, and telemetry
  freshness.
- **Data sources:** `bioetl_provider_current_status`,
  `bioetl_provider_current_cause`, `bioetl_provider_range_operational_ok`,
  `bioetl_provider_health_check_provider_universe_15m`

### 2. Health Check Outcomes
- **Type:** Stat / Gauge / Timeseries
- **Purpose:** Track healthy, degraded, and failed checks over the selected
  range.
- **Data sources:** `bioetl_health_check_success_total`,
  `bioetl_health_check_degraded_total`, `bioetl_health_check_failures_total`,
  `bioetl_health_check_latency_seconds_bucket`

### 3. Adapter and HTTP Failure Evidence
- **Type:** Table / Timeseries
- **Purpose:** Inspect retry exhaustion, request latency, HTTP errors, and
  rate-limiter wait.
- **Data sources:** `bioetl_data_source_retry_exhausted_total`,
  `bioetl_adapter_request_duration_seconds_bucket`,
  `bioetl_http_request_errors_total`,
  `bioetl_rate_limiter_wait_seconds_bucket`,
  `bioetl_rate_limiter_tokens_available`

### 4. Circuit Breaker State
- **Type:** Stat / Timeseries
- **Purpose:** Show cross-scope circuit breaker state and trips.
- **Data sources:** `bioetl_circuit_breaker_state`,
  `bioetl_circuit_breaker_trips_total`

## Variables

- `provider` is the primary selector.
- `pipeline_context` is a hidden handoff context from pipeline-scoped
  dashboards.

## Notes

- Provider health uses the health-check, adapter, HTTP, rate-limiter, and
  circuit-breaker families above. Legacy provider request-success/rate-limited
  placeholders are intentionally not documented here.
