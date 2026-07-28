#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${HOME}/.local/bin"
REPO="/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2"
cd "$REPO"
OUT_DIR="$REPO/reports/grok"
mkdir -p "$OUT_DIR"
STAMP=$(date +%Y%m%d_%H%M)
OUT_FILE="$OUT_DIR/review_coderabbit_architecture_${STAMP}.jsonl"
LOG_FILE="$OUT_DIR/review_coderabbit_architecture_${STAMP}.log"

# Base before ARCH-RES residual quality epic (captures ARCH-RES + ARCH-CONT + ARCH-REF waves)
BASE_COMMIT="f7ec4386fd~1"

echo "repo=$(pwd)" | tee "$LOG_FILE"
echo "base=$BASE_COMMIT" | tee -a "$LOG_FILE"
echo "head=$(git rev-parse HEAD)" | tee -a "$LOG_FILE"
echo "coderabbit=$(coderabbit --version)" | tee -a "$LOG_FILE"
coderabbit auth status 2>&1 | tee -a "$LOG_FILE" || true

# Agent-mode structured review of architecture program range
# Long-running; output both agent JSONL-style stream and plain summary.
set +e
coderabbit review --agent --base-commit "$BASE_COMMIT" 2>&1 | tee "$OUT_FILE"
RC=${PIPESTATUS[0]}
set -e
echo "exit_code=$RC" | tee -a "$LOG_FILE"
echo "out_file=$OUT_FILE" | tee -a "$LOG_FILE"
exit "$RC"
