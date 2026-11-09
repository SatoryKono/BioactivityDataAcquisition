#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SKILLS_SOURCE_DIR="$REPO_ROOT/.codex/skills"
GROK_SKILLS_SOURCE_DIR="$REPO_ROOT/docs/00-project/ai/grok/skills"
CURSOR_HOME="${CURSOR_HOME:-$HOME/.cursor}"
PROJECT_SKILLS_DIR="$REPO_ROOT/.cursor/skills"
USER_SKILLS_DIR="$CURSOR_HOME/skills"
SYNC_USER_SKILLS=1
DRY_RUN=0

usage() {
    cat <<'EOF'
Usage: setup_skills.sh [--dry-run] [--project-only]

Sync repository skills into Cursor project and user skill homes.
Project links are relative:
  .cursor/skills/<name> -> ../../.codex/skills/<name>
  .cursor/skills/<name> -> ../../docs/00-project/ai/grok/skills/<name>
The Grok set is the operator skills under docs/00-project/ai/grok/skills.
Only links managed by this script are replaced or pruned. Existing files,
directories, and unrelated symlinks make the sync fail closed.
On Windows, if symlink creation is denied, the script creates a directory
junction to the same source.
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
grok_skill_dirs=()
if [[ -d "$GROK_SKILLS_SOURCE_DIR" ]]; then
    mapfile -t grok_skill_dirs < <(find "$GROK_SKILLS_SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
fi

for grok_path in ${grok_skill_dirs[@]+"${grok_skill_dirs[@]}"}; do
    grok_name="$(basename "$grok_path")"
    if [[ -d "$SKILLS_SOURCE_DIR/$grok_name" ]]; then
        echo "Skill name exists in both Codex and Grok sources: $grok_name" >&2
        exit 1
    fi
done

relative_skill_source() {
    local target_root="$1"
    local name="$2"
    local kind="${3:-codex}"
    if [[ "$target_root" == "$PROJECT_SKILLS_DIR" ]]; then
        if [[ "$kind" == "grok" ]]; then
            printf '%s\n' "../../docs/00-project/ai/grok/skills/$name"
        else
            printf '%s\n' "../../.codex/skills/$name"
        fi
        return 0
    fi
    if [[ "$kind" == "grok" ]]; then
        printf '%s\n' "$GROK_SKILLS_SOURCE_DIR/$name"
        return 0
    fi
    printf '%s\n' "$SKILLS_SOURCE_DIR/$name"
}

absolute_skill_source() {
    local name="$1"
    local kind="$2"
    if [[ "$kind" == "grok" ]]; then
        printf '%s\n' "$GROK_SKILLS_SOURCE_DIR/$name"
        return 0
    fi
    printf '%s\n' "$SKILLS_SOURCE_DIR/$name"
}

skill_source_present() {
    local name="$1"
    [[ -d "$SKILLS_SOURCE_DIR/$name" || -d "$GROK_SKILLS_SOURCE_DIR/$name" ]]
}

path_exists() {
    local path="$1"
    [[ -e "$path" || -L "$path" ]]
}

link_targets_match() {
    local actual="$1"
    local expected="$2"
    local actual_unix expected_unix
    [[ "$actual" == "$expected" ]] && return 0
    if ! command -v cygpath >/dev/null 2>&1; then
        return 1
    fi
    case "$actual" in
        /*|[A-Za-z]:*)
            ;;
        *)
            return 1
            ;;
    esac
    actual_unix="$(cygpath -u "$actual" 2>/dev/null || true)"
    expected_unix="$(cygpath -u "$expected" 2>/dev/null || true)"
    [[ -n "$actual_unix" && "$actual_unix" == "$expected_unix" ]]
}

read_skill_link_target() {
    local link_path="$1"
    if [[ -L "$link_path" ]]; then
        readlink -- "$link_path"
        return
    fi
    [[ -d "$link_path" ]] && command -v cygpath >/dev/null 2>&1 &&
        command -v powershell.exe >/dev/null 2>&1 || return 1
    BIOETL_CURSOR_LINK="$(cygpath -w "$link_path")" \
        powershell.exe -NoProfile -NonInteractive -Command \
        '$item = Get-Item -LiteralPath $env:BIOETL_CURSOR_LINK -Force -ErrorAction Stop; if ($item.LinkType -ne "Junction") { exit 1 }; [Console]::WriteLine([string]($item.Target | Select-Object -First 1))' |
        tr -d '\r'
}

is_managed_skill_link() {
    local target_root="$1"
    local name="$2"
    local expected_kind="${3:-}"
    local link_path="$target_root/$name"
    local actual_target kind expected_target absolute_target
    actual_target="$(read_skill_link_target "$link_path")" || return 1
    for kind in codex grok; do
        [[ -z "$expected_kind" || "$kind" == "$expected_kind" ]] || continue
        expected_target="$(relative_skill_source "$target_root" "$name" "$kind")"
        if [[ "$actual_target" == "$expected_target" ]]; then
            return 0
        fi
        absolute_target="$(absolute_skill_source "$name" "$kind")"
        if link_targets_match "$actual_target" "$absolute_target"; then
            return 0
        fi
    done
    return 1
}

remove_managed_skill_link() {
    local target_root="$1" name="$2"
    local link_path="$target_root/$name"
    is_managed_skill_link "$target_root" "$name" || return 1
    if [[ -L "$link_path" ]]; then
        rm -- "$link_path"
    else
        BIOETL_CURSOR_LINK="$(cygpath -w "$link_path")" \
            powershell.exe -NoProfile -NonInteractive -Command \
            '$ErrorActionPreference = "Stop"; $item = Get-Item -LiteralPath $env:BIOETL_CURSOR_LINK -Force; if ($item.LinkType -ne "Junction") { exit 1 }; [IO.Directory]::Delete($item.FullName)'
    fi
}

create_skill_link() {
    local link_path="$1"
    local link_target="$2"
    local source_path="$3"
    local win_link win_target
    if MSYS=winsymlinks:nativestrict ln -s "$link_target" "$link_path" 2>/dev/null; then
        return 0
    fi
    if ! command -v cygpath >/dev/null 2>&1 || ! command -v powershell.exe >/dev/null 2>&1; then
        echo "Failed to link $link_path -> $link_target" >&2
        return 1
    fi
    win_link="$(cygpath -w "$link_path")"
    win_target="$(cygpath -w "$source_path")"
    if BIOETL_CURSOR_LINK="$win_link" BIOETL_CURSOR_TARGET="$win_target" \
        powershell.exe -NoProfile -NonInteractive -Command \
        'New-Item -ItemType Junction -Path $env:BIOETL_CURSOR_LINK -Target $env:BIOETL_CURSOR_TARGET -ErrorAction Stop | Out-Null'; then
        echo "Junction (symlink privilege unavailable): $link_path" >&2
        return 0
    fi
    echo "Failed to link $link_path -> $link_target" >&2
    return 1
}

report_collision() {
    local path="$1"
    local reason="$2"
    echo "Collision: $path ($reason); refusing to overwrite or delete it." >&2
    COLLISIONS=1
}

preflight_target_root() {
    local target_root="$1"
    if read_skill_link_target "$target_root" >/dev/null; then
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
    for path in "${skill_dirs[@]}" ${grok_skill_dirs[@]+"${grok_skill_dirs[@]}"}; do
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
        if ! skill_source_present "$name" && ! is_managed_skill_link "$target_root" "$name"; then
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
    local kind="${3:-codex}"
    local source_root="$SKILLS_SOURCE_DIR"
    local source_path link_path link_target
    if [[ "$kind" == "grok" ]]; then
        source_root="$GROK_SKILLS_SOURCE_DIR"
    fi
    source_path="$source_root/$name"
    link_path="$target_root/$name"
    if [[ ! -d "$source_path" ]]; then
        echo "Skip missing skill source: $source_path" >&2
        return 0
    fi
    link_target="$(relative_skill_source "$target_root" "$name" "$kind")"
    if is_managed_skill_link "$target_root" "$name" "$kind"; then
        if [[ "$DRY_RUN" -eq 1 ]]; then
            echo "  keep managed: $link_path -> $link_target"
        fi
        return 0
    fi
    if [[ "$DRY_RUN" -eq 1 ]]; then
        if is_managed_skill_link "$target_root" "$name"; then
            echo "  retarget managed: $link_path -> $link_target"
        else
            echo "  create: $link_path -> $link_target"
        fi
        return 0
    fi
    if path_exists "$link_path" && ! remove_managed_skill_link "$target_root" "$name"; then
        report_collision "$link_path" "expected a removable managed skill link"
        return 1
    fi
    create_skill_link "$link_path" "$link_target" "$source_path"
}

prune_stale_project_links() {
    local target_root="$1"
    [[ -d "$target_root" ]] || return 0
    local entry name
    shopt -s nullglob
    for entry in "$target_root"/*; do
        name="$(basename "$entry")"
        if ! skill_source_present "$name"; then
            if [[ "$DRY_RUN" -eq 1 ]]; then
                echo "  prune managed stale: $entry"
            else
                remove_managed_skill_link "$target_root" "$name" || return 1
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
    link_skill "$PROJECT_SKILLS_DIR" "$(basename "$path")" codex
done
for path in ${grok_skill_dirs[@]+"${grok_skill_dirs[@]}"}; do
    link_skill "$PROJECT_SKILLS_DIR" "$(basename "$path")" grok
done

if [[ "$SYNC_USER_SKILLS" -eq 1 ]]; then
    prepare_target_root "$USER_SKILLS_DIR"
    for path in "${skill_dirs[@]}"; do
        link_skill "$USER_SKILLS_DIR" "$(basename "$path")" codex
    done
    for path in ${grok_skill_dirs[@]+"${grok_skill_dirs[@]}"}; do
        link_skill "$USER_SKILLS_DIR" "$(basename "$path")" grok
    done
fi

synced_count=$((${#skill_dirs[@]} + ${#grok_skill_dirs[@]}))
echo "Synced ${synced_count} skills into $PROJECT_SKILLS_DIR"
if [[ "$SYNC_USER_SKILLS" -eq 1 ]]; then
    echo "Synced ${synced_count} skills into $USER_SKILLS_DIR"
fi
echo "Reload Cursor (Developer: Reload Window) to pick up project skills."
