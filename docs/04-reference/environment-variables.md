# Environment Variables Reference

This document is a **partial** published reference for commonly used
`BIOETL_*` environment variables. It is not an exhaustive dump of every
runtime key. For the onboarding table and additional pipeline/DQ/quarantine
variables, see [README.md](../../README.md#installation) and `.env.example`.

## Core Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_ENV` | Environment mode (`dev`, `staging`, `prod`). `test` is not a valid mode. | `dev` | No |
| `BIOETL_DATA_DIR` | Directory for data storage | `./data` | No |
| `BIOETL_JSON_ENCODER` | JSON encoder implementation (orjson or stdlib) | `""` | No |
| `BIOETL_SILVER_DEDUP_TIMEOUT_SECONDS` | Timeout budget in seconds for Silver deduplication executor work | `60.0` | No |
| `BIOETL_STRICT_MEDALLION` | When True, schema drift in Silver layer raises SchemaEvolutionError | `False` | No |
| `BIOETL_DEBUG` | Enable debug features | `False` | No |
| `BIOETL_TEST_MODE` | Shortens HTTP retry delays, caps request timeout, ignores YAML input filters, and relaxes some local durability paths. It does not replace provider calls with fixtures and is not an offline mode | `False` | No |
| `BIOETL_STRICT_ERROR_HANDLING` | When True, API client errors raise exceptions instead of being silently ignored | `False` | No |
| `BIOETL_ARCHIVE_ROOT` | Optional separate local archive root | unset | No |

The default log level is `INFO`. Use `bioetl run --debug` or workflow `--log-level`. Settings does not read a log-level environment variable.

## Pipeline Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_PIPELINE__BATCH_SIZE` | Fills `Settings.pipeline.batch_size` and the settings info view. Batch execution reads `pipeline.config.batch_size` from the pipeline YAML, not this variable | `100` | No |
| `BIOETL_PIPELINE__CHECKPOINT_INTERVAL` | Fills `Settings.pipeline.checkpoint_interval`. Checkpoint frequency during execution reads `pipeline.config.checkpoint_interval` from the pipeline YAML, not this variable | `1000` | No |
| `BIOETL_PIPELINE__STRICT_PREFLIGHT` | Block startup on Medallion preflight violations | `True` | No |
| `BIOETL_PIPELINE__RELAXED_DQ` | When True, DQ thresholds are relaxed for testing | `False` | No |
| `BIOETL_PIPELINE__MAX_CONCURRENT_BATCHES` | Maximum concurrent batch writes | `4` | No |
| `BIOETL_PIPELINE__HEARTBEAT_INTERVAL` | Lock heartbeat interval in seconds | `30` | No |
| `BIOETL_PIPELINE__SILVER_RESILIENCE_ENABLED` | Feature flag for adaptive resilience in Silver merge | `True` | No |
| `BIOETL_PIPELINE__HEALTH_CHECK_MODE` | Preflight health-check gate mode | `strict` | No |
| `BIOETL_PIPELINE__CONTROL_PLANE__REQUIRED_PERSISTENCE_PROFILE` | Minimum persistence profile | `replay_ready` | No |
| `BIOETL_PIPELINE__CONTROL_PLANE__RUN_MANIFEST_ENABLED` | Create immutable run manifests before execution | `True` | No |
| `BIOETL_PIPELINE__CONTROL_PLANE__RUN_LEDGER_ENABLED` | Append run-ledger events for lifecycle and lineage | `True` | No |
| `BIOETL_PIPELINE__CONTROL_PLANE__CHECKPOINT_COMPATIBILITY_POLICY` | Resume behavior when checkpoint validation fails | `hard_fail` | No |

### Silver Resilience & Retry Policies

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__ENABLED` | Atomic replace retry policy for Silver metadata sidecars | `True` | No |
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__MAX_RETRIES` | Max retries | `20` | No |
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__BASE_DELAY_SECONDS` | Base delay in seconds | `0.010` | No |
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__MAX_DELAY_SECONDS` | Max delay in seconds | `0.250` | No |
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__ADAPTIVE_BACKOFF` | Use adaptive backoff | `True` | No |
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__JITTER_SECONDS` | Jitter in seconds | `0.010` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__ENABLED` | Commit conflict retry policy for Delta merge | `True` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__MAX_RETRIES` | Max retries | `3` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__BASE_DELAY_SECONDS` | Base delay in seconds | `0.250` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__MAX_DELAY_SECONDS` | Max delay in seconds | `2.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__ADAPTIVE_BACKOFF` | Use adaptive backoff | `True` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__JITTER_SECONDS` | Jitter in seconds | `0.050` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__RETRY_ENABLED` | Dedicated retry controls for timeout | `True` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__MAX_RETRIES` | Max retries | `1` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__BASE_DELAY_SECONDS` | Base delay in seconds | `0.200` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__MAX_DELAY_SECONDS` | Max delay in seconds | `2.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__ADAPTIVE_BACKOFF` | Use adaptive backoff | `True` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__JITTER_SECONDS` | Jitter in seconds | `0.050` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__EXECUTION_TIMEOUT_SECONDS` | Default-profile execution timeout in seconds | `45.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__UNIT_EXECUTION_TIMEOUT_SECONDS` | Unit-profile execution timeout in seconds | `15.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__E2E_EXECUTION_TIMEOUT_SECONDS` | E2E-profile execution timeout in seconds | `600.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__PROFILE` | Retry profile | `default` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__PLAIN_WRITE_PROCESS_ISOLATION` | Process isolation | `False` | No |

## Provider API Keys

### UniProt
| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_UNIPROT_API_KEY` | Optional UniProt API key (higher rate limits) | No (public access by default) |

### OpenAlex
| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_OPENALEX_API_KEY` | API key for production-like OpenAlex runs. This is the production access boundary, not only a higher rate limit. | Yes for production-like runs |


### PubMed
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_PUBMED_API_KEY` | PubMed API key for higher rate limits | - | No |
| `BIOETL_DEFAULT_EMAIL` | Technical email for NCBI API tool identification | `default@example.com` | No |

### Semantic Scholar
| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_SEMANTICSCHOLAR_API_KEY` | Semantic Scholar API key | No |

## Observability

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_METRICS_PORT` | Prometheus metrics endpoint port | `8000` | No |
| `BIOETL_METRICS_ENABLED` | Flat `Settings.metrics_enabled`. Used only when `observability` is absent, and shown in settings info. Standard runtime bootstrap does not let this override `Settings.observability.metrics_enabled` | `True` | No |
| `BIOETL_METRICS_ADDR` | Prometheus metrics endpoint address | `0.0.0.0` | No |
| `BIOETL_PROMETHEUS_URL` | Optional Prometheus base URL for local HTTP probes | unset (`http://localhost:9090` loopback default in health/processed-records) | No |
| `BIOETL_OBSERVABILITY__METRICS_ENABLED` | Runtime metrics switch (`Settings.observability.metrics_enabled`). Metrics bootstrap and the observability builder read this field | `True` | No |
| `BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED` | Enable Prometheus metrics HTTP server (requires `metrics_enabled` to be active) | `True` | No |
| `BIOETL_OBSERVABILITY__METRICS_FAIL_FAST` | If True, exit with error when the metrics server fails to start. `resolve_metrics_fail_fast` (used by `maybe_start_metrics_server`) automatically enables fail-fast only when `env` is `prod`, `test_mode` is not `True`, and the field was not set explicitly; explicit `True` and `False` are preserved. `bioetl health server` passes the declared value and does not apply that override | `False` | No |
| `BIOETL_OBSERVABILITY__METRICS_RETRY_COUNT` | Total number of attempts (not additional retries) for transient errors when starting the metrics server | `3` | No |
| `BIOETL_OBSERVABILITY__METRICS_RETRY_DELAY` | Base delay in seconds for exponential backoff (`retry_delay * 2**attempt`) when starting the metrics server. Defaults use at most 3 attempts and wait 1s then 2s after transient errors | `1.0` | No |
| `BIOETL_OBSERVABILITY__TRACING_ENABLED` | Enable OpenTelemetry tracing | `False` | No |
| `BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD` | Allow NoOp observability in prod | `False` | No |
| `BIOETL_OBSERVABILITY__AUDIT_ENABLED` | Enable file-backed audit logging for Medallion write operations (`FileAuditAdapter` instead of `NoOpAudit`). This variable is not the forensic-grade persistence profile. Profile `forensic_grade` separately requires real audit plus a structured logger, tracing, and metrics, including outside prod; `BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD` does not waive that check | `False` | No |
| `BIOETL_OBSERVABILITY__AUDIT_BASE_PATH` | Optional override path for audit JSONL files. Unset (Python `None`) falls back to `<BIOETL_DATA_DIR>/output/audit` (`data/output/audit` with the default `BIOETL_DATA_DIR`). The environment string `None` is a path and does not select the fallback | unset | No |
| `BIOETL_PUSHGATEWAY_URL` | Pushgateway address for terminal metrics publication | unset | No |
| `BIOETL_OBSERVABILITY__DQ_MONITOR_ENABLED` | Enable data quality monitoring | `True` | No |
| `BIOETL_OBSERVABILITY__DQ_BASELINE_WINDOW` | Number of recent runs to use for baseline calculation | `7` | No |
| `BIOETL_OBSERVABILITY__DQ_Z_SCORE_THRESHOLD` | Z-score threshold for anomaly detection | `2.5` | No |
| `BIOETL_OBSERVABILITY__DQ_MIN_BASELINE_SAMPLES` | Minimum stored baseline length before z-score detection runs (`AnomalyDetector.detect`). Integer, range 1–10. Absolute thresholds are checked first and do not wait for this count. `bootstrap_dq_monitor()` assigns the value after the monitor is created | `3` | No |
| `BIOETL_OBSERVABILITY__DQ_COLD_START_RUNS` | Stored on `ObservabilitySettings` only (integer, range 0–20). `bootstrap_dq_monitor()` leaves the value unused, so early runs still emit absolute-threshold anomalies from `DQ_ERROR_RATE_MAX` and `DQ_QUALITY_SCORE_MIN`. Z-score detection waits on `DQ_MIN_BASELINE_SAMPLES` | `5` | No |
| `BIOETL_OBSERVABILITY__DQ_ERROR_RATE_MAX` | Maximum allowed error rate | `0.10` | No |
| `BIOETL_OBSERVABILITY__DQ_QUALITY_SCORE_MIN` | Minimum quality score threshold | `0.8` | No |

## Runtime Identity

| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_RUNTIME_SOURCE_ID` | Opaque runtime source digest (BIOETL_RUNTIME_SOURCE_ID) | No |

## Report Enforcement

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_ENFORCE_REPORT_ROOT_MARKER` | Fail readiness closed when the run-report root marker is invalid | `False` | No |
| `BIOETL_REPORT_ROOT` | Run-report root override | unset | No |

## Windows + WSL Mixed Checkout

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_WSL_VENV_DIR` | WSL virtual environment directory | `$HOME/.venvs/bioetl` | No |
| `BIOETL_PYTEST_WINDOWS_XDIST_WORKERS` | Windows pytest worker count | `1` | No |

## Security Notes

### PII Security

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_PII_SALT_CURRENT` | Current salt for PII hashing | unset | No |
| `BIOETL_PII_SALT_NEXT` | Next salt for rotation | unset | No |
| `BIOETL_PII_SALT_ROTATION_ACTIVE` | Whether salt rotation is active | `False` | No |

### API Security

- **Secrets**: Environment variables only (`BIOETL_{PROVIDER}_{KEY}`)
- **Never commit secrets**: Store API keys in `.env` file (gitignored)
- **Polite pools**: Some providers offer polite pools with email attribution
- **Rate limits**: API keys enable higher rate limits where available

## Configuration Files

- Main config: `.env` (machine-local, gitignored)
- Example config: `.env.example`
- Docker compose: `docker-compose.yml` (includes default env vars)

## Related Documentation

- [Getting Started Guide](../03-guides/getting-started.md#3-configuration)
- [Quick Start](../03-guides/quick-start.md#setup-3-minutes)
- [Security Policy](../../.github/SECURITY.md)
- [Docker Quick Start](../DOCKER_QUICKSTART.md)
