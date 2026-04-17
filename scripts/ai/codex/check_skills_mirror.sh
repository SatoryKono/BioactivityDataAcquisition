#!/usr/bin/env bash
# check_skills_mirror.sh - Verify/sync docs/00-project/ai/skills/local mirror from .codex/skills.
# Also overlays reference bundles from docs/00-project/ai/skills/_references/local.
# Usage:
#   bash scripts/ai/codex/check_skills_mirror.sh --check
#   bash scripts/ai/codex/check_skills_mirror.sh --sync

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

SOURCE_ROOT="$REPO_ROOT/.codex/skills"
MIRROR_ROOT="$REPO_ROOT/docs/00-project/ai/skills/local"
REFERENCE_SOURCE_ROOT="$REPO_ROOT/docs/00-project/ai/skills/_references/local"
MODE="${1:---check}"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[skills-mirror]${NC} ${message}"
    return 0
}

log_ok() {
    local message="${1:-}"
    echo -e "${GREEN}[skills-mirror]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}[skills-mirror]${NC} ${message}"
    return 0
}

log_err() {
    local message="${1:-}"
    echo -e "${RED}[skills-mirror]${NC} ${message}" >&2
    return 0
}

usage() {
    cat <<'EOF'
Usage:
  bash scripts/ai/codex/check_skills_mirror.sh --check
  bash scripts/ai/codex/check_skills_mirror.sh --sync

Modes:
  --check   Fail if docs/00-project/ai/skills/local differs from .codex/skills.
  --sync    Replace docs/00-project/ai/skills/local with .codex/skills and then verify.
EOF
}

case "$MODE" in
    --check|--sync) ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        log_err "Unknown argument: $MODE"
        usage
        exit 2
        ;;
esac

if [[ ! -d "$SOURCE_ROOT" ]]; then
    log_err "Source directory not found: $SOURCE_ROOT"
    exit 1
fi
if [[ ! -d "$MIRROR_ROOT" ]]; then
    log_err "Mirror directory not found: $MIRROR_ROOT"
    exit 1
fi
if [[ ! -d "$REFERENCE_SOURCE_ROOT" ]]; then
    log_err "Reference source directory not found: $REFERENCE_SOURCE_ROOT"
    exit 1
fi

if [[ "$MODE" == "--sync" ]]; then
    log_info "Syncing docs/00-project/ai/skills/local from .codex/skills"
    find "$MIRROR_ROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    cp -a "$SOURCE_ROOT"/. "$MIRROR_ROOT"/
    log_info "Overlaying documentation reference bundles (references/**)"
    while IFS= read -r ref_dir; do
        rel_path="${ref_dir#"$REFERENCE_SOURCE_ROOT"/}"
        target_dir="$MIRROR_ROOT/$rel_path"
        mkdir -p "$(dirname "$target_dir")"
        rm -rf "$target_dir"
        cp -a "$ref_dir" "$target_dir"
    done < <(find "$REFERENCE_SOURCE_ROOT" -type d -name references | sort)
    log_ok "Sync completed"
fi

log_info "Checking mirror consistency"
if ! diff -qr -x references "$SOURCE_ROOT" "$MIRROR_ROOT" > /tmp/skills_mirror_diff.txt; then
    log_err "Mirror drift detected between .codex/skills and docs/00-project/ai/skills/local"
    sed -n '1,200p' /tmp/skills_mirror_diff.txt
    log_warn "Run: bash scripts/ai/codex/check_skills_mirror.sh --sync"
    exit 1
fi

log_info "Validating SKILL.md frontmatter contracts"
while IFS= read -r skill_file; do
    relative_path="${skill_file#"$SOURCE_ROOT"/}"

    needs_frontmatter=false
    case "$relative_path" in
        agent-orchestration/SKILL.md|documentation-audit/SKILL.md|documentation-cascade-audit/SKILL.md|new-pipeline/SKILL.md|public/architecture-guardian/SKILL.md|py-audit-bot/SKILL.md|py-architecture-debt-bot/SKILL.md|py-code-bot/SKILL.md|py-config-bot/SKILL.md|py-debug-bot/SKILL.md|py-doc-bot/SKILL.md|py-plan-bot/SKILL.md|py-review-orchestrator/SKILL.md|py-test-bot/SKILL.md|py-test-swarm/SKILL.md|technical-designer-mermaid/SKILL.md|vcr-record/SKILL.md|verify-architecture/SKILL.md)
            needs_frontmatter=true
            ;;
        *)
            ;;
    esac

    has_valid_frontmatter=true
    if ! awk '
        BEGIN { header = 0; has_name = 0; has_description = 0; done = 0 }
        {
            line = $0
            sub(/\r$/, "", line)
        }
        NR == 1 && line == "---" { header = 1; next }
        header == 1 && line == "---" { done = 1; exit }
        header == 1 && line ~ /^name:[[:space:]]*[^[:space:]].*/ { has_name = 1 }
        header == 1 && line ~ /^description:[[:space:]]*[^[:space:]].*/ { has_description = 1 }
        END {
            if (header == 1 && done == 1 && has_name == 1 && has_description == 1) {
                exit 0
            }
            exit 1
        }
    ' "$skill_file"; then
        has_valid_frontmatter=false
    fi

    if [[ "$needs_frontmatter" == true && "$has_valid_frontmatter" == false ]]; then
        log_err "Invalid frontmatter contract (required): $skill_file"
        log_warn "Expected YAML frontmatter with non-empty name and description."
        exit 1
    fi

    if [[ "$needs_frontmatter" == false && "$has_valid_frontmatter" == false ]]; then
        log_warn "No strict frontmatter contract for optional skill: $relative_path"
    fi
done < <(find "$SOURCE_ROOT" -type f -name 'SKILL.md' | sort)

SOURCE_COUNT="$(find "$SOURCE_ROOT" -type f -name 'SKILL.md' | wc -l | tr -d ' ')"
MIRROR_COUNT="$(find "$MIRROR_ROOT" -type f -name 'SKILL.md' | wc -l | tr -d ' ')"
log_ok "Mirror is in sync (SKILL.md count: source=$SOURCE_COUNT, mirror=$MIRROR_COUNT)"
