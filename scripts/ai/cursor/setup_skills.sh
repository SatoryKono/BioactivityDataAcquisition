#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SKILLS_SOURCE_DIR="$REPO_ROOT/.codex/skills"
CURSOR_HOME="${CURSOR_HOME:-$HOME/.cursor}"
PROJECT_SKILLS_DIR="$REPO_ROOT/.cursor/skills"
USER_SKILLS_DIR="$CURSOR_HOME/skills"
SYNC_USER_SKILLS=1
DRY_RUN=0

usage() {
    cat <<'EOF'
Usage: setup_skills.sh [--dry-run] [--project-only]

Sync repository Codex skills into Cursor project and user skill homes.
Project skills are symlinked from .codex/skills to keep .codex as source of truth.
EOF
    return 0
}

for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=1
            ;;
        --project-only)
            SYNC_USER_SKILLS=0
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

link_skill() {
    local target_root="$1"
    local name="$2"
    local source_path="$SKILLS_SOURCE_DIR/$name"
    local link_path="$target_root/$name"

    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  $name -> $source_path (into $target_root)"
        return 0
    fi

    mkdir -p "$target_root"
    rm -rf "$link_path"
    ln -sfn "$source_path" "$link_path"
}

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Would sync project skills: $SKILLS_SOURCE_DIR -> $PROJECT_SKILLS_DIR"
    for path in "${skill_dirs[@]}"; do
        link_skill "$PROJECT_SKILLS_DIR" "$(basename "$path")"
    done
    if [[ "$SYNC_USER_SKILLS" -eq 1 ]]; then
        echo "Would sync user skills: $SKILLS_SOURCE_DIR -> $USER_SKILLS_DIR"
        for path in "${skill_dirs[@]}"; do
            link_skill "$USER_SKILLS_DIR" "$(basename "$path")"
        done
    fi
    exit 0
fi

mkdir -p "$PROJECT_SKILLS_DIR"
for path in "${skill_dirs[@]}"; do
    link_skill "$PROJECT_SKILLS_DIR" "$(basename "$path")"
done

if [[ "$SYNC_USER_SKILLS" -eq 1 ]]; then
    mkdir -p "$USER_SKILLS_DIR"
    for path in "${skill_dirs[@]}"; do
        link_skill "$USER_SKILLS_DIR" "$(basename "$path")"
    done
fi

echo "Synced ${#skill_dirs[@]} skills into $PROJECT_SKILLS_DIR"
if [[ "$SYNC_USER_SKILLS" -eq 1 ]]; then
    echo "Synced ${#skill_dirs[@]} skills into $USER_SKILLS_DIR"
fi
