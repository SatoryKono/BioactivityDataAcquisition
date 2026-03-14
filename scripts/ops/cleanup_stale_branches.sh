#!/usr/bin/env bash
# ==============================================================================
# cleanup_stale_branches.sh — Delete stale remote branches after consolidation
#
# Generated: 2026-03-14
# Context: Branch consolidation analysis (claude/review-branch-consolidation)
#
# Usage:
#   ./scripts/ops/cleanup_stale_branches.sh          # Dry-run (default)
#   ./scripts/ops/cleanup_stale_branches.sh --execute # Actually delete
# ==============================================================================

set -euo pipefail

DRY_RUN=true
if [[ "${1:-}" == "--execute" ]]; then
    DRY_RUN=false
fi

# ─── GROUP 1: Already merged into main ────────────────────────────────────────
MERGED_BRANCHES=(
    "feat/mmd-diagrams-improvements"
    "master-20260310"
    "master_20250310-1"
)

# ─── GROUP 2: Duplicates (keep best, delete rest) ─────────────────────────────
DUPLICATE_BRANCHES=(
    # ClockPort duplicates (keep: implement-clockport-with-systemclock-and-fixedclock)
    "codex/add-clockport-and-implement-systemclock"
    "codex/add-clockport-and-integrate-with-services"
    # Review reports duplicates (keep: feat/generate-review-reports-1938004674597881868)
    "generate-review-reports-1947833378410250100"
    "jules/py-review-orchestrator-reports-12179720024460888652"
    # SilverDQAnalyzer duplicate (keep: -bpi4lc variant)
    "codex/refactor-silverdqanalyzer-into-components"
    # Consolidate scripts duplicate (keep: -IyUir)
    "claude/consolidate-project-scripts-NzcGh"
)

# ─── GROUP 3: Junk / empty branches ──────────────────────────────────────────
JUNK_BRANCHES=(
    "codex/main_20250309-01"          # Single commit "1", no content
)

# ─── GROUP 4: Stale — cherry-picked or obsolete (files deleted/diverged) ──────
STALE_BRANCHES=(
    # Perf branches (values cherry-picked or obsolete)
    "bolt-opt-flatten-arrow-1596384014476340969"      # Cherry-picked: walrus optimization
    "perf-arrow-as-py-13400775707547248079"            # Cherry-picked: lint fix
    "jules-bolt-perf-extractors-4618911369928474874"   # Already in main: batch_size fix
    "perf/optimize-as-py-walrus-2758896252945543510"   # Only mkdocs.yml nav entry, stale
    "bolt/optimize-as-py-1821097349407395074"          # Deletes scripts, stale
    "jules-5062629851525629488-e88eaea2"               # TextNormalization opt, 1700+ file diff, stale

    # DI/Refactoring branches (all based on ancient commit, services_factory.py deleted)
    "codex/refactor-batch-executor-dependencies"
    "codex/refactor-dependency-injection-in-core-modules"
    "codex/refactor-to-use-constructor-injection"
    "codex/refactor-getattr-calls-in-bioetl"           # Target files deleted in main
    "codex/refactor-mixin-files-for-type-safety"       # 22 conflicts, completely stale

    # Other stale codex branches
    "codex/categorize-and-tidy-up-type-ignores"        # 8 conflicts, stale
    "codex/add-fsmstatehelperservice-to-compositepipelinerunnerservice"  # 12 conflicts, mixin files deleted
    "codex/filter-architecture-metric-exemptions"      # Docs-only, stale base

    # Setup script (cherry-picked the valuable fix)
    "claude/configure-setup-script-ei3rR"

    # Audit branch (conflicts on deleted mixin files)
    "claude/audit-refactor-review-AOMLk"
)

# ─── GROUP 5: KEEP (do not delete) ───────────────────────────────────────────
# claude/add-interactive-debugger          — explicitly excluded by user
# feat/generate-review-reports-*           — kept as best duplicate
# codex/implement-clockport-*              — kept as best duplicate
# codex/refactor-silverdqanalyzer-*-bpi4lc — kept as best duplicate
# claude/consolidate-project-scripts-IyUir — kept as best duplicate
# main_20250312                            — backup, needs manual review
# perf-async-metrics-server-*              — valuable idea, needs re-impl
# dependabot/*                             — automated, managed by dependabot

# ─── GROUP 6: NEEDS MANUAL REVIEW ────────────────────────────────────────────
# perf-async-metrics-server-1814537927827611323 — valuable async refactor, 5 conflicts
#   → Re-implement sync→async metrics server from scratch
# feat/generate-review-reports-1938004674597881868 — review report generator
#   → Evaluate if AST-based review generator is still needed

echo "============================================================"
echo "  Branch Cleanup Script"
echo "============================================================"
echo ""

delete_branch() {
    local branch="$1"
    local reason="$2"
    if $DRY_RUN; then
        echo "[DRY-RUN] Would delete: $branch ($reason)"
    else
        echo "Deleting: $branch ($reason)"
        git push origin --delete "$branch" 2>&1 || echo "  FAILED to delete $branch"
    fi
}

echo "── Merged branches ──"
for b in "${MERGED_BRANCHES[@]}"; do
    delete_branch "$b" "merged into main"
done

echo ""
echo "── Duplicate branches ──"
for b in "${DUPLICATE_BRANCHES[@]}"; do
    delete_branch "$b" "duplicate"
done

echo ""
echo "── Junk branches ──"
for b in "${JUNK_BRANCHES[@]}"; do
    delete_branch "$b" "junk/empty"
done

echo ""
echo "── Stale branches ──"
for b in "${STALE_BRANCHES[@]}"; do
    delete_branch "$b" "stale/cherry-picked"
done

echo ""
echo "============================================================"
TOTAL=$(( ${#MERGED_BRANCHES[@]} + ${#DUPLICATE_BRANCHES[@]} + ${#JUNK_BRANCHES[@]} + ${#STALE_BRANCHES[@]} ))
echo "  Total branches to delete: $TOTAL"
echo ""
echo "  Branches KEPT:"
echo "    - claude/add-interactive-debugger (user request)"
echo "    - codex/implement-clockport-with-systemclock-and-fixedclock (best ClockPort)"
echo "    - feat/generate-review-reports-1938004674597881868 (best review reports)"
echo "    - codex/refactor-silverdqanalyzer-into-components-bpi4lc (best DQ refactor)"
echo "    - claude/consolidate-project-scripts-IyUir (best scripts consolidation)"
echo "    - perf-async-metrics-server-1814537927827611323 (valuable, needs re-impl)"
echo "    - main_20250312 (backup, manual review)"
echo "    - dependabot/* branches (automated)"
echo "============================================================"

if $DRY_RUN; then
    echo ""
    echo "This was a DRY RUN. To actually delete branches, run:"
    echo "  $0 --execute"
fi
