import re

with open("docs/04-reference/environment-variables.md") as f:
    docs_content = f.read()

# Add missing variables to the Core Configuration table.
new_vars = [
    "| `BIOETL_DEBUG` | Enable debug features | `False` | No |",
    "| `BIOETL_TEST_MODE` | Use fixtures instead of real APIs | `False` | No |",
    "| `BIOETL_STRICT_ERROR_HANDLING` | When True, API client errors raise exceptions instead of being silently ignored. | `False` | No |",
    "| `BIOETL_ARCHIVE_ROOT` | Optional separate local archive root | unset | No |",
]

lines = docs_content.split('\n')
for i, line in enumerate(lines):
    if line.startswith("| `BIOETL_STRICT_MEDALLION`"):
        for var in new_vars[::-1]:
            lines.insert(i+1, var)
        break

# We will need a Pipeline Configuration table
pipeline_table = """
## Pipeline Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_PIPELINE__BATCH_SIZE` | Number of records per batch write | `100` | No |
| `BIOETL_PIPELINE__CHECKPOINT_INTERVAL` | Save checkpoint every N records | `1000` | No |
| `BIOETL_PIPELINE__MAX_CONCURRENT_BATCHES` | Maximum concurrent batch writes | `4` | No |
| `BIOETL_PIPELINE__HEARTBEAT_INTERVAL` | Lock heartbeat interval in seconds | `30` | No |
| `BIOETL_PIPELINE__STRICT_PREFLIGHT` | Block startup on Medallion preflight violations | `True` | No |
| `BIOETL_PIPELINE__RELAXED_DQ` | When True, DQ thresholds are relaxed for testing | `False` | No |
| `BIOETL_PIPELINE__SILVER_RESILIENCE_ENABLED` | Feature flag for adaptive resilience in Silver merge | `True` | No |
| `BIOETL_PIPELINE__HEALTH_CHECK_MODE` | Preflight health-check gate mode (`strict`, `probe`) | `strict` | No |
| `BIOETL_PIPELINE__CONTROL_PLANE__REQUIRED_PERSISTENCE_PROFILE` | Minimum persistence profile | `replay_ready` | No |
| `BIOETL_PIPELINE__CONTROL_PLANE__RUN_MANIFEST_ENABLED` | Create immutable run manifests before execution | `True` | No |
| `BIOETL_PIPELINE__CONTROL_PLANE__RUN_LEDGER_ENABLED` | Append run-ledger events for lifecycle and lineage | `True` | No |
| `BIOETL_PIPELINE__CONTROL_PLANE__CHECKPOINT_COMPATIBILITY_POLICY` | Resume behavior when checkpoint validation fails | `hard_fail` | No |
"""

for i, line in enumerate(lines):
    if line.startswith("## Provider API Keys"):
        lines.insert(i, pipeline_table)
        break

# Add BIOETL_DEFAULT_EMAIL
for i, line in enumerate(lines):
    if line.startswith("### PubMed"):
        # find the table in pubmed
        for j in range(i, i+10):
            if lines[j].startswith("| `BIOETL_PUBMED_API_KEY`"):
                lines.insert(j+1, "| `BIOETL_DEFAULT_EMAIL` | Technical email for NCBI API tool identification | `default@example.com` | No |")
                break
        break

new_content = "\n".join(lines)
with open("docs/04-reference/environment-variables.md", "w") as f:
    f.write(new_content)
