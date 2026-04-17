#!/usr/bin/env bash
# check_skills_layout.sh - Enforce canonical docs skills layout.
# Canonical top-level directories in docs/00-project/ai/skills:
#   - local
#   - global
#   - _references
#   - collected (optional internal archive)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SKILLS_ROOT="$REPO_ROOT/docs/00-project/ai/skills"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[ai-skills-layout]${NC} $1"; }
log_ok() { echo -e "${GREEN}[ai-skills-layout]${NC} $1"; }
log_err() { echo -e "${RED}[ai-skills-layout]${NC} $1"; }

if [[ ! -d "$SKILLS_ROOT" ]]; then
    log_err "Skills root not found: $SKILLS_ROOT"
    exit 1
fi

log_info "Checking required directories"
for required in local global _references; do
    if [[ ! -d "$SKILLS_ROOT/$required" ]]; then
        log_err "Missing required directory: docs/00-project/ai/skills/$required"
        exit 1
    fi
done

log_info "Checking forbidden top-level skill folders"
mapfile -t bad_dirs < <(
    find "$SKILLS_ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' \
        | grep -Ev '^(_references|local|global|collected)$' || true
)
if (( ${#bad_dirs[@]} > 0 )); then
    log_err "Forbidden top-level directories detected:"
    for d in "${bad_dirs[@]}"; do
        echo "  - docs/00-project/ai/skills/$d"
    done
    exit 1
fi

log_info "Checking obsolete flat artifacts"
mapfile -t bad_files < <(
    find "$SKILLS_ROOT" -mindepth 1 -maxdepth 1 -type f \
        \( -name '*.openai.yaml' -o -name '*.skill.md' \) \
        -printf '%f\n'
)
if (( ${#bad_files[@]} > 0 )); then
    log_err "Obsolete files detected:"
    for f in "${bad_files[@]}"; do
        echo "  - docs/00-project/ai/skills/$f"
    done
    exit 1
fi

log_info "Checking active docs/scripts for forbidden legacy path docs/00-project/skills/"
if command -v rg >/dev/null 2>&1; then
    legacy_hits="$(
        rg -n --hidden \
            --glob '!docs/00-project/skills/**' \
            --glob '!docs/reports/**' \
            --glob '!docs/exports/**' \
            --glob '!docs/99-archive/**' \
            --glob '!scripts/check_ai_skills_layout.sh' \
            --glob '!scripts/ops/check_ai_skills_layout.sh' \
            --glob '!scripts/ai/codex/check_skills_layout.sh' \
            "docs/00-project/skills/" \
            "$REPO_ROOT/mkdocs.yml" \
            "$REPO_ROOT/.github" \
            "$REPO_ROOT/scripts" \
            "$REPO_ROOT/docs/00-project" \
            "$REPO_ROOT/docs/01-requirements" \
            "$REPO_ROOT/docs/02-architecture" \
            "$REPO_ROOT/docs/03-guides" \
            "$REPO_ROOT/docs/04-reference" \
            "$REPO_ROOT/docs/05-operations" || true
    )"
else
    legacy_hits="$(
        grep -Rsn "docs/00-project/skills/" \
            "$REPO_ROOT/mkdocs.yml" \
            "$REPO_ROOT/.github" \
            "$REPO_ROOT/scripts" \
            "$REPO_ROOT/docs/00-project" \
            "$REPO_ROOT/docs/01-requirements" \
            "$REPO_ROOT/docs/02-architecture" \
            "$REPO_ROOT/docs/03-guides" \
            "$REPO_ROOT/docs/04-reference" \
            "$REPO_ROOT/docs/05-operations" \
            --exclude-dir=skills \
            --exclude-dir=reports \
            --exclude-dir=exports \
            --exclude-dir=99-archive \
            --exclude=check_ai_skills_layout.sh \
            --exclude=check_skills_layout.sh || true
    )"
fi
if [[ -n "$legacy_hits" ]]; then
    log_err "Forbidden references to legacy docs/00-project/skills/ detected:"
    echo "$legacy_hits"
    exit 1
fi

log_ok "Canonical ai/skills layout is valid"
