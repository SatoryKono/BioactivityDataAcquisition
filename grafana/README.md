# Grafana Dashboards

This directory contains Grafana dashboards for monitoring BioETL.

## Import Instructions

1.  Login to Grafana (default: `http://localhost:3000`, admin/admin).
2.  Go to **Dashboards** > **New** > **Import**.
3.  Upload the JSON files from the `dashboards/` directory or copy-paste their content.
4.  Select your Prometheus datasource.

## Available Dashboards

### 1. BioETL Overview (`bioetl-overview.json`)
High-level view of pipeline performance.
-   **Records Processed**: Throughput metrics per pipeline/stage.
-   **Error Rates**: Errors broken down by type and pipeline.
-   **Pipeline Status**: Success/Failure counts.

### 2. Provider Health (`bioetl-provider-health.json`)
Monitoring of external data providers.
-   **Health Status**: Healthy/Degraded/Unhealthy state.
-   **Circuit Breakers**: State transitions (Closed/Open/Half-Open).
-   **Rate Limits**: Throttling events.
