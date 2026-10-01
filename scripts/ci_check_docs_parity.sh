#!/bin/bash

# Compatibility wrapper — RETIRED / NON-CI (DOCS-PIPE-010, #11858).
# Not called from any workflow; the active CI gate is
# `python -m scripts.data_quality check-entity-config-parity` in docs.yml.
# Kept only so old local invocations still reach the canonical entry point.

set -e

echo "🔍 Running documentation parity check..."

# Run the canonical package entry point.
python3 -m scripts.data_quality check-entity-config-parity

# Capture exit code
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✅ Documentation parity check passed"
    exit 0
else
    echo "❌ Documentation parity check failed"
    exit 1
fi
