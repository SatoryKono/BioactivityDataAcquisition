#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${HOME}/.local/bin"
REPO="/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"
cd "$REPO"
OUT_DIR="$REPO/reports/grok"
mkdir -p "$OUT_DIR"
STAMP=$(date +%Y%m%d_%H%M)
BASE_COMMIT="f7ec4386fd~1"
SUMMARY="$OUT_DIR/review_coderabbit_architecture_split_${STAMP}.md"
LOG="$OUT_DIR/review_coderabbit_architecture_split_${STAMP}.log"

{
  echo "# CodeRabbit split architecture audit"
  echo
  echo "- head: $(git rev-parse HEAD)"
  echo "- base-commit: $BASE_COMMIT"
  echo "- stamp: $STAMP"
  echo
} | tee "$SUMMARY" | tee "$LOG"

# Prior stored findings (if any)
echo "## Prior stored findings" | tee -a "$SUMMARY"
set +e
coderabbit review findings --dir "$REPO" 2>&1 | tee -a "$OUT_DIR/review_coderabbit_prior_findings_${STAMP}.txt" | tee -a "$LOG"
set -e
echo | tee -a "$SUMMARY"

# Architecture-critical scopes (mutually exclusive per run; sequential)
# Prefer source/config/tests/docs architecture surfaces.
SCOPES=(
  "src/bioetl/application"
  "src/bioetl/composition"
  "src/bioetl/domain"
  "src/bioetl/infrastructure"
  "src/bioetl/interfaces"
  "configs/quality"
  "tests/architecture"
  "docs/02-architecture"
  "docs/00-project"
  "docs/01-requirements"
)

for scope in "${SCOPES[@]}"; do
  if [ ! -e "$scope" ]; then
    echo "SKIP missing scope: $scope" | tee -a "$LOG"
    continue
  fi
  out="$OUT_DIR/review_coderabbit_arch_${scope//\//_}_${STAMP}.jsonl"
  echo "===== REVIEW scope=$scope =====" | tee -a "$LOG"
  echo "## Scope \`$scope\`" | tee -a "$SUMMARY"
  set +e
  coderabbit review --agent --base-commit "$BASE_COMMIT" --dir "$scope" 2>&1 | tee "$out"
  rc=${PIPESTATUS[0]}
  set -e
  echo "scope=$scope exit=$rc out=$out" | tee -a "$LOG"
  # Extract error/finding counts into summary
  if grep -q '"type":"error"' "$out" 2>/dev/null; then
    echo "- status: error" | tee -a "$SUMMARY"
    grep '"type":"error"' "$out" | head -3 | tee -a "$SUMMARY"
  else
    findings=$(grep -c '"type":"finding"' "$out" 2>/dev/null || echo 0)
    echo "- status: completed exit=$rc findings≈$findings" | tee -a "$SUMMARY"
  fi
  echo | tee -a "$SUMMARY"
done

echo "DONE summary=$SUMMARY" | tee -a "$LOG"
