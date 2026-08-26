#!/usr/bin/env bash
# Resume remaining architecture layers (agent-only, with per-layer timeout).
set -euo pipefail
export PATH="${HOME}/.local/bin:${PATH}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="${BIOETL_CR_REVIEW_SRC:-$REPO_ROOT}"
DST="${HOME}/bioetl-cr-review"
OUT="${SRC}/reports/quality/coderabbit"
BASE_REF="${1:-HEAD~300}"
TIMEOUT_SECS="${CR_LAYER_TIMEOUT:-1500}"
TS="$(date +%Y%m%d_%H%M%S)"
SUMMARY="${OUT}/architecture-layered-remaining_${TS}.md"
AGENT_ALL="${OUT}/architecture-layered-remaining_${TS}.agent.ndjson"
CONSOLIDATED="${OUT}/architecture-layered-remaining_${TS}_consolidated.md"

if [[ ! -d "${DST}/.git" ]]; then
  echo "missing worktree ${DST}; run full script first" >&2
  exit 2
fi
cd "${DST}"
HEAD="$(git rev-parse HEAD)"
BASE="$(git rev-parse "${BASE_REF}" 2>/dev/null || git rev-parse arch-base)"
git config coderabbit.baseBranch arch-base || true
if ! git show-ref --verify --quiet refs/heads/arch-base; then
  git update-ref refs/heads/arch-base "${BASE}"
fi

mkdir -p "${OUT}"
: >"${AGENT_ALL}"
{
  echo "# CodeRabbit Architecture Review — remaining layers"
  echo
  echo "- HEAD: \`${HEAD}\`"
  echo "- BASE: \`${BASE}\`"
  echo "- Mode: agent-only, timeout ${TIMEOUT_SECS}s/layer"
  echo "- Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
} >"${SUMMARY}"

DIRS=(
  src/bioetl/composition
  src/bioetl/infrastructure
  src/bioetl/interfaces
  tests/architecture
  docs/02-architecture
)

for d in "${DIRS[@]}"; do
  echo "======== REVIEW ${d} ========"
  files="$(git diff --name-only "${BASE}" HEAD -- "${d}" | wc -l | tr -d ' ')"
  {
    echo "## Layer: \`${d}\`"
    echo
    echo "- Changed files: **${files}**"
    echo
    echo '```text'
  } >>"${SUMMARY}"

  set +e
  log="/tmp/cr_agent_${d//\//_}.log"
  echo "[$(date -Is)] agent ${d} files=${files} timeout=${TIMEOUT_SECS}"
  # shellcheck disable=SC2086
  timeout --signal=TERM --kill-after=30 "${TIMEOUT_SECS}" \
    coderabbit review --agent --base arch-base --base-commit="${BASE}" --dir "${d}" \
    2>&1 | tee -a "${AGENT_ALL}" | tee "${log}"
  st=${PIPESTATUS[0]}
  set -e

  {
    echo '```'
    echo
    echo "exit: agent=${st}"
    echo
  } >>"${SUMMARY}"
done

python3 "${SRC}/scripts/ops/_build_arch_review_report.py" \
  "${AGENT_ALL}" \
  "${CONSOLIDATED}"

echo "SUMMARY_FILE=${SUMMARY}"
echo "AGENT_FILE=${AGENT_ALL}"
echo "CONSOLIDATED_FILE=${CONSOLIDATED}"
echo DONE
