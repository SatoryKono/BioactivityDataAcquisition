# Observability Checklist

*Reference: [RULES.md §3.2](../../RULES.md#32-наблюдаемость-observability)*

This checklist ensures all components meet the project's observability requirements.

## Adapter Requirements

Every adapter in `src/bioetl/infrastructure/adapters/` **MUST** implement:

### 1. Health Check Method

```python
async def health_check(self) -> bool:
    """Check if the external service is reachable.

    Returns:
        True if service is healthy, False otherwise.
    """
```

**Health Check Endpoints by Provider:**

| Provider | Health Check |
|----------|--------------|
| ChEMBL | `GET /chembl/api/data/status.json` |
| PubChem | `GET /rest/pug/compound/cid/2244/property/MolecularFormula/JSON` |
| UniProt | Lightweight Search Probe |
| Generic | `GET /` or `/status` with 5s timeout |

### 2. Structured Logging

All log messages **MUST** include:

| Field | Required | Example |
|-------|----------|---------|
| `run_id` | MUST | UUID |
| `pipeline` | MUST | `chembl_activity` |
| `stage` | MUST | `extract`, `transform`, `load` |
| `dataset` | SHOULD | `chembl.activity` |

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

*Reference: [RULES.md §3.2.2](../../RULES.md#322-prometheus-metrics)*

### Required Metrics (prefix: `bioetl_`)

| Metric | Type | Labels |
|--------|------|--------|
| `pipeline_duration_seconds` | Histogram | pipeline, stage, status, run_type |
| `records_processed_total` | Counter | pipeline, stage, run_type |
| `errors_total` | Counter | pipeline, stage, error_code |
| `batch_size_records` | Histogram | pipeline, stage |

### DQ Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `dq_validation_score` | Gauge | pipeline, column, check |
| `data_freshness_seconds` | Gauge | pipeline |

### Provider Health Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `provider_health_status` | Gauge | provider (0=Unhealthy, 1=Degraded, 2=Healthy) |
| `circuit_breaker_state` | Gauge | provider (0=Closed, 1=Half-Open, 2=Open) |
| `circuit_breaker_trips_total` | Counter | provider |

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
2. [ ] Use `structlog` for all logging
3. [ ] Include `run_id` in all log messages
4. [ ] Add rate limiting (TokenBucket)
5. [ ] Register metrics in composition layer
6. [ ] Add integration test with VCR cassette

## Architecture Test

The following test enforces health_check presence:

```python
# tests/architecture/test_layer_dependencies.py
def test_adapters_have_health_check(src_dir: Path) -> None:
    """REQ-OBS-001: All adapters MUST implement health_check()."""
    ...
```

Run with: `make arch-test`
