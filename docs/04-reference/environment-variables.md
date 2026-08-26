# Environment Variables Reference

This document is a **partial** published reference for commonly used
`BIOETL_*` environment variables. It is not an exhaustive dump of every
runtime key. For the onboarding table and additional pipeline/DQ/quarantine
variables, see [README.md](../../README.md#installation) and `.env.example`.

## Core Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_ENV` | Environment mode (dev, test, prod) | `dev` | No |
| `BIOETL_DATA_DIR` | Directory for data storage | `./data` | No |
| `BIOETL_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` | No |

## Provider API Keys

### UniProt
| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_UNIPROT_API_KEY` | Optional UniProt API key (higher rate limits) | No (public access by default) |

### OpenAlex
| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_OPENALEX_API_KEY` | OpenAlex API key for higher rate limits | No |
| `BIOETL_OPENALEX_EMAIL` | Email for polite pool attribution | No |

### PubMed
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_PUBMED_API_KEY` | PubMed API key for higher rate limits | - | No |
| `BIOETL_PUBMED_EMAIL` | Email for polite pool attribution | empty / unset (adapter returns `None`; no fake identity) | No |

### Semantic Scholar
| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_SEMANTICSCHOLAR_API_KEY` | Semantic Scholar API key | No |

### CrossRef
| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_CROSSREF_EMAIL` | Email for polite pool attribution | No |

## Observability

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_METRICS_PORT` | Prometheus metrics endpoint port | `8000` | No |
| `BIOETL_PROMETHEUS_URL` | Optional Prometheus base URL for local HTTP probes | unset (`http://localhost:9090` loopback default in health/processed-records) | No |
| `BIOETL_OBSERVABILITY__TRACING_ENABLED` | Enable OpenTelemetry tracing | `false` | No |
| `BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD` | Allow NoOp observability in prod | `false` | No |

## Docker Helper (Optional)

| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_DOCKER_HELPER_ADR010_ADJUNCT` | Local-Only Docker helpers governed by ADR-010 | No |

## MCP Shared Runtime (Optional)

| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_MCP_SHARED_API_KEY` | Auth token for MCP shared plane | No |

## Grafana Ops HTTP (Optional)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_GRAFANA_REQUIRE_OPS_HTTP` | Require Ops HTTP provisioning | - | No |
| `BIOETL_GRAFANA_OPS_READY_ATTEMPTS` | Ops ready check attempts | - | No |
| `BIOETL_GRAFANA_OPS_READY_SLEEP_SEC` | Ops ready check sleep seconds | - | No |

## Runtime Identity

| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_RUNTIME_SOURCE_ID` | Managed runtime source identity (injected by runtime_manager.py) | No |

## Report Enforcement

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_ENFORCE_REPORT_ROOT_MARKER` | Enforce report root marker for Grafana | `true` (in docker-compose.yml) | No |

## Telemetry (Optional)

| Variable | Description | Required |
|----------|-------------|----------|
| `BIOETL_TELEMETRY_REFERENCE_NOW` | Injectable reference time for telemetry freshness | No |
| `BIOETL_REQUIRE_TELEMETRY_SOURCE_COMMIT_EQUALS_HEAD` | Require source_commit == HEAD for telemetry | No |

## Windows + WSL Mixed Checkout

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_WSL_VENV_DIR` | WSL virtual environment directory | `$HOME/.venvs/bioetl` | No |
| `BIOETL_PYTEST_WINDOWS_XDIST_WORKERS` | Windows pytest worker count | `1` | No |

## Security Notes

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
