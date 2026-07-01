# BioETL Provider Health v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-provider-health-v2.json`

## Overview

Dashboard `3. Provider Health` monitors provider current status, health-check latency/outcomes, adapter retry exhaustion, HTTP errors, rate limiting, and circuit breaker state. Shipped dashboard JSON is the source of truth.

## Key Panels

### 1. Review Dashboard Navigation
- **Type:** Text
- **Purpose:** Explain dashboard navigation and escalation flow.
- **Data sources:** Dashboard variables and operator copy.

### 2. Provenance
- **Type:** Text
- **Purpose:** Show run ID, manifest ID, and replay provenance anchors.
- **Data sources:** Dashboard variables and operator copy.

### 3. Status
- **Type:** Stat
- **Purpose:** Current provider severity for the selected scope.
- **Data sources:** `bioetl_provider_current_status`

### 4. ID
- **Type:** Table
- **Purpose:** Show run ID, pipeline, run type, and timestamp.
- **Data sources:** `bioetl_pipeline_runs`

### 5. Processed Records
- **Type:** Table
- **Purpose:** Show records processed by stage.
- **Data sources:** `bioetl_records_processed_total`

### 6. Monitor GLOBAL Provider Severity Matrix
- **Type:** Table
- **Purpose:** Show global provider severity matrix.
- **Data sources:** `bioetl_provider_current_status`

### 7. Inspect Critical Providers
- **Type:** Table
- **Purpose:** Show critical providers with issues.
- **Data sources:** `bioetl_provider_current_status`

### 8. Inspect Provider Top Causes
- **Type:** Table
- **Purpose:** Show top provider failure causes.
- **Data sources:** `bioetl_provider_current_cause`

### 9. Monitor Provider Telemetry Freshness
- **Type:** Stat
- **Purpose:** Show provider telemetry freshness.
- **Data sources:** `bioetl_provider_range_operational_ok`

### 10. First Action
- **Type:** Text
- **Purpose:** Guide operator to next triage action.
- **Data sources:** Dashboard variables and operator copy.

### 11. Track Health Check Latency by Provider (p95)
- **Type:** Timeseries
- **Purpose:** Show health check latency p95 by provider.
- **Data sources:** `bioetl_health_check_latency_seconds_bucket`

### 12. Review Raw Provider Health Enum
- **Type:** Table
- **Purpose:** Show raw provider health enum values.
- **Data sources:** `bioetl_health_check_provider_universe_15m`

### 13. Monitor Healthy Checks (Selected Range)
- **Type:** Stat
- **Purpose:** Count healthy health checks.
- **Data sources:** `bioetl_health_check_success_total`

### 14. Track Provider Failure Rate (Selected Range)
- **Type:** Gauge
- **Purpose:** Show provider failure rate.
- **Data sources:** `bioetl_health_check_failures_total`

### 15. Track Health Checks Total (Selected Range)
- **Type:** Stat
- **Purpose:** Count total health checks.
- **Data sources:** `bioetl_health_check_success_total`, `bioetl_health_check_degraded_total`, `bioetl_health_check_failures_total`

### 16. Monitor Degraded Checks (Selected Range)
- **Type:** Stat
- **Purpose:** Count degraded health checks.
- **Data sources:** `bioetl_health_check_degraded_total`

### 17. Track Failure and Degraded Trend by Provider
- **Type:** Timeseries
- **Purpose:** Show failure and degraded trend by provider.
- **Data sources:** `bioetl_health_check_failures_total`, `bioetl_health_check_degraded_total`

### 18. Track Provider Failure Share (Selected Range)
- **Type:** Bargauge
- **Purpose:** Show provider failure share.
- **Data sources:** `bioetl_health_check_failures_total`

### 19. Track Retries Exhausted by Provider/Operation
- **Type:** Table
- **Purpose:** Show retry exhaustion by provider and operation.
- **Data sources:** `bioetl_data_source_retry_exhausted_total`

### 20. Track Retries Exhausted Trend by Provider/Operation
- **Type:** Timeseries
- **Purpose:** Show retry exhaustion trend.
- **Data sources:** `bioetl_data_source_retry_exhausted_total`

### 21. Selected Provider Detail
- **Type:** Row
- **Purpose:** Row-based provider detail workflow.
- **Data sources:** `bioetl_adapter_request_duration_seconds_bucket`, `bioetl_http_request_errors_total`

### 22. Inspect Provider Health Check Latency (p95) - $provider
- **Type:** Gauge
- **Purpose:** Show health check latency p95 for selected provider.
- **Data sources:** `bioetl_health_check_latency_seconds_bucket`

### 23. Inspect Adapter Request Latency by Endpoint (p95)
- **Type:** Timeseries
- **Purpose:** Show adapter request latency p95 by endpoint.
- **Data sources:** `bioetl_adapter_request_duration_seconds_bucket`

### 24. Inspect Rate Limit Errors by Method
- **Type:** Timeseries
- **Purpose:** Show rate limit errors by method.
- **Data sources:** `bioetl_http_request_errors_total`

### 25. Inspect Network Timeout Errors by Method
- **Type:** Timeseries
- **Purpose:** Show network timeout errors by method.
- **Data sources:** `bioetl_http_request_errors_total`

### 26. Track Rate Limiter Wait by Provider (p95)
- **Type:** Timeseries
- **Purpose:** Show rate limiter wait time p95.
- **Data sources:** `bioetl_rate_limiter_wait_seconds_bucket`

### 27. Monitor Minimum Rate Limiter Tokens Available
- **Type:** Bargauge
- **Purpose:** Show minimum rate limiter tokens available.
- **Data sources:** `bioetl_rate_limiter_tokens_available`

### 28. Monitor Cross-Scope Adapter Circuit Breaker State (max)
- **Type:** Stat
- **Purpose:** Show cross-scope circuit breaker state.
- **Data sources:** `bioetl_circuit_breaker_state`

### 29. Track Cross-Scope Adapter Circuit Breaker Trips
- **Type:** Timeseries
- **Purpose:** Show circuit breaker trips over time.
- **Data sources:** `bioetl_circuit_breaker_trips_total`

## Variables

- `provider` is the primary selector.
- `pipeline_context` is a hidden handoff context from pipeline-scoped dashboards.

## Notes

- Provider health uses the health-check, adapter, HTTP, rate-limiter, and circuit-breaker families above.
- Legacy provider request-success/rate-limited placeholders are intentionally not documented here.
