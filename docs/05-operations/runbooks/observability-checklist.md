# Observability Checklist

*Reference: [RULES.md §3.2](../../00-project/RULES.md#32-наблюдаемость-observability)*

> Runtime profile: Local-Only single-instance (ADR-010). Observability checks assume one local process and local log/metrics endpoints.

This checklist ensures all components meet the project's observability requirements.

## Adapter Requirements

Every adapter in `src/bioetl/infrastructure/adapters/` **MUST** implement:

### 1. Health Check Method

```python
async def health_check(self) -> HealthStatus:
    """Check if the external service is reachable.

    Returns:
        HealthStatus (HEALTHY, DEGRADED, UNHEALTHY).
    """
```

**Health Check Endpoints by Provider:**

| Provider | Health Check                                                     |
| -------- | ---------------------------------------------------------------- |
| ChEMBL   | `GET /chembl/api/data/status`                                    |
| PubChem  | `GET /rest/pug/compound/cid/2244/property/MolecularFormula/JSON` |
| UniProt  | Lightweight Search Probe                                         |
| Generic  | `GET /` or `/status` with 5s timeout                             |

### 2. Structured Logging

All log messages **MUST** include:

| Field      | Required | Example                        |
| ---------- | -------- | ------------------------------ |
| `run_id`   | MUST     | UUID                           |
| `pipeline` | MUST     | `chembl_activity`              |
| `stage`    | MUST     | `extract`, `transform`, `load` |
| `dataset`  | SHOULD   | `chembl/activity`              |

**Example:**

```python
self.logger.info(
    "Fetching records",
    run_id=ctx.run_id,
    pipeline=ctx.pipeline_name,
    stage="extract",
    offset=offset,
    limit=limit,
)
```

## Pipeline Metrics

*Reference: [RULES.md §3.2.2](../../00-project/RULES.md#322-prometheus-metrics)*

### Required Metrics (prefix: `bioetl_`)

| Metric                      | Type      | Labels                            |
| --------------------------- | --------- | --------------------------------- |
| `pipeline_duration_seconds` | Histogram | pipeline, stage, status, run_type |
| `records_processed_total`   | Counter   | pipeline, stage, run_type         |
| `errors_total`              | Counter   | pipeline, stage, error_code       |
| `batch_size_records`        | Histogram | pipeline, stage                   |

### DQ Metrics

| Metric                   | Type  | Labels                  |
| ------------------------ | ----- | ----------------------- |
| `dq_validation_score`    | Gauge | pipeline, entity |
| `data_freshness_seconds` | Gauge | pipeline, entity |

### Provider Health Metrics

| Metric                        | Type    | Labels                                        |
| ----------------------------- | ------- | --------------------------------------------- |
| `provider_health_status`      | Gauge   | provider (0=UNHEALTHY, 1=DEGRADED, 2=HEALTHY) |
| `circuit_breaker_state`       | Gauge   | adapter (0=CLOSED, 1=HALF_OPEN, 2=OPEN)       |
| `circuit_breaker_trips_total` | Counter | adapter                                        |
| `circuit_breaker_success_total` | Counter | adapter                                      |
| `circuit_breaker_failure_total` | Counter | adapter                                      |

## Verification Commands

### Check Metrics Endpoint

```bash
# Start metrics server (default port 8000)
curl http://localhost:8000/metrics | grep bioetl_
```

### Verify Adapter Health Checks

```bash
# Run architecture test
pytest tests/architecture/test_layer_dependencies.py::test_adapters_have_health_check -v
```

### Validate Log Schema

```bash
# Check logs for required fields
cat logs/bioetl.log | jq 'select(.run_id and .pipeline and .stage)'
```

## Adding New Adapters

When creating a new adapter:

1. [ ] Implement `health_check()` method
1. [ ] Use `LoggerPort` (injected via DI) for all logging
1. [ ] Include `run_id`, `pipeline`, `stage` in all log messages (Log Schema §3.2.1)
1. [ ] Add rate limiting (TokenBucket)
1. [ ] Register metrics in composition layer (`bootstrap/runtime/observability.py`)
1. [ ] Add integration test with VCR cassette

## Architecture Test

The following test enforces health_check presence:

```python
# tests/architecture/test_layer_dependencies.py
def test_adapters_have_health_check(src_dir: Path) -> None:
    """REQ-OBS-001: All adapters MUST implement health_check()."""
    ...
```

Run with: `make test-architecture`
