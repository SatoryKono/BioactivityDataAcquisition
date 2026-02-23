# Grafana Dashboard Audit Report

*Date: 2026-02-23 | Auditor: Claude | Scope: grafana/, metrics, observability*

## Inventory

| Artifact | Path | Description |
|----------|------|-------------|
| **Dashboards (4)** | `grafana/dashboards/*.json` | simple, overview-v2, dq-v2, provider-health-v2 |
| **Metric definitions** | `src/bioetl/infrastructure/observability/metrics.py` | 50+ metrics (Histogram, Counter, Gauge) |
| **Prometheus adapter** | `src/bioetl/infrastructure/observability/prometheus_metrics.py` | PrometheusMetrics implements MetricsPort |
| **Metrics server** | `src/bioetl/infrastructure/observability/server.py` | HTTP exposition + Pushgateway push |
| **Demo server** | `docs/03-guides/dashbords/metrics_server.py` | Synthetic metrics for testing |
| **Fix script** | `scripts/fix_grafana_dashboards.py` | Variable injection into PromQL |
| **Provisioning** | `grafana/provisioning/` | datasources + dashboards auto-load |
| **Docker Compose** | `docker-compose.monitoring.yml` | Prometheus + Pushgateway + Grafana |
| **Tests** | `tests/integration/test_grafana_config.py` | JSON validation, metric contract, required vars |
| **Documentation (16 files)** | `docs/03-guides/dashbords/` | ~145KB total |

---

## CRITICAL Issues

### C-1. Duplicate `run_id` variable in all dashboards

In all dashboards except provider-health-v2, the `run_id` template variable is defined **twice** with identical queries. Grafana shows two dropdowns with the same name; the second overwrites the first.

**Affected:** `bioetl-simple.json`, `bioetl-overview-v2.json`, `bioetl-dq-v2.json`

### C-2. Template variables defined but unused in queries

| Variable | Defined in | Used in PromQL |
|----------|-----------|----------------|
| `run_id` | simple, overview-v2, dq-v2 | Nowhere — queries filter only by `$pipeline`, `$run_type` |
| `execution` | simple, overview-v2, dq-v2 | Nowhere |
| `run_id` | provider-health-v2 | Nowhere — queries use `$provider_.*` |
| `pipeline` | provider-health-v2 | Nowhere — queries use `$provider_.*` |

Users see dropdown filters that have no effect on displayed data.

### C-3. DQ dashboard does not show actual Data Quality metrics

`bioetl-dq-v2.json` claims to show "Data Quality metrics" but uses **only** `bioetl_records_processed_total` and `bioetl_records_processed_created`. It is effectively a copy of the overview dashboard.

**Unused DQ metrics (all defined in code):**
- `bioetl_dq_validation_score` — main DQ score (0.0–1.0)
- `bioetl_dq_records_quarantined_total` — quarantined records
- `bioetl_dq_anomaly_detected` — detected anomalies
- `bioetl_dq_baseline_samples` — baseline sample count
- `bioetl_dq_check_duration_ms` — check duration
- `bioetl_dq_soft_threshold_exceeded` — soft threshold violations
- `bioetl_dq_baseline_updated` — baseline updates

### C-4. Massive metric coverage gap

Out of 50+ defined metrics, dashboards visualize only **5** (~10%).

**Not visualized:** all circuit breaker (4), all error metrics (3), batch sizes, pipeline duration, all DQ metrics (7), all transform metrics (2), all HTTP/adapter metrics (8), rate limiter (2), storage/vacuum/archive (6), phase duration, shutdown, policy violations.

### C-5. Demo metrics server incompatible with production schema

`docs/03-guides/dashbords/metrics_server.py` defines metrics with **different labels**:
- Demo: `bioetl_records_processed_total` → labels `['pipeline', 'run_id', 'stage', 'status']`
- Production: `bioetl_records_processed_total` → labels `['pipeline', 'stage', 'run_type']`

Also defines non-existent metrics: `bioetl_processing_duration_seconds`, `bioetl_error_rate`.

---

## HIGH Issues

### H-1. Provider Health dashboard shows minimal data

Only shows health check duration/status. Missing: circuit breaker state/trips, provider health status, HTTP errors, adapter requests, rate limiter, retry analysis.

### H-2. Fragile `$provider_.*` regex in Provider Health

Queries use `pipeline=~"$provider_.*"`, assuming pipeline name format `{provider}_{entity}`. If naming convention changes, the dashboard breaks.

### H-3. Fix script is destructive

`scripts/fix_grafana_dashboards.py` line 70 overwrites ALL template variables with just `pipeline` and `run_id`. Not idempotent. No tests. No dry-run mode.

### H-4. Inconsistent naming in registry keys

Some keys have `bioetl_` prefix, some don't. Callers must guess.

### H-5. PrometheusMetrics silently ignores unknown metrics

No warning when a metric name is not found in the registry — hides instrumentation bugs.

### H-6. Datasource referenced by name, not UID

All dashboards use `"datasource": "Prometheus"` (string name). UID references would be more reliable.

---

## MEDIUM Issues

| ID | Description |
|----|-------------|
| M-1 | `bioetl-simple.json` is redundant (fully overlaps with overview-v2) |
| M-2 | 16 doc files (~145KB) for 4 simple dashboards; many are changelog-style |
| M-3 | Typo in path: `dashbords/` instead of `dashboards/` |
| M-4 | `schemaVersion: 30` is outdated (Grafana 8.x era) |
| M-5 | `docker-compose.monitoring.yml` uses deprecated `version: '3.8'` |
| M-6 | `host.docker.internal` in prometheus.yml doesn't work on Linux Docker |
| M-7 | Corrupted Unicode in dq-v2 panel title (mojibake arrows) |
| M-8 | Division by zero in simple dashboard Quality Ratio (missing `clamp_min`) |

---

## LOW Issues

| ID | Description |
|----|-------------|
| L-1 | `grafana/README.md` is 34K lines — excessive |
| L-2 | No alerting rules configured |
| L-3 | `refresh: "5s"` in simple dashboard is too aggressive for batch pipeline |
| L-4 | No dashboard links between dashboards for navigation |
| L-5 | Excessive tags on dashboards |

---

## Refactoring Plan

### Phase 1: Critical dashboard fixes (RF-GRAF-001) — P0

| Step | Action | Files |
|------|--------|-------|
| 1.1 | Remove duplicate `run_id` variables | simple, overview-v2, dq-v2 |
| 1.2 | Remove unused `execution` variable | simple, overview-v2, dq-v2 |
| 1.3 | Add `run_id` filter to PromQL queries or remove variable | all |
| 1.4 | Fix division by zero in simple dashboard (`clamp_min`) | simple |
| 1.5 | Fix corrupted Unicode in dq-v2 title | dq-v2 |
| 1.6 | Unify datasource to UID reference | all 4 dashboards |

### Phase 2: Real DQ dashboard (RF-GRAF-002) — P0

Rewrite `bioetl-dq-v2.json` panels:

| Panel | Metric | Type |
|-------|--------|------|
| DQ Validation Score | `bioetl_dq_validation_score` | Gauge |
| Quarantined Records | `bioetl_dq_records_quarantined_total` | Time series by error_type |
| DQ Anomalies | `bioetl_dq_anomaly_detected` by severity | Bar chart / stat |
| DQ Check Latency | `bioetl_dq_check_duration_ms` (p50, p95, p99) | Histogram quantile |
| Baseline Stability | `bioetl_dq_baseline_samples` | Gauge |
| Soft Threshold Violations | `bioetl_dq_soft_threshold_exceeded` | Counter rate |
| Gold/Bronze Ratio | keep as summary | Gauge |
| Data Flow overview | `records_processed_total` by stage | Time series |

### Phase 3: Full Provider Health dashboard (RF-GRAF-003) — P1

Add sections for: Circuit Breaker, HTTP Performance, Adapter Activity, Rate Limiter, Retry Analysis, Provider Status. Replace fragile `$provider_.*` regex.

### Phase 4: Overview consolidation (RF-GRAF-004) — P2

Remove `bioetl-simple.json`. Extend overview-v2 with: pipeline duration, errors, batch size. Add row grouping and dashboard links.

### Phase 5: Demo metrics server (RF-GRAF-005) — P1

Sync label sets with production definitions. Add DQ, circuit breaker, adapter metric generation. Remove non-existent metrics.

### Phase 6: Fix script refactoring (RF-GRAF-006) — P2

Make non-destructive (merge variables). Add `--dry-run`. Ensure idempotency. Write tests.

### Phase 7: Naming consistency (RF-GRAF-007) — P1

Unify registry keys (remove `bioetl_` prefix inconsistency). Add warning log for unknown metric names.

### Phase 8: Infrastructure & docs (RF-GRAF-008) — P3

Fix typo `dashbords/` → `dashboards/`. Consolidate 16 docs into 3–4. Fix docker-compose. Add Linux support. Add basic alerting rules.

### Phase 9: Extended tests (RF-GRAF-009) — P2

Add tests: no duplicate variables, all variables used in queries, datasource by UID, no corrupted Unicode, clamp_min in division queries, metric coverage threshold (≥50%).

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Metrics visualized / defined | ~10% (5/50+) | ≥60% |
| Dashboards with duplicate vars | 3/4 | 0/4 |
| Unused template variables | ~8 | 0 |
| DQ metrics on DQ dashboard | 0 | ≥5 |
| Provider metrics on Provider dashboard | 2 | ≥8 |
| Test assertions for dashboards | 3 | ≥9 |
| Doc files | 16 | ≤4 |
