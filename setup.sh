#!/usr/bin/env bash
# ==============================================================================
# setup.sh — BioETL development environment setup (convenience entry point)
#
# Delegates to scripts/dev/dev_setup.sh with all arguments forwarded.
#
# Usage:
#   ./setup.sh              # Full setup (prerequisites + deps + checks)
#   ./setup.sh --quick      # Quick install (deps only, no tests/linters)
#   ./setup.sh --ci         # CI mode (no color, no interactive prompts)
#   ./setup.sh --force      # Recreate virtual environment from scratch
#   ./setup.sh --help       # Show all available options
#
# BioETL v6.0.0
# ==============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$REPO_ROOT/scripts/dev/dev_setup.sh" "$@"
