#!/usr/bin/env bash
# setup_skills.sh - Sync repository Codex skills into CODEX_HOME.
# By default this also syncs the paired `.codex/agents` tree because many
# skills resolve relative agent references through CODEX_HOME.
# Usage:
#   bash scripts/ai/codex/setup_skills.sh
#   bash scripts/ai/codex/setup_skills.sh --dry-run
#   bash scripts/ai/codex/setup_skills.sh --skills-only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

SOURCE_ROOT="$REPO_ROOT/.codex/skills"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DEST_ROOT="$CODEX_HOME/skills"
DRY_RUN=false
SYNC_AGENTS=true

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
elif [[ "${1:-}" == "--skills-only" ]]; then
    SYNC_AGENTS=false
elif [[ -n "${1:-}" ]]; then
    echo "[setup-skills][error] Unknown argument: $1"
    echo "[setup-skills][hint] Supported arguments: --dry-run, --skills-only"
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

if [[ "$SYNC_AGENTS" == true ]]; then
    AGENT_SETUP_SCRIPT="$SCRIPT_DIR/setup_agents.sh"
    if [[ "$DRY_RUN" == true ]]; then
        log_info "Dry-run: would also sync paired agents via $AGENT_SETUP_SCRIPT"
        bash "$AGENT_SETUP_SCRIPT" --dry-run
    else
        log_info "Syncing paired agent surfaces"
        bash "$AGENT_SETUP_SCRIPT"
    fi
fi

if [[ "$DRY_RUN" == false ]]; then
    log_info "Installed skills:"
    find "$DEST_ROOT" -type f -name "SKILL.md" | sed "s|$DEST_ROOT/|  - |"
    if [[ "$SYNC_AGENTS" == true ]]; then
        log_ok "Skills and paired agents setup completed. Restart Codex to pick up new runtime surfaces."
    else
        log_ok "Skills setup completed. Restart Codex to pick up new skills."
    fi
fi
