#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SOURCE_DIR="$REPO_ROOT/.codex/agents"
TARGET_DIR="$CODEX_HOME/subagents"
DRY_RUN=0

usage() {
    cat <<'EOF'
Usage: setup_agents.sh [--dry-run]

Sync repository Codex agent markdown files into the local Codex home.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=1
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

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Agent source directory not found: $SOURCE_DIR" >&2
    exit 1
fi

mapfile -t agent_files < <(find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.md' | sort)

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Would sync: $SOURCE_DIR -> $TARGET_DIR"
    for path in "${agent_files[@]}"; do
        echo "  $(basename "$path")"
    done
    echo "Target folder: subagents"
    exit 0
fi

mkdir -p "$TARGET_DIR"
for path in "${agent_files[@]}"; do
    cp "$path" "$TARGET_DIR/$(basename "$path")"
done

echo "Synced ${#agent_files[@]} agent files into $TARGET_DIR"
