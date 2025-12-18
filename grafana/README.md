# BioETL Grafana Dashboards

This directory contains pre-built Grafana dashboards for monitoring BioETL pipelines.

## Available Dashboards

### 1. BioETL Overview (`bioetl-overview.json`)

Main dashboard for pipeline health and throughput monitoring.

**Panels:**
- **Pipeline Status**: Success/failure counts, success rate, average duration
- **Pipeline Runs by Status**: Time series of runs by outcome (success/failure/shutdown)
- **Pipeline Duration (p50/p95)**: Latency percentiles by pipeline
- **Records Processed**: Bronze/Silver/Gold/Quarantined record counts
- **Records by Layer (Stacked)**: Time series of record throughput
- **Errors by Type**: Bar chart of error classifications
- **Error Distribution**: Pie chart of error breakdown
- **Data Quality Rejection Rate**: Percentage of quarantined records
- **Circuit Breaker State**: Current state per provider (CLOSED/HALF-OPEN/OPEN)
- **Provider Health Status**: Current health per provider (HEALTHY/DEGRADED/UNHEALTHY)
- **Data Freshness Lag**: Time since last successful data update

### 2. BioETL Provider Health (`bioetl-provider-health.json`)

Detailed dashboard for individual provider monitoring.

**Panels:**
- **Provider Status Overview**: Health status cards for ChEMBL, PubChem, UniProt
- **Circuit Breakers**: Per-provider circuit breaker state
- **Circuit Breaker State History**: Timeline of state transitions
- **Circuit Breaker Trips**: Count of OPEN transitions per provider
- **API Response Time (p95)**: Latency by provider
- **Request Rate**: Requests per second by provider
- **Errors by Provider**: Error type breakdown for each provider
- **Rate Limit Hits**: Rate limiting (429) errors over time
- **Timeout Errors**: Connection/read timeout errors over time

## Importing Dashboards

### Method 1: Grafana UI Import

1. Open Grafana in your browser
2. Navigate to **Dashboards** > **Import** (or press `+` > **Import**)
3. Click **Upload JSON file**
4. Select the dashboard JSON file from this directory
5. Select your Prometheus data source
6. Click **Import**

### Method 2: Grafana Provisioning (Recommended for Production)

Add to your Grafana provisioning configuration:

**`/etc/grafana/provisioning/dashboards/bioetl.yaml`:**

```yaml
apiVersion: 1

providers:
  - name: 'BioETL'
    orgId: 1
    folder: 'BioETL'
    folderUid: 'bioetl'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards/bioetl
```

Then copy the JSON files to `/var/lib/grafana/dashboards/bioetl/`.

### Method 3: Docker Compose

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./grafana/dashboards:/var/lib/grafana/dashboards/bioetl:ro
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
```

## Required Prometheus Metrics

These dashboards expect the following metrics to be available:

### Pipeline Metrics
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `pipeline_duration_seconds` | Histogram | `pipeline_name`, `run_type`, `status` | Pipeline run duration |
| `records_processed_total` | Counter | `pipeline_name`, `run_type`, `layer` | Records by layer |
| `records_bronze_total` | Counter | `pipeline` | Bronze layer records |
| `records_silver_total` | Counter | `pipeline` | Silver layer records |
| `records_gold_total` | Counter | `pipeline` | Gold layer records |
| `records_quarantined_total` | Counter | `pipeline` | Quarantined records |
| `errors_total` | Counter | `pipeline_name`, `error_code` | Errors by type |

### Provider Health Metrics
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `circuit_breaker_state` | Gauge | `provider` | 0=CLOSED, 1=HALF-OPEN, 2=OPEN |
| `circuit_breaker_trips_total` | Counter | `provider` | Times circuit opened |
| `health_status` | Gauge | `provider` | 0=UNHEALTHY, 1=DEGRADED, 2=HEALTHY |
| `data_freshness_lag_seconds` | Gauge | `pipeline_name` | Seconds since last update |

### HTTP Metrics (Optional)
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_request_duration_seconds` | Histogram | `provider` | API call latency |
| `http_requests_total` | Counter | `provider` | Total API calls |

## Customization

### Data Source

Both dashboards use a variable `${datasource}` for the Prometheus data source.
This is automatically populated from available Prometheus sources.

### Time Range

Default time range is 6 hours with 30-second auto-refresh.
Adjust in dashboard settings as needed.

### Adding New Providers

To add a new provider to the Provider Health dashboard:

1. Duplicate an existing provider panel (e.g., ChEMBL status panel)
2. Edit the PromQL query to filter by the new provider name
3. Update panel title

## Alerting

These dashboards are designed for visualization. For alerting, consider:

1. **Grafana Alerting**: Add alert rules directly to panels
2. **Prometheus Alertmanager**: Define alert rules in Prometheus

Example alert rules for Alertmanager:

```yaml
groups:
  - name: bioetl
    rules:
      - alert: PipelineFailureRate
        expr: |
          sum(increase(pipeline_duration_seconds_count{status="failure"}[1h])) /
          sum(increase(pipeline_duration_seconds_count[1h])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High pipeline failure rate"

      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state == 2
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker open for {{ $labels.provider }}"

      - alert: DataFreshnessLag
        expr: data_freshness_lag_seconds > 86400
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Data freshness lag > 24h for {{ $labels.pipeline_name }}"
```

## Troubleshooting

### No data showing

1. Verify Prometheus is scraping the BioETL metrics endpoint
2. Check the metrics server is running: `curl http://localhost:8000/metrics`
3. Verify metric names match (check for typos in labels)

### Panels show "No data"

1. Adjust time range - metrics may not have been emitted yet
2. Run a pipeline to generate metrics
3. Check Prometheus targets are healthy

### Dashboard not loading

1. Check Grafana logs for JSON parsing errors
2. Verify Grafana version >= 9.0 (uses v10 dashboard schema)
