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
Project skills are relative symlinks from .cursor/skills to .codex/skills.
Stale links (e.g. historical public) are pruned.
EOF
    return 0
}

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --project-only) SYNC_USER_SKILLS=0 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ ! -d "$SKILLS_SOURCE_DIR" ]]; then
    echo "Skills source directory not found: $SKILLS_SOURCE_DIR" >&2
    exit 1
fi

mapfile -t skill_dirs < <(find "$SKILLS_SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

relative_skill_source() {
    local target_root="$1"
    local name="$2"
    if [[ "$target_root" == "$PROJECT_SKILLS_DIR" ]]; then
        printf '%s\n' "../../.codex/skills/$name"
        return 0
    fi
    printf '%s\n' "$SKILLS_SOURCE_DIR/$name"
}

link_skill() {
    local target_root="$1"
    local name="$2"
    local source_path="$SKILLS_SOURCE_DIR/$name"
    local link_path="$target_root/$name"
    local link_target
    if [[ ! -d "$source_path" ]]; then
        echo "Skip missing skill source: $source_path" >&2
        return 0
    fi
    link_target="$(relative_skill_source "$target_root" "$name")"
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  $name -> $link_target (into $target_root)"
        return 0
    fi
    mkdir -p "$target_root"
    rm -rf "$link_path"
    ln -sfn "$link_target" "$link_path"
}

prune_stale_project_links() {
    local target_root="$1"
    [[ -d "$target_root" ]] || return 0
    local entry name
    shopt -s nullglob
    for entry in "$target_root"/*; do
        name="$(basename "$entry")"
        if [[ ! -d "$SKILLS_SOURCE_DIR/$name" ]]; then
            if [[ "$DRY_RUN" -eq 1 ]]; then
                echo "  prune stale: $entry"
            else
                rm -rf "$entry" || true
                [[ -e "$entry" || -L "$entry" ]] && rm -f "$entry" || true
                echo "Pruned stale skill link: $entry"
            fi
        fi
    done
    shopt -u nullglob
}

mkdir -p "$PROJECT_SKILLS_DIR"
prune_stale_project_links "$PROJECT_SKILLS_DIR"
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
echo "Reload Cursor (Developer: Reload Window) to pick up project skills."
