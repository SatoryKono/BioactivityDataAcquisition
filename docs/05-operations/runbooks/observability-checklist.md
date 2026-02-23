# Observability Checklist

*Reference: [RULES.md §3.2](../../00-project/RULES.md#32-%D0%BD%D0%B0%D0%B1%D0%BB%D1%8E%D0%B4%D0%B0%D0%B5%D0%BC%D0%BE%D1%81%D1%82%D1%8C-observability)*

This checklist ensures all components meet the project's observability requirements.

## Adapter Requirements

Every adapter in `src/bioetl/infrastructure/adapters/` **MUST** implement:

### 1. Health Check Method

```python
async def health-check(self) -> HealthStatus:
    """Check if the external service is reachable.

    Returns:
        True if service is healthy, False otherwise.
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
| `run-id`   | MUST     | UUID                           |
| `pipeline` | MUST     | `chembl_activity`              |
| `stage`    | MUST     | `extract`, `transform`, `load` |
| `dataset`  | SHOULD   | `chembl/activity`              |

**Example:**

```python
self.logger.info(
    "Fetching records",
    run-id=ctx.run-id,
    pipeline=ctx.pipeline-name,
    stage="extract",
    offset=offset,
    limit=limit,
)
```

## Pipeline Metrics

*Reference: [RULES.md §3.2.2](../../00-project/RULES.md#322-prometheus-metrics)*

### Required Metrics (prefix: `bioetl-`)

| Metric                      | Type      | Labels                            |
| --------------------------- | --------- | --------------------------------- |
| `pipeline-duration-seconds` | Histogram | pipeline, stage, status, run-type |
| `records-processed-total`   | Counter   | pipeline, stage, run-type         |
| `errors-total`              | Counter   | pipeline, stage, error-code       |
| `batch-size-records`        | Histogram | pipeline, stage                   |

### DQ Metrics

| Metric                   | Type  | Labels                  |
| ------------------------ | ----- | ----------------------- |
| `dq-validation-score`    | Gauge | pipeline, column, check |
| `data-freshness-seconds` | Gauge | pipeline                |

### Provider Health Metrics

| Metric                        | Type    | Labels                                        |
| ----------------------------- | ------- | --------------------------------------------- |
| `provider-health-status`      | Gauge   | provider (0=Unhealthy, 1=Degraded, 2=Healthy) |
| `circuit-breaker-state`       | Gauge   | adapter (0=Closed, 1=Half-Open, 2=Open)       |
| `circuit-breaker-trips-total` | Counter | adapter                                       |
| `circuit-breaker-success-total` | Counter | adapter                                     |
| `circuit-breaker-failure-total` | Counter | adapter                                     |

## Verification Commands

### Check Metrics Endpoint

```bash
# Start metrics server (default port 8000)
curl http://localhost:8000/metrics | grep bioetl-
```

### Verify Adapter Health Checks

```bash
# Run architecture test
pytest tests/architecture/test-layer-dependencies.py::test-adapters-have-health-check -v
```

### Validate Log Schema

```bash
# Check logs for required fields
cat logs/bioetl.log | jq 'select(.run-id and .pipeline and .stage)'
```

## Adding New Adapters

When creating a new adapter:

1. [ ] Implement `health-check()` method
1. [ ] Use `LoggerPort` (injected via DI) for all logging
1. [ ] Include `run-id`, `pipeline`, `stage` in all log messages (Log Schema §3.2.1)
1. [ ] Add rate limiting (TokenBucket)
1. [ ] Register metrics in composition layer (`bootstrap/runtime/observability.py`)
1. [ ] Add integration test with VCR cassette

## Architecture Test

The following test enforces health-check presence:

```python
# tests/architecture/test-layer-dependencies.py
def test-adapters-have-health-check(src-dir: Path) -> None:
    """REQ-OBS-001: All adapters MUST implement health-check()."""
    ...
```

Run with: `make arch-test`
