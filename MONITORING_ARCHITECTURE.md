# Архитектура мониторинга BioETL (активная конфигурация)

## Топология сети (docker-compose.monitoring.yml)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          HOST (Windows WSL / macOS)                     │
│                                                                         │
│  Published ports (127.0.0.1):                                          │
│  ├─ :3000    → Grafana UI                                              │
│  ├─ :9090    → Prometheus API + UI                                     │
│  ├─ :9091    → Pushgateway metrics ingestion                           │
│  ├─ :8000    → BioETL health + /metrics endpoint                       │
│  └─ :9093    → AlertManager                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
         ↓ Docker Bridge
┌─────────────────────────────────────────────────────────────────────────┐
│                 Docker Network: bioetl-monitoring (50a1bb65f93b)        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Prometheus Container                                             │   │
│  │ Image: prom/prometheus:v3.13.1                                  │   │
│  │ Internal: prometheus:9090                                       │   │
│  │ Role: TSDB (Time Series DB), PromQL engine, rule evaluator    │   │
│  │ Config: /etc/prometheus/prometheus.yml                         │   │
│  │ Storage: prometheus-data volume (2 GiB limit, 7d retention)   │   │
│  │                                                                 │   │
│  │  ┌─ SCRAPE CONFIG (job=bioetl)                               │   │
│  │  │  Interval: 30s                                            │   │
│  │  │  Target: bioetl:8000/metrics  ←─── DNS resolution       │   │
│  │  │  Relabel: instance="bioetl:8000", job="bioetl"          │   │
│  │  └─ Stores time series in TSDB every 30s                    │   │
│  │                                                                 │   │
│  │  HEALTHCHECK: GET /-/healthy → "Prometheus Server is Healthy" │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           ↑                                    ↓                        │
│        scrapes                          PromQL queries                  │
│           │                                    ↓                        │
│  ┌────────┼────────────────────────────────────────────────────────┐   │
│  │ BioETL Container                    │                           │   │
│  │ Image: bioetl-main-bioetl                  Grafana Container   │   │
│  │ Internal: bioetl:8000              │ Image: grafana/grafana:12.0.0 │
│  │ Role: App health + metrics export   │ Internal: grafana:3000       │
│  │ Entrypoint: bioetl health server    │ Role: Visualization layer    │
│  │                                      │ Config: provisioning/ (auto) │
│  │  ┌─ HTTP Endpoints                  │ Storage: grafana-data volume │
│  │  │  :8000/health      → liveness   │ Plugins: Infinity 3.8.0      │
│  │  │  :8000/health/live → readiness  │ Auth: admin / $GF_PASS       │
│  │  │  :8000/health/ready→ readiness  │ Datasources:                 │
│  │  │  :8000/metrics      → export    │   - Prometheus (canonical)   │
│  │  └─ Metrics Format                  │   - BioETL Ops HTTP (∞)      │
│  │     text/plain v0.0.4               │                               │
│  │     Examples:                        │  Dashboard Provisioning:     │
│  │     - bioetl_provider_universe      │    - Path: /var/lib/grafana/ │
│  │     - bioetl_records_processed      │      dashboards/             │
│  │     - bioetl_manifest_integrity     │    - Update interval: 30s    │
│  │     - bioetl_dq_quarantine          │    - allowUiUpdates: false   │
│  │                                      │    - 7 shipped JSON UIDs     │
│  │  ┌─ prometheus_client library      │                               │
│  │  │  Counter, Gauge, Histogram      │  Renderer (internal):        │
│  │  │  Labels: pipeline, provider,    │    Chromium for PDF/PNG      │
│  │  │  stage, run_type, error_type    │    Memory: 3 GiB limit       │
│  │  └─ Separate HTTP server thread    │    Port: 8081 (internal)     │
│  │                                      │                               │
│  │  HEALTHCHECK: GET /health/live      │  HEALTHCHECK:               │
│  │    → 200 OK (every 15s)            │    GET /api/health → 200    │
│  └──────────┬──────────────────────────┴───────────────────────────┘   │
│             │                                   ↑                      │
│             │ (bioetl exports metrics)   (Grafana queries)            │
│             │                                   │                      │
│  ┌──────────┴─────────────────────────────────┬──────────────────────┐ │
│  │          Pushgateway Container             │                    │ │
│  │ Image: prom/pushgateway:v1.11.3            │                    │ │
│  │ Internal: pushgateway:9091                 │ Renderer Container │ │
│  │ Role: Batch metrics ingestion / gateway    │ (auto, optional)   │ │
│  │ Config: /etc/pushgateway                   │ Image: grafana-    │ │
│  │ Storage: none (in-memory)                  │   image-renderer   │ │
│  │ Use case: batch jobs, scheduled tasks      │ Internal: 8081     │ │
│  │ Metrics path: /metrics                     │ Role: Screenshot   │ │
│  │ Push API: POST /metrics/job/...            │   rendering        │ │
│  │                                            │ Config: env vars   │ │
│  │ HEALTHCHECK: GET /-/healthy → "OK"        │ Memory: 3 GiB      │ │
│  │                                            │ WebSocket timeout  │ │
│  │                                            │  90s (Chromium)    │ │
│  │                                            │ Network wait:      │ │
│  │                                            │  disabled (Live)   │ │
│  │                                            │ Max concurrency: 1 │ │
│  └────────────────────────────────────────────┴────────────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ AlertManager Container (optional audit)                         │   │
│  │ Image: prom/alertmanager:latest                                 │   │
│  │ Internal: alertmanager:9093                                     │   │
│  │ Role: Alert grouping, routing, deduplication                   │   │
│  │ Config: /etc/alertmanager/alertmanager.yml                     │   │
│  │ Receivers: Slack webhook (when configured)                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
         ↑                                    ↓
   Docker volumes                    Published to host
```

## Dataflow: От кода к графику

```
┌─────────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER                                               │
│                                                                 │
│  BioETL Pipeline (Python)                                      │
│  ├─ domain/ports/observability/metrics.py (MetricsPort)       │
│  ├─ infrastructure/observability/prometheus_metrics.py         │
│  └─ infrastructure/observability/server.py                     │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Pipeline execution                                     │    │
│  │                                                        │    │
│  │ self._metrics.increment_counter(                      │    │
│  │   "records_processed_total",                          │    │
│  │   value=1000,                                         │    │
│  │   labels={                                            │    │
│  │     "pipeline": "chembl_activity",                   │    │
│  │     "stage": "bronze",                               │    │
│  │     "run_type": "incremental"                        │    │
│  │   }                                                   │    │
│  │ )                                                     │    │
│  └────────────────────┬───────────────────────────────────┘    │
│                       ↓                                        │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ prometheus_client library                              │    │
│  │                                                        │    │
│  │ COUNTERS["records_processed_total"]                   │    │
│  │   .labels(pipeline="chembl_activity", ...)            │    │
│  │   .inc(1000)                                          │    │
│  │                                                        │    │
│  │ Stored in-memory: thread-safe metric objects          │    │
│  └────────────────────┬───────────────────────────────────┘    │
└────────────────────┼─────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│ METRICS EXPORT (HTTP Server)                                    │
│                                                                 │
│  prometheus_client.start_http_server(port=8000, addr="0.0.0.0")│
│                                                                 │
│  GET http://0.0.0.0:8000/metrics                              │
│  └─ Serializes all metric objects to Prometheus exposition     │
│     format (text/plain; version=0.0.4)                        │
│                                                                 │
│  Response:                                                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ # HELP bioetl_records_processed_total ...              │    │
│  │ # TYPE bioetl_records_processed_total counter          │    │
│  │ bioetl_records_processed_total{...} 1000.0             │    │
│  │ bioetl_records_processed_total{...} 2500.0             │    │
│  │ ...                                                    │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────┬────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ PROMETHEUS SCRAPE (every 30s for bioetl job)                   │
│                                                                 │
│  Prometheus scheduler (every 30s):                             │
│  1. Resolve "bioetl:8000" via Docker DNS → container IP       │
│  2. GET http://<container_ip>:8000/metrics (with timeout)     │
│  3. Parse exposition format → metric name, labels, value      │
│  4. Append timestamp (current Unix time)                      │
│  5. Store in TSDB as time series                              │
│                                                                 │
│  TSDB entry:                                                   │
│  (metric_name, labels_dict) → [(timestamp1, value1), ...]     │
│                                                                 │
│  Indices for query:                                           │
│  - __name__="bioetl_records_processed_total"                  │
│  - pipeline="chembl_activity"                                │
│  - stage="bronze"                                             │
│  - run_type="incremental"                                    │
│  - instance="bioetl:8000"                                    │
│  - job="bioetl"                                              │
└─────────────────────┬────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ PROMETHEUS STORAGE (TSDB, 2 GiB persistent volume)              │
│                                                                 │
│  /prometheus/wal/           ← Write-ahead log (unflushed)      │
│  /prometheus/chunks_head/   ← In-memory chunk buffer           │
│  /prometheus/01M2DC4PV.../  ← Block storage (compressed)       │
│                                                                 │
│  Compaction policy:                                            │
│  - 2h blocks → compress                                        │
│  - 7d old blocks → delete (retention policy)                  │
│  - 2 GiB hard limit → delete oldest blocks                    │
└─────────────────────┬────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ GRAFANA QUERIES (every dashboard load / auto-refresh)           │
│                                                                 │
│  Panel datasource: Prometheus (uid="prometheus")               │
│  Query type: PromQL                                            │
│  Query example:                                                │
│                                                                 │
│  rate(bioetl_records_processed_total[5m])                     │
│    by (pipeline, stage)                                       │
│                                                                 │
│  Grafana HTTP GET:                                             │
│  /api/v1/query?query=rate(...)&time=<now>                     │
│                                                                 │
│  Prometheus PromQL engine:                                     │
│  1. Parse PromQL expression                                   │
│  2. Search TSDB index for matching time series                │
│  3. Fetch sample values from TSDB                             │
│  4. Apply PromQL function (rate, sum, by, etc.)              │
│  5. Return result vector/matrix                               │
│                                                                 │
│  JSON Response:                                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ {                                                      │    │
│  │   "status": "success",                                │    │
│  │   "data": {                                           │    │
│  │     "resultType": "matrix",                          │    │
│  │     "result": [                                      │    │
│  │       {                                              │    │
│  │         "metric": {                                 │    │
│  │           "pipeline": "chembl_activity",           │    │
│  │           "stage": "bronze"                        │    │
│  │         },                                          │    │
│  │         "values": [                                │    │
│  │           [1789305900, "12.5"],                    │    │
│  │           [1789305930, "13.2"],                    │    │
│  │           ...                                       │    │
│  │         ]                                           │    │
│  │       }                                             │    │
│  │     ]                                               │    │
│  │   }                                                │    │
│  │ }                                                   │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────┬────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ GRAFANA VISUALIZATION (HTML/Canvas/WebGL)                       │
│                                                                 │
│  Dashboard JSON (shipped):                                     │
│  - Panel "Records Processed" (type: graph, id: 102)           │
│  - Datasource: Prometheus (uid="prometheus")                  │
│  - Query targets: [rate(...), sum(...), etc.]                │
│  - Options: axes, legend, tooltips, thresholds                │
│  - Refresh: 30s (matches BioETL scrape interval)              │
│                                                                 │
│  Grafana frontend:                                             │
│  1. Load dashboard JSON from disk/provisioning                │
│  2. Parse panel definitions                                   │
│  3. On load + every 30s: execute PromQL queries               │
│  4. Receive JSON results                                      │
│  5. Transform time series → canvas rendering                 │
│  6. Draw line graph, tooltips, legend                         │
│                                                                 │
│  Browser (http://localhost:3000):                             │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │    │
│  │ ░ Grafana Dashboard: Control Plane v1                ░    │
│  │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │    │
│  │                                                       │    │
│  │  Records Processed (last 6h) [Updated 30s ago]     │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │  ^                                            │  │    │
│  │  │  │        ╱╱ chembl_activity/bronze           │  │    │
│  │  │  │    ╱╱╱                                     │  │    │
│  │  │  │   ╱                                        │  │    │
│  │  │  │  ╱   ╱ chembl_activity/silver             │  │    │
│  │  │  │ ╱   ╱╱                                     │  │    │
│  │  │  │╱   ╱                                       │  │    │
│  │  │ ╱    ╱                                        │  │    │
│  │  │─────┴──────────────────────────────────→ time │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │                                                    │    │
│  │  Legend:  ● chembl_activity/bronze       (avg 12500) │    │
│  │           ● chembl_activity/silver       (avg 12450) │    │
│  │           ● chembl_activity/gold         (avg 12102) │    │
│  │                                                    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                         │    │
│  Operator can:                                         │    │
│  - Click drill-down to filter by pipeline/stage       │    │
│  - Hover for exact value at timestamp                │    │
│  - Export as PNG/PDF (Renderer)                       │    │
│  - Set alerts on threshold violations                 │    │
│  - Compare time ranges                               │    │
└────────────────────────────────────────────────────────────┘
```

## Конфигурационные файлы

```
project_root/
├── docker-compose.monitoring.yml      ← Main Compose for monitoring stack
│   ├── services:
│   │   ├── prometheus (v3.13.1)
│   │   ├── pushgateway (v1.11.3)
│   │   ├── grafana (12.0.0)
│   │   └── renderer (grafana-image-renderer)
│   ├── volumes:
│   │   ├── prometheus-data (persistent TSDB)
│   │   └── grafana-data (persistent dashboards/auth)
│   └── networks:
│       └── bioetl-monitoring (external: true, shared across stacks)
│
├── grafana/
│   ├── prometheus.yml                 ← Prometheus scrape config
│   │   ├── global: scrape_interval=15s (default)
│   │   ├── job=bioetl: scrape_interval=30s, target=bioetl:8000
│   │   ├── job=prometheus, pushgateway, grafana, renderer
│   │   └── rules: /etc/prometheus/rules/*.yml (alerts, recordings)
│   │
│   ├── provisioning/
│   │   ├── datasources-core/
│   │   │   ├── prometheus.yml         ← Datasource: Prometheus
│   │   │   └── bioetl-ops-http.yml    ← Datasource: Infinity plugin
│   │   │
│   │   └── dashboards/
│   │       └── bioetl.yaml            ← Dashboard provisioning (auto-load)
│   │           ├── path: /var/lib/grafana/dashboards
│   │           ├── updateIntervalSeconds: 30
│   │           └── allowUiUpdates: false (source of truth is Git)
│   │
│   ├── dashboards/                    ← 7 shipped JSON dashboards
│   │   ├── bioetl-control-plane-v1.json
│   │   ├── bioetl-overview-v2.json
│   │   ├── bioetl-runtime.json
│   │   ├── bioetl-provider-health-v2.json
│   │   ├── bioetl-dq-v2.json
│   │   ├── bioetl-incident-v1.json
│   │   └── bioetl-run-explorer-v1.json
│   │
│   ├── prometheus-rules/               ← Prometheus alert rules (extensible)
│   │   ├── alert-pipeline.yml          ← Custom alerts (when configured)
│   │   └── recording-rules.yml         ← Perf optimizations (when configured)
│   │
│   └── scripts/
│       ├── bootstrap-datasources.sh    ← Grafana provisioning entrypoint
│       ├── render_nav_bus.py           ← Generate navigation panel
│       └── ...
│
└── src/bioetl/
    ├── domain/ports/observability/
    │   ├── metrics.py                 ← MetricsPort protocol
    │   ├── tracing.py                 ← TracingPort protocol (optional)
    │   └── logging.py                 ← LoggerPort protocol (optional)
    │
    ├── infrastructure/observability/
    │   ├── prometheus_metrics.py       ← PrometheusMetrics adapter
    │   ├── server.py                   ← HTTP /metrics endpoint
    │   ├── metrics.py                  ← Runtime export surface
    │   ├── _metrics_defs_*.py          ← Metric definitions
    │   └── prometheus_metric_registries.py ← Canonical inventory
    │
    └── composition/bootstrap/runtime/
        └── observability.py            ← Wiring (bootstrap_metrics_port)
```

## Режимы работы

### Default (Prometheus-only)
```bash
docker compose -f docker-compose.monitoring.yml up -d \
  prometheus pushgateway grafana renderer
  
# Dashboards show static "Prometheus-only" mode
# Ops HTTP datasource: not provisioned
# Identity panels: fallback to "prometheus_only" mode
```

### Managed (Prometheus + Ops HTTP)
```bash
# When bioetl health server is running on same network:
docker compose up -d  # main stack joins bioetl-monitoring network

docker compose -f docker-compose.monitoring.yml up -d
# Dashboards detect /ops/control-plane/ready on Ops HTTP
# Infinity datasource: fully provisioned
# Identity panels: load live run metadata
```

### Audit (Isolated, read-only)
```bash
python scripts/ops/observability/start_read_only_audit_stack.py \
  --data-root=/path/to/data \
  --log-root=/path/to/logs \
  --timeout-seconds=90
  
# Deploys Loki, Promtail, Tempo (audit-only overlays)
# Reads from external data/logs, does not modify
# Sentinel logs verify write path
# Produces live-panel-audit.json for CI/release gates
```

## Параметры ресурсов (cgroup limits)

```
prometheus:
  mem_limit: 3g
  mem_reservation: 768m
  cpus: 2.0
  oom_score_adj: 200  # Kill renderer first on OOM

pushgateway:
  mem_limit: 512m
  mem_reservation: 64m
  cpus: 0.5

grafana:
  mem_limit: 2g
  mem_reservation: 384m
  cpus: 1.0

renderer (Chromium):
  mem_limit: 3g
  memswap_limit: 3g
  mem_reservation: 512m
  cpus: 1.0
  oom_score_adj: 800  # Kill this first on OOM
  shm_size: 512mb     # Chromium /dev/shm (avoid disable-dev-shm-usage!)
  
Total budget: ~8.5 GiB (safe for 32 GiB hosts with IDE, main, neo4j)
```

## Контрольный список инициализации

```bash
# 1. Ensure networks exist (owner label required)
python scripts/ops/runtime/docker/runtime_manager.py ensure-networks --stack main

# 2. Start main stack (bioetl joins bioetl-monitoring and bioetl-runtime)
python scripts/ops/runtime/docker/runtime_manager.py start --stack main

# 3. Start monitoring stack (opt-in)
docker compose -f docker-compose.monitoring.yml up -d
# or:
python scripts/ops/runtime/docker/runtime_manager.py start --stack monitoring

# 4. Verify chain
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="bioetl")'
# Expected: job=bioetl, instance=bioetl:8000, health=up

# 5. Check PromQL
curl -s 'http://localhost:9090/api/v1/query?query=bioetl_provider_observed_universe' | jq .

# 6. Open Grafana
# http://localhost:3000
# admin / $GF_SECURITY_ADMIN_PASSWORD (first-boot) or $GRAFANA_PASSWORD (live)
```
