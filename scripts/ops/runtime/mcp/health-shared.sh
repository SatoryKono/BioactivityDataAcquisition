#!/usr/bin/env bash
# Profile-aware bounded health probe for the shared MCP plane.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
PROFILE="${CODEX_MCP_PROFILE:-stable}"
ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        daily)
            PROFILE="stable"
            shift
            ;;
        all)
            PROFILE="full"
            shift
            ;;
        --profile)
            PROFILE="${2:-}"
            shift 2
            ;;
        --no-write|--json)
            ARGS+=("$1")
            shift
            ;;
        --timeout|--overall-timeout)
            ARGS+=("$1" "${2:-}")
            shift 2
            ;;
        *)
            echo "Unsupported argument: $1" >&2
            exit 2
            ;;
    esac
done

exec python3 "$ROOT/scripts/ai/codex/doctor.py" mcp --profile "$PROFILE" "${ARGS[@]}"
