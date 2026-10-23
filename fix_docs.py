import re

with open("docs/04-reference/environment-variables.md") as f:
    content = f.read()

# ADD CORE CONFIGS
core_addition = """
| `BIOETL_DEBUG` | Enable debug features | `False` | No |
| `BIOETL_TEST_MODE` | Use fixtures instead of real APIs | `False` | No |
| `BIOETL_STRICT_ERROR_HANDLING` | When True, API client errors raise exceptions instead of being silently ignored | `False` | No |
| `BIOETL_ARCHIVE_ROOT` | Optional separate local archive root | unset | No |"""

if "BIOETL_DEBUG" not in content:
    content = content.replace(
        "| `BIOETL_STRICT_MEDALLION` | When True, schema drift in Silver layer raises SchemaEvolutionError | `False` | No |",
        "| `BIOETL_STRICT_MEDALLION` | When True, schema drift in Silver layer raises SchemaEvolutionError | `False` | No |" + core_addition
    )

# ADD PIPELINE CONFIGS
pipeline_section = """
## Pipeline Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_PIPELINE__BATCH_SIZE` | Number of records per batch write | `100` | No |
| `BIOETL_PIPELINE__CHECKPOINT_INTERVAL` | Save checkpoint every N records | `1000` | No |
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
"""

if "## Pipeline Configuration" not in content:
    content = content.replace(
        "## Provider API Keys",
        pipeline_section.strip() + "\n\n## Provider API Keys"
    )

# ADD PUBMED DEFAULT EMAIL
email_addition = """
| `BIOETL_DEFAULT_EMAIL` | Technical email for NCBI API tool identification | `default@example.com` | No |"""

if "BIOETL_DEFAULT_EMAIL" not in content:
    content = content.replace(
        "| `BIOETL_PUBMED_API_KEY` | PubMed API key for higher rate limits | - | No |",
        "| `BIOETL_PUBMED_API_KEY` | PubMed API key for higher rate limits | - | No |" + email_addition
    )

# ADD METRICS_ENABLED
metrics_enabled_addition = """
| `BIOETL_METRICS_ENABLED` | Enable metrics collection | `True` | No |"""

if "BIOETL_METRICS_ENABLED" not in content:
    content = content.replace(
        "| `BIOETL_METRICS_PORT` | Prometheus metrics endpoint port | `8000` | No |",
        "| `BIOETL_METRICS_PORT` | Prometheus metrics endpoint port | `8000` | No |" + metrics_enabled_addition
    )

with open("docs/04-reference/environment-variables.md", "w") as f:
    f.write(content)
