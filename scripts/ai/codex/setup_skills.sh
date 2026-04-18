#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
SKILLS_SOURCE_DIR="$REPO_ROOT/.codex/skills"
AGENTS_SOURCE_DIR="$REPO_ROOT/.codex/agents"
SKILLS_TARGET_DIR="$CODEX_HOME/skills"
AGENTS_TARGET_DIR="$CODEX_HOME/subagents"
DRY_RUN=0
SYNC_PAIRED_AGENTS=1

usage() {
    cat <<'EOF'
Usage: setup_skills.sh [--dry-run] [--no-agents]

Sync repository Codex skills into the local Codex home. By default the script
also syncs paired agents when a matching `.codex/agents/<skill>.md` exists.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=1
            ;;
        --no-agents)
            SYNC_PAIRED_AGENTS=0
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

if [[ ! -d "$SKILLS_SOURCE_DIR" ]]; then
    echo "Skills source directory not found: $SKILLS_SOURCE_DIR" >&2
    exit 1
fi

mapfile -t skill_dirs < <(find "$SKILLS_SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
paired_agents=()
for path in "${skill_dirs[@]}"; do
    name="$(basename "$path")"
    agent_path="$AGENTS_SOURCE_DIR/$name.md"
    if [[ -f "$agent_path" ]]; then
        paired_agents+=("$name:$agent_path")
    fi
done

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Would sync: $SKILLS_SOURCE_DIR -> $SKILLS_TARGET_DIR"
    for path in "${skill_dirs[@]}"; do
        echo "  $(basename "$path")/"
    done
    if [[ "$SYNC_PAIRED_AGENTS" -eq 1 ]]; then
        echo "would also sync paired agents:"
        for entry in "${paired_agents[@]}"; do
            name="${entry%%:*}"
            agent_path="${entry#*:}"
            echo "  $name -> $AGENTS_TARGET_DIR/$(basename "$agent_path")"
        done
    fi
    exit 0
fi

mkdir -p "$SKILLS_TARGET_DIR"
for path in "${skill_dirs[@]}"; do
    name="$(basename "$path")"
    rm -rf "$SKILLS_TARGET_DIR/$name"
    cp -R "$path" "$SKILLS_TARGET_DIR/$name"
done

if [[ "$SYNC_PAIRED_AGENTS" -eq 1 ]]; then
    mkdir -p "$AGENTS_TARGET_DIR"
    for entry in "${paired_agents[@]}"; do
        agent_path="${entry#*:}"
        cp "$agent_path" "$AGENTS_TARGET_DIR/$(basename "$agent_path")"
    done
fi

echo "Synced ${#skill_dirs[@]} skills into $SKILLS_TARGET_DIR"
if [[ "$SYNC_PAIRED_AGENTS" -eq 1 ]]; then
    echo "Synced ${#paired_agents[@]} paired agents into $AGENTS_TARGET_DIR"
fi
