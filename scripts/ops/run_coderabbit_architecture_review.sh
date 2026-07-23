#!/usr/bin/env bash
# Exhaustive hexagonal architecture review via CodeRabbit (layered to stay under 300-file limit).
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BASE_REF="${1:-HEAD~300}"
BASE="$(git rev-parse "$BASE_REF")"
HEAD="$(git rev-parse HEAD)"
OUT_DIR="reports/quality/coderabbit"
mkdir -p "$OUT_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
SUMMARY="$OUT_DIR/architecture-layered_${TS}.md"
AGENT_ALL="$OUT_DIR/architecture-layered_${TS}.agent.ndjson"
: >"$AGENT_ALL"

{
  echo "# CodeRabbit Exhaustive Architecture Review"
  echo
  echo "- HEAD: \`$HEAD\`"
  echo "- BASE: \`$BASE\` (\`$BASE_REF\`)"
  echo "- Mode: layered hexagonal packages (CodeRabbit max 300 files per review)"
  echo "- Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
} >"$SUMMARY"

DIRS=(
  "src/bioetl/domain"
  "src/bioetl/application"
  "src/bioetl/composition"
  "src/bioetl/infrastructure"
  "src/bioetl/interfaces"
)

for d in "${DIRS[@]}"; do
  echo
  echo "======== REVIEW $d ========"
  {
    echo "## Layer: \`$d\`"
    echo
    files="$(git diff --name-only "$BASE" HEAD -- "$d" | wc -l | tr -d ' ')"
    echo "- Changed files in scope (git estimate): **$files**"
    echo
    echo '```text'
  } >>"$SUMMARY"

  set +e
  coderabbit review --agent --base-commit="$BASE" --dir "$d" 2>&1 | tee -a "$AGENT_ALL" | tee "/tmp/cr_agent_${d//\//_}.log"
  st_agent=${PIPESTATUS[0]}
  coderabbit review --base-commit="$BASE" --dir "$d" 2>&1 | tee -a "$SUMMARY"
  st_plain=${PIPESTATUS[0]}
  coderabbit review findings --agent 2>&1 | tee -a "$AGENT_ALL" || true
  set -e

  {
    echo '```'
    echo
    echo "exit: agent=$st_agent plain=$st_plain"
    echo
  } >>"$SUMMARY"
done

{
  echo "## Outputs"
  echo
  echo "- Summary: \`$SUMMARY\`"
  echo "- Agent NDJSON: \`$AGENT_ALL\`"
} >>"$SUMMARY"

ls -la "$OUT_DIR"
echo "SUMMARY_FILE=$SUMMARY"
echo "AGENT_FILE=$AGENT_ALL"
echo DONE
