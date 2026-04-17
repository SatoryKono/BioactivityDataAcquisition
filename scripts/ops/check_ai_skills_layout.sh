#!/usr/bin/env bash
# Compatibility facade for the canonical Codex skills layout check.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

exec bash "$REPO_ROOT/scripts/ai/codex/check_skills_layout.sh" "$@"
