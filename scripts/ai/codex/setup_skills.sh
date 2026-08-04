#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PERSONAL_CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
SKILLS_SOURCE_DIR="$REPO_ROOT/.codex/skills"
SKILLS_TARGET_DIR="$PERSONAL_CODEX_ROOT/skills"
INSTALL_PERSONAL=0
SYNC_NATIVE=0
DRY_RUN=0

usage() {
    cat <<'EOF'
Usage: setup_skills.sh [--check] [--sync-native] [--install-personal] [--dry-run]

Check the generated `.agents/skills/*/SKILL.md` discovery adapters. Codex
discovers these repository skills directly; no user-home bootstrap is required.

`--sync-native` refreshes the tracked adapters from canonical `.codex/skills`.
`--install-personal` explicitly copies canonical skills to the current user's
Codex home. `--dry-run` previews only that optional personal copy.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --check)
            ;;
        --sync-native)
            SYNC_NATIVE=1
            ;;
        --install-personal)
            INSTALL_PERSONAL=1
            ;;
        --dry-run)
            INSTALL_PERSONAL=1
            DRY_RUN=1
            ;;
        --no-agents)
            echo "[WARN] --no-agents is obsolete; skills no longer bootstrap paired agents" >&2
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

if [[ "$SYNC_NATIVE" -eq 1 ]]; then
    python3 "$SCRIPT_DIR/sync_native_skills.py" --sync
else
    python3 "$SCRIPT_DIR/sync_native_skills.py" --check
fi

if [[ "$INSTALL_PERSONAL" -eq 0 ]]; then
    exit 0
fi

mapfile -t skill_dirs < <(find "$SKILLS_SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Would copy optional personal skills: $SKILLS_SOURCE_DIR -> $SKILLS_TARGET_DIR"
    for path in "${skill_dirs[@]}"; do
        echo "  $(basename "$path")/"
    done
    exit 0
fi

mkdir -p "$SKILLS_TARGET_DIR"
for path in "${skill_dirs[@]}"; do
    name="$(basename "$path")"
    destination="$SKILLS_TARGET_DIR/$name"
    if [[ -e "$destination" ]]; then
        echo "[WARN] Existing personal skill left unchanged: $destination" >&2
        continue
    fi
    cp -R "$path" "$destination"
done
echo "Copied ${#skill_dirs[@]} optional personal skills into $SKILLS_TARGET_DIR"
