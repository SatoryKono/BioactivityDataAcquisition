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
- **Data sources:** BioETL Ops HTTP control-plane identity endpoint
  `/ops/control-plane/identity-table`; this is not a Prometheus panel.

### 5. Processed Records
- **Type:** Table
- **Purpose:** Show records processed by stage.
- **Data sources:** BioETL Ops HTTP
  `/ops/observability/processed-records`; this is not a Prometheus panel.

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
- **Type:** Stat
- **Purpose:** Show provider failure rate as neutral selected-range supporting
  evidence at 0%; WARN `>=5%`, CRIT `>=20%`.
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
- **Purpose:** Collapsed-by-default provider forensics. Expand when current
  severity or a non-zero selected-range failure signal requires localization.
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

### 30. Range / debug evidence
- **Type:** Row
- **Purpose:** Group selected-range provider health and transport diagnostics.
- **Data sources:** Prometheus range evidence from the nested panels.

### 31. Run context (identity / processed records)
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
