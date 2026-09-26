#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SETUP_MCP="$REPO_ROOT/scripts/ai/codex/setup_mcp.py"
SETUP_SKILLS="$SCRIPT_DIR/setup_skills.sh"
SKIP_MCP=0
SKIP_SKILLS=0
SKIP_CODEX_HOME_CONFIG=0
PROJECT_SKILLS_ONLY=0

usage() {
    cat <<'EOF'
Usage: setup_cursor.sh [--skip-mcp] [--skip-skills] [--project-skills-only]

Configure Cursor MCP and skills to mirror the canonical Codex runtime setup.
EOF
    return 0
}

for arg in "$@"; do
    case "$arg" in
        --skip-mcp)
            SKIP_MCP=1
            ;;
        --skip-skills)
            SKIP_SKILLS=1
            ;;
        --project-skills-only)
            PROJECT_SKILLS_ONLY=1
            ;;
        --skip-codex-home-config)
            SKIP_CODEX_HOME_CONFIG=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ "$SKIP_MCP" -eq 0 ]]; then
    mcp_args=(
        --root "$REPO_ROOT"
        --workspace-root "$REPO_ROOT"
        --skip-codex
        --skip-gemini-settings
    )
    if [[ "$SKIP_CODEX_HOME_CONFIG" -eq 1 ]]; then
        mcp_args+=(--skip-codex-config)
    fi
    python3 "$SETUP_MCP" "${mcp_args[@]}"
fi

if [[ "$SKIP_SKILLS" -eq 0 ]]; then
    skills_args=()
    if [[ "$PROJECT_SKILLS_ONLY" -eq 1 ]]; then
        skills_args+=(--project-only)
    fi
    bash "$SETUP_SKILLS" "${skills_args[@]}"
fi

echo "Cursor setup complete."
