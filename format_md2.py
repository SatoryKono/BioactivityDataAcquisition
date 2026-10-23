import re

with open("docs/04-reference/environment-variables.md") as f:
    docs_content = f.read()

# ADD RETRY AND TIMEOUT POLICIES
retry_addition = """
### Silver Resilience & Retry Policies

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__ENABLED` | Atomic replace retry policy for Silver metadata sidecars | `True` | No |
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__MAX_RETRIES` | Max retries | `3` | No |
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__BASE_DELAY_SECONDS` | Base delay in seconds | `0.1` | No |
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__MAX_DELAY_SECONDS` | Max delay in seconds | `1.0` | No |
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__ADAPTIVE_BACKOFF` | Use adaptive backoff | `True` | No |
| `BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__JITTER_SECONDS` | Jitter | `0.1` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__ENABLED` | Commit conflict retry policy for Delta merge | `True` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__MAX_RETRIES` | Max retries | `5` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__BASE_DELAY_SECONDS` | Base delay in seconds | `1.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__MAX_DELAY_SECONDS` | Max delay in seconds | `10.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__ADAPTIVE_BACKOFF` | Use adaptive backoff | `True` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_RETRY__JITTER_SECONDS` | Jitter | `1.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__RETRY_ENABLED` | Dedicated retry controls for timeout | `True` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__MAX_RETRIES` | Max retries | `2` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__BASE_DELAY_SECONDS` | Base delay in seconds | `2.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__MAX_DELAY_SECONDS` | Max delay in seconds | `10.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__ADAPTIVE_BACKOFF` | Use adaptive backoff | `True` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__JITTER_SECONDS` | Jitter | `1.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__EXECUTION_TIMEOUT_SECONDS` | Execution timeout limit | `300.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__UNIT_EXECUTION_TIMEOUT_SECONDS` | Unit execution timeout limit | `300.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__E2E_EXECUTION_TIMEOUT_SECONDS` | E2E execution timeout limit | `300.0` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__PROFILE` | Retry profile | `default` | No |
| `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__PLAIN_WRITE_PROCESS_ISOLATION` | Process isolation | `False` | No |
"""

if "Silver Resilience" not in docs_content:
    docs_content = docs_content.replace(
        "## Provider API Keys",
        retry_addition.strip() + "\n\n## Provider API Keys"
    )

with open("docs/04-reference/environment-variables.md", "w") as f:
    f.write(docs_content)
