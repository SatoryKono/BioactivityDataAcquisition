#!/usr/bin/env bash
# setup_skills.sh - Sync repository Codex skills into CODEX_HOME.
# Usage:
#   bash scripts/setup_skills.sh
#   bash scripts/setup_skills.sh --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SOURCE_ROOT="$REPO_ROOT/.codex/skills"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DEST_ROOT="$CODEX_HOME/skills"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
elif [[ -n "${1:-}" ]]; then
    echo "[setup-skills][error] Unknown argument: $1"
    echo "[setup-skills][hint] Supported arguments: --dry-run"
    exit 2
fi

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[setup-skills]${NC} $1"; }
log_ok() { echo -e "${GREEN}[setup-skills]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[setup-skills]${NC} $1"; }

if [[ ! -d "$SOURCE_ROOT" ]]; then
    log_warn "Source skills directory not found: $SOURCE_ROOT"
    exit 1
fi

mapfile -t SKILL_FILES < <(find "$SOURCE_ROOT" -type f -name "SKILL.md" | sort)
if [[ "${#SKILL_FILES[@]}" -eq 0 ]]; then
    log_warn "No skills found in $SOURCE_ROOT"
    exit 1
fi

log_info "Source root: $SOURCE_ROOT"
log_info "Destination root: $DEST_ROOT"
if [[ "$DRY_RUN" == true ]]; then
    log_info "Dry-run mode enabled"
else
    mkdir -p "$DEST_ROOT"
fi

for skill_file in "${SKILL_FILES[@]}"; do
    skill_dir="$(dirname "$skill_file")"
    rel_path="${skill_dir#"$SOURCE_ROOT"/}"
    dest_dir="$DEST_ROOT/$rel_path"

    if [[ "$DRY_RUN" == true ]]; then
        echo "Would sync: $skill_dir -> $dest_dir"
        continue
    fi

    rm -rf "$dest_dir"
    mkdir -p "$(dirname "$dest_dir")"
    cp -R "$skill_dir" "$dest_dir"
    log_ok "Synced: $rel_path"
done

if [[ "$DRY_RUN" == false ]]; then
    log_info "Installed skills:"
    find "$DEST_ROOT" -type f -name "SKILL.md" | sed "s|$DEST_ROOT/|  - |"
    log_ok "Skills setup completed. Restart Codex to pick up new skills."
fi
