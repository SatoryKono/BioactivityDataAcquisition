#!/usr/bin/env bash
# setup_agents.sh - Sync repository Codex agents into CODEX_HOME.
# Usage:
#   bash scripts/ai/codex/setup_agents.sh
#   bash scripts/ai/codex/setup_agents.sh --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

SOURCE_ROOT="$REPO_ROOT/.codex/agents"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DEST_ROOT="$CODEX_HOME/agents"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
elif [[ -n "${1:-}" ]]; then
    echo "[setup-agents][error] Unknown argument: $1"
    echo "[setup-agents][hint] Supported arguments: --dry-run"
    exit 2
fi

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[setup-agents]${NC} ${message}"
    return 0
}

log_ok() {
    local message="${1:-}"
    echo -e "${GREEN}[setup-agents]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}[setup-agents]${NC} ${message}"
    return 0
}

if [[ ! -d "$SOURCE_ROOT" ]]; then
    log_warn "Source agents directory not found: $SOURCE_ROOT"
    exit 1
fi

mapfile -t AGENT_ENTRIES < <(find "$SOURCE_ROOT" -mindepth 1 -maxdepth 1 | sort)
if [[ "${#AGENT_ENTRIES[@]}" -eq 0 ]]; then
    log_warn "No agents found in $SOURCE_ROOT"
    exit 1
fi

log_info "Source root: $SOURCE_ROOT"
log_info "Destination root: $DEST_ROOT"
if [[ "$DRY_RUN" == true ]]; then
    log_info "Dry-run mode enabled"
else
    mkdir -p "$DEST_ROOT"
fi

for entry in "${AGENT_ENTRIES[@]}"; do
    rel_name="$(basename "$entry")"
    dest_path="$DEST_ROOT/$rel_name"

    if [[ "$DRY_RUN" == true ]]; then
        echo "Would sync: $entry -> $dest_path"
        continue
    fi

    rm -rf "$dest_path"
    cp -R "$entry" "$dest_path"
    log_ok "Synced: $rel_name"
done

if [[ "$DRY_RUN" == false ]]; then
    log_info "Installed agent entries:"
    find "$DEST_ROOT" -mindepth 1 -maxdepth 1 | sed "s|$DEST_ROOT/|  - |"
    log_ok "Agents setup completed. Restart Codex to pick up updated agent surfaces."
fi
