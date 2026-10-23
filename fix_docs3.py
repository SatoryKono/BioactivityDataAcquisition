import re

with open("docs/04-reference/environment-variables.md") as f:
    content = f.read()

# I see what's happening. `BIOETL_PIPELINE__RUN_MANIFEST_ENABLED` is missing? No, `BIOETL_PIPELINE__CONTROL_PLANE__RUN_MANIFEST_ENABLED` is in docs, but the `get_env_vars.py` has a logic bug when analyzing `BIOETL_PIPELINE__CONTROL_PLANE__...`.
# Wait, are `run_manifest_enabled` and `run_ledger_enabled` on `ControlPlaneSettings` or `PipelineSettings` in code?
