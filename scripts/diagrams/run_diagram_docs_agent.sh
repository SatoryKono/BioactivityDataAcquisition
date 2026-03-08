#!/usr/bin/env bash
# Compatibility wrapper for agent-canonical diagram docs orchestrator.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec bash "$REPO_ROOT/docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-4.sh" "$@"
