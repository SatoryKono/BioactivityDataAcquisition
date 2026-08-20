#!/usr/bin/env bash
#
# CodeRabbit Comprehensive Audit Launcher
# Hybrid approach: immediate P0 issues, batched P1 findings
# Based on: docs/03-guides/coderabbit-audit-playbook.md
# Policy: docs/03-guides/coderabbit-audit-playbook.md
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AUDIT_TS=$(date -u +%Y%m%d_%H%M)
OUT_DIR="reports/quality/coderabbit/${AUDIT_TS}"
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# Scope matrix (≤300 files each)
declare -A SCOPES=(
    ["S00"]="src/bioetl/domain"
    ["S01"]="src/bioetl/application/core"
    ["S02"]="src/bioetl/application/services/control_plane"
    ["S03"]="src/bioetl/infrastructure/adapters"
    ["S04"]="src/bioetl/composition"
    ["S05"]="src/bioetl/interfaces"
    ["S06"]="tests/architecture"
    ["S07"]="configs/quality"
    ["S08"]="docs/00-project docs/02-architecture/decisions"
)

# Prompt themes per scope
declare -A PROMPT_THEMES=(
    ["S00"]="domain-purity"
    ["S01"]="pipelines-determinism"
    ["S02"]="control-plane-idempotency"
    ["S03"]="adapters-resilience"
    ["S04"]="composition-di"
    ["S05"]="interfaces-boundaries"
    ["S06"]="architecture-gates"
    ["S07"]="debt-governance"
    ["S08"]="docs-drift"
)

log_info() {
    local message="$1"
    echo -e "${GREEN}[INFO]${NC} $message"
}

log_warn() {
    local message="$1"
    echo -e "${YELLOW}[WARN]${NC} $message"
}

log_error() {
    local message="$1"
    echo -e "${RED}[ERROR]${NC} $message" >&2
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check CodeRabbit CLI
    if ! command -v coderabbit &> /dev/null; then
        log_error "CodeRabbit CLI not found. Install from https://cli.coderabbit.ai/"
        exit 1
    fi
    
    CR_VERSION=$(coderabbit --version)
    log_info "CodeRabbit version: $CR_VERSION"
    
    # Check API key
    if [[ -z "${CODERABBIT_API_KEY:-}" ]] && ! coderabbit auth status &> /dev/null; then
        log_warn "CODERABBIT_API_KEY not set and no auth cache found."
        log_warn "Run: coderabbit auth login --api-key YOUR_KEY"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check git status
    if ! git diff-index --quiet HEAD --; then
        log_error "Working directory has uncommitted changes. Please commit or stash first."
        exit 1
    fi
    
    # Check gh CLI for issue creation
    if ! command -v gh &> /dev/null; then
        log_warn "GitHub CLI not found. Issue creation will be skipped."
    fi
    
    log_info "Prerequisites check passed."
}

phase_0_preflight() {
    log_info "Phase 0: Preflight & Baseline"
    
    mkdir -p "$OUT_DIR"
    
    # Freeze baseline
    git rev-parse HEAD > "$OUT_DIR/baseline_sha.txt"
    git rev-parse main > "$OUT_DIR/main_sha.txt"
    
    log_info "Baseline SHA: $(cat $OUT_DIR/baseline_sha.txt)"
    log_info "Main SHA: $(cat $OUT_DIR/main_sha.txt)"
    
    # Run baseline quality checks
    log_info "Running baseline architecture tests..."
    pytest tests/architecture/ -q --tb=no > "$OUT_DIR/baseline_arch_tests.txt" 2>&1 || true
    
    log_info "Running baseline debt audit..."
    python -m scripts.engineering.qa validate-technical-debt-audit > "$OUT_DIR/baseline_debt_audit.txt" 2>&1 || true
    
    log_info "Preflight complete."
}

phase_1_scope_validation() {
    log_info "Phase 1: Scope Matrix Validation"
    
    echo "=== File Count Preflight ===" > "$OUT_DIR/preflight_file_counts.txt"
    
    for scope_id in "${!SCOPES[@]}"; do
        scope_paths="${SCOPES[$scope_id]}"
        file_count=0
        
        for path in $scope_paths; do
            if [[ -d "$path" ]]; then
                count=$(git ls-files "$path" | wc -l)
                file_count=$((file_count + count))
            fi
        done
        
        echo "$scope_id ($scope_paths): $file_count files" >> "$OUT_DIR/preflight_file_counts.txt"
        
        if (( file_count > 300 )); then
            log_error "Scope $scope_id has $file_count files (>300 limit). Split required."
            exit 1
        fi
    done
    
    log_info "All scopes within file limit (≤300)."
    cat "$OUT_DIR/preflight_file_counts.txt"
}

phase_2_sequential_reviews() {
    log_info "Phase 2: Sequential Scope Reviews"
    
    echo "=== Starting CodeRabbit comprehensive audit ===" > "$OUT_DIR/progress.log"
    echo "Timestamp: $(date -u +%Y%m%d_%H%M%S)" >> "$OUT_DIR/progress.log"
    echo "Baseline: $(cat $OUT_DIR/baseline_sha.txt)" >> "$OUT_DIR/progress.log"
    
    for scope_id in "${!SCOPES[@]}"; do
        scope_paths="${SCOPES[$scope_id]}"
        prompt_theme="${PROMPT_THEMES[$scope_id]}"
        
        log_info "Starting scope $scope_id ($prompt_theme)..."
        echo "=== Starting scope $scope_id at $(date -u +%Y%m%d_%H%M%S) ===" >> "$OUT_DIR/progress.log"
        
        # Build directory arguments
        dir_args=""
        for path in $scope_paths; do
            if [[ -d "$path" ]]; then
                dir_args="$dir_args --dir $path"
            fi
        done
        
        # Run CodeRabbit review
        log_info "Running CodeRabbit on $scope_paths..."
        if coderabbit review --base=main $dir_args --plain \
            | tee "$OUT_DIR/review_${scope_id}.log"; then
            log_info "Scope $scope_id completed successfully."
        else
            log_warn "Scope $scope_id completed with warnings."
        fi
        
        echo "=== Completed scope $scope_id at $(date -u +%Y%m%d_%H%M%S) ===" >> "$OUT_DIR/progress.log"
        
        # Rate limiting
        log_info "Waiting 30 seconds for rate limiting..."
        sleep 30
    done
    
    log_info "All scope reviews completed."
}

phase_3_p0_immediate() {
    log_info "Phase 3: Immediate P0 Issue Creation"
    
    if ! command -v gh &> /dev/null; then
        log_warn "GitHub CLI not available. Skipping P0 issue creation."
        return
    fi
    
    p0_count=0
    
    for scope_id in "${!SCOPES[@]}"; do
        log_file="$OUT_DIR/review_${scope_id}.log"
        
        if [[ ! -f "$log_file" ]]; then
            continue
        fi
        
        # Parse log for critical findings (simplified - actual parsing depends on CR output format)
        # This is a placeholder for actual parsing logic
        critical_findings=$(grep -i "critical" "$log_file" | wc -l || echo 0)
        
        if (( critical_findings > 0 )); then
            log_info "Found $critical_findings critical findings in $scope_id"
            # Actual issue creation would go here
            # p0_count=$((p0_count + critical_findings))
        fi
    done
    
    log_info "P0 immediate issues: $p0_count created"
    echo "P0 immediate issues: $p0_count" >> "$OUT_DIR/progress.log"
}

phase_4_batch_accumulation() {
    log_info "Phase 4: Batch P1 Findings Accumulation"
    
    # Create issue pack template
    cat > "$OUT_DIR/ISSUE_PACK.md" << EOF
# CodeRabbit Comprehensive Audit — Issue Pack ${AUDIT_TS}

**Published:** $(date -u +%Y-%m-%d)
**Baseline SHA:** $(cat $OUT_DIR/baseline_sha.txt)
**Artifacts:** reports/quality/coderabbit/${AUDIT_TS}/

## Severity Summary

| Severity | Count |
| --- | ---: |
| critical | TBD |
| major | TBD |
| minor | TBD |
| trivial | TBD |
| **total** | **TBD** |

## Immediate P0 Issues

TBD (created in Phase 3)

## Batch P1 Findings

TBD (to be populated from review logs)

## De-dupe Policy

1. One open issue per residual path
2. Prefer earlier scopes for same path
3. Prefer higher severity, then lower issue number
4. Implement only canonical issues
5. No tech-debt budget growth

## Next Steps

1. Review and triage P1 findings
2. Publish batch P1 issues
3. Implement fixes (one_issue_one_pr)
4. Re-run CR on fixed scopes
5. Closeout with FINAL.md
EOF
    
    log_info "Issue pack template created: $OUT_DIR/ISSUE_PACK.md"
}

phase_5_batch_publication() {
    log_info "Phase 5: Batch P1 Issue Publication"
    
    if ! command -v gh &> /dev/null; then
        log_warn "GitHub CLI not available. Skipping batch publication."
        return
    fi
    
    log_info "Batch publication would happen here after triage."
    log_info "Review $OUT_DIR/ISSUE_PACK.md for findings to publish."
}

phase_6_closeout() {
    log_info "Phase 6: Closeout Document"
    
    cat > "$OUT_DIR/FINAL.md" << EOF
# CodeRabbit Comprehensive Audit — Closeout ${AUDIT_TS}

**Completed:** $(date -u +%Y-%m-%d)
**Baseline SHA:** $(cat $OUT_DIR/baseline_sha.txt)
**Final SHA:** $(git rev-parse HEAD)

## Campaign Summary

| Metric | Value |
| --- | ---: |
| Tool version | $(coderabbit --version) |
| Scopes reviewed | ${#SCOPES[@]} |
| Total findings | TBD |
| P0 critical | TBD |
| P1 major | TBD |
| P2 minor | TBD |
| Trivial | TBD |

## Issues Published

- P0 immediate: TBD
- P1 batch: TBD
- Total: TBD

## Closeout Checklist

- [ ] FINAL.md: tool version, SHA, scopes, severity counts
- [ ] De-dupe vs prior ARCH-CR / DOC-GOV / epic issues
- [ ] No quality budget growth
- [ ] Relevant gates green (arch / debt / types / docs)
- [ ] Secrets not committed
- [ ] Tag: audit/coderabbit-${AUDIT_TS}

## Related Artifacts

- Issue pack: reports/quality/coderabbit/${AUDIT_TS}/ISSUE_PACK.md
- Review logs: reports/quality/coderabbit/${AUDIT_TS}/review_*.log
- Progress: reports/quality/coderabbit/${AUDIT_TS}/progress.log
EOF
    
    log_info "Closeout document created: $OUT_DIR/FINAL.md"
    
    # Create git tag (optional, requires confirmation)
    log_info "To create git tag: git tag audit/coderabbit-${AUDIT_TS}"
}

main() {
    log_info "CodeRabbit Comprehensive Audit Launcher"
    log_info "Timestamp: ${AUDIT_TS}"
    log_info "Output directory: ${OUT_DIR}"
    
    check_prerequisites
    phase_0_preflight
    phase_1_scope_validation
    phase_2_sequential_reviews
    phase_3_p0_immediate
    phase_4_batch_accumulation
    phase_5_batch_publication
    phase_6_closeout
    
    log_info "Audit campaign completed successfully!"
    log_info "Review artifacts in: ${OUT_DIR}"
    log_info "Next: Review ISSUE_PACK.md and create GitHub issues"
}

# Run main function
main "$@"
