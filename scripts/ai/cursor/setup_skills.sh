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
Only links managed by this script are replaced or pruned. Existing files,
directories, and unrelated symlinks make the sync fail closed.
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

path_exists() {
    local path="$1"
    [[ -e "$path" || -L "$path" ]]
}

is_managed_skill_link() {
    local target_root="$1"
    local name="$2"
    local link_path="$target_root/$name"
    local expected_target actual_target
    [[ -L "$link_path" ]] || return 1
    expected_target="$(relative_skill_source "$target_root" "$name")"
    actual_target="$(readlink -- "$link_path")" || return 1
    [[ "$actual_target" == "$expected_target" ]]
}

report_collision() {
    local path="$1"
    local reason="$2"
    echo "Collision: $path ($reason); refusing to overwrite or delete it." >&2
    COLLISIONS=1
}

preflight_target_root() {
    local target_root="$1"
    if [[ -L "$target_root" ]]; then
        report_collision "$target_root" "skill root is a symlink"
        return 1
    fi
    if [[ -e "$target_root" && ! -d "$target_root" ]]; then
        report_collision "$target_root" "skill root is not a directory"
        return 1
    fi
    return 0
}

preflight_skill_links() {
    local target_root="$1"
    preflight_target_root "$target_root" || return 0
    local path name link_path
    for path in "${skill_dirs[@]}"; do
        name="$(basename "$path")"
        link_path="$target_root/$name"
        if path_exists "$link_path" && ! is_managed_skill_link "$target_root" "$name"; then
            report_collision "$link_path" "expected a managed skill symlink"
        fi
    done
}

preflight_stale_project_links() {
    local target_root="$1"
    [[ -d "$target_root" && ! -L "$target_root" ]] || return 0
    local entry name
    shopt -s nullglob
    for entry in "$target_root"/*; do
        name="$(basename "$entry")"
        if [[ ! -d "$SKILLS_SOURCE_DIR/$name" ]] && ! is_managed_skill_link "$target_root" "$name"; then
            report_collision "$entry" "stale entry is not a managed skill symlink"
        fi
    done
    shopt -u nullglob
}

prepare_target_root() {
    local target_root="$1"
    [[ -d "$target_root" ]] && return 0
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  create directory: $target_root"
        return 0
    fi
    mkdir -p "$target_root"
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
    if is_managed_skill_link "$target_root" "$name"; then
        if [[ "$DRY_RUN" -eq 1 ]]; then
            echo "  keep managed: $link_path -> $link_target"
        fi
        return 0
    fi
    if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "  create: $link_path -> $link_target"
        return 0
    fi
    ln -s "$link_target" "$link_path"
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
                echo "  prune managed stale: $entry"
            else
                rm -- "$entry"
                echo "Pruned stale skill link: $entry"
            fi
        fi
    done
    shopt -u nullglob
}

COLLISIONS=0
preflight_skill_links "$PROJECT_SKILLS_DIR"
preflight_stale_project_links "$PROJECT_SKILLS_DIR"
if [[ "$SYNC_USER_SKILLS" -eq 1 ]]; then
    preflight_skill_links "$USER_SKILLS_DIR"
fi
if [[ "$COLLISIONS" -ne 0 ]]; then
    echo "Skill sync aborted because unmanaged Cursor content would be affected." >&2
    exit 1
fi

prepare_target_root "$PROJECT_SKILLS_DIR"
prune_stale_project_links "$PROJECT_SKILLS_DIR"
for path in "${skill_dirs[@]}"; do
    link_skill "$PROJECT_SKILLS_DIR" "$(basename "$path")"
done

if [[ "$SYNC_USER_SKILLS" -eq 1 ]]; then
    prepare_target_root "$USER_SKILLS_DIR"
    for path in "${skill_dirs[@]}"; do
        link_skill "$USER_SKILLS_DIR" "$(basename "$path")"
    done
fi

echo "Synced ${#skill_dirs[@]} skills into $PROJECT_SKILLS_DIR"
if [[ "$SYNC_USER_SKILLS" -eq 1 ]]; then
    echo "Synced ${#skill_dirs[@]} skills into $USER_SKILLS_DIR"
fi
echo "Reload Cursor (Developer: Reload Window) to pick up project skills."
