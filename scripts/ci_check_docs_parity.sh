#!/bin/bash

# Compatibility wrapper
# CI/CD Documentation Parity Check Script
# This script runs the entity config parity check as part of CI/CD pipeline

set -e

echo "🔍 Running documentation parity check..."

# Run the parity check
python3 scripts/check_entity_config_parity.py

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Documentation parity check passed"
    exit 0
else
    echo "❌ Documentation parity check failed"
    exit 1
fi
