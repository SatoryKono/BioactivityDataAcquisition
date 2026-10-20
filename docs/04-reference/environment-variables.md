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

The default log level is `INFO`. Use `bioetl run --debug` or workflow `--log-level`. Settings does not read a log-level environment variable.

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

### Semantic Scholar
| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_SEMANTICSCHOLAR_API_KEY` | Semantic Scholar API key | No |

## Observability

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_METRICS_PORT` | Prometheus metrics endpoint port | `8000` | No |
| `BIOETL_METRICS_ADDR` | Prometheus metrics endpoint address | `0.0.0.0` | No |
| `BIOETL_PROMETHEUS_URL` | Optional Prometheus base URL for local HTTP probes | unset (`http://localhost:9090` loopback default in health/processed-records) | No |
| `BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED` | Enable Prometheus metrics HTTP server (requires `metrics_enabled` to be active) | `True` | No |
| `BIOETL_OBSERVABILITY__METRICS_FAIL_FAST` | If True, exit with error when the metrics server fails to start | `False` declared. `resolve_metrics_fail_fast` (used by `maybe_start_metrics_server`) returns `True` only when `env` is `prod`, `test_mode` is not `True`, and the field was not set explicitly; an explicit `False` is preserved. `bioetl health server` passes the declared value and does not apply that override | No |
| `BIOETL_OBSERVABILITY__METRICS_RETRY_COUNT` | Total number of attempts (not additional retries) for transient errors when starting the metrics server | `3` | No |
| `BIOETL_OBSERVABILITY__METRICS_RETRY_DELAY` | Base delay in seconds for exponential backoff (`retry_delay * 2**attempt`) when starting the metrics server. Defaults use at most 3 attempts and wait 1s then 2s after transient errors | `1.0` | No |
| `BIOETL_OBSERVABILITY__TRACING_ENABLED` | Enable OpenTelemetry tracing | `False` | No |
| `BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD` | Allow NoOp observability in prod | `False` | No |
| `BIOETL_OBSERVABILITY__AUDIT_ENABLED` | Enable file-backed audit logging for Medallion write operations (`FileAuditAdapter` instead of `NoOpAudit`). This variable is not the forensic-grade persistence profile. Profile `forensic_grade` separately requires real audit plus a structured logger, tracing, and metrics, including outside prod; `BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD` does not waive that check | `False` | No |
| `BIOETL_OBSERVABILITY__AUDIT_BASE_PATH` | Optional override path for audit JSONL files. Unset (Python `None`) falls back to `<BIOETL_DATA_DIR>/output/audit` (`data/output/audit` with the default `BIOETL_DATA_DIR`). The environment string `None` is a path and does not select the fallback | unset | No |
| `BIOETL_PUSHGATEWAY_URL` | Pushgateway address for terminal metrics publication | unset | No |

## Runtime Identity

| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_RUNTIME_SOURCE_ID` | Managed runtime source identity (injected by runtime_manager.py) | No |

## Report Enforcement

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_ENFORCE_REPORT_ROOT_MARKER` | Enforce report root marker for Grafana | `True` (in docker-compose.yml) | No |
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
