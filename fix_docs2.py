import re

with open("docs/04-reference/environment-variables.md") as f:
    content = f.read()

# ADD OBSERVABILITY__METRICS_ENABLED
obs_addition = """
| `BIOETL_OBSERVABILITY__METRICS_ENABLED` | Enable Prometheus metrics | `True` | No |"""

if "BIOETL_OBSERVABILITY__METRICS_ENABLED" not in content:
    content = content.replace(
        "| `BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED` | Enable Prometheus metrics HTTP server (requires `metrics_enabled` to be active) | `True` | No |",
        obs_addition.strip() + "\n| `BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED` | Enable Prometheus metrics HTTP server (requires `metrics_enabled` to be active) | `True` | No |"
    )


with open("docs/04-reference/environment-variables.md", "w") as f:
    f.write(content)
