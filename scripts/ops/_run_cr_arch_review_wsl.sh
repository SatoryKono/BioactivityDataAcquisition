#!/usr/bin/env bash
# Exhaustive hexagonal architecture review via CodeRabbit.
# Uses a native-FS worktree + object alternates to avoid GDrive full-clone
# and Windows-git index extension mismatches under /mnt/e.
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

SRC=/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2
DST="${HOME}/bioetl-cr-review"
OUT="${SRC}/reports/quality/coderabbit"
BASE_REF="${1:-HEAD~300}"
TS="$(date +%Y%m%d_%H%M%S)"
SUMMARY="${OUT}/architecture-layered_${TS}.md"
AGENT_ALL="${OUT}/architecture-layered_${TS}.agent.ndjson"

echo "[$(date -Is)] prepare lightweight worktree at ${DST}"
rm -rf "${DST}"
mkdir -p "${DST}"
cd "${DST}"
git init -q
mkdir -p .git/objects/info
# One path per line; use echo to avoid PowerShell eating \n when the script is rewritten.
echo "${SRC}/.git/objects" > .git/objects/info/alternates
echo "alternates=$(cat .git/objects/info/alternates)"

HEAD="$(git --git-dir="${SRC}/.git" rev-parse HEAD)"
BASE="$(git --git-dir="${SRC}/.git" rev-parse "${BASE_REF}")"
echo "HEAD=${HEAD} BASE=${BASE}"

# Prove objects are reachable via alternates before building refs.
git cat-file -t "${HEAD}"
git cat-file -t "${BASE}"

# CodeRabbit needs a named base branch (not only --base-commit).
git update-ref refs/heads/arch-base "${BASE}"
git update-ref refs/heads/review "${HEAD}"
git symbolic-ref HEAD refs/heads/review
git config coderabbit.baseBranch arch-base
git sparse-checkout init --cone
git sparse-checkout set src/bioetl tests/architecture docs/02-architecture
git read-tree "${HEAD}"
git checkout-index -a -f

echo "[$(date -Is)] worktree ready"
ls src/bioetl
git rev-parse HEAD
git branch -v
git status -sb | head -5

mkdir -p "${OUT}"
: >"${AGENT_ALL}"
{
  echo "# CodeRabbit Exhaustive Architecture Review"
  echo
  echo "- HEAD: \`${HEAD}\`"
  echo "- BASE: \`${BASE}\` (\`${BASE_REF}\`)"
  echo "- Mode: layered hexagonal packages (CodeRabbit max 300 files per review)"
  echo "- Working copy: native WSL FS ${DST} (object alternates → ${SRC}/.git/objects)"
  echo "- Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
} >"${SUMMARY}"

DIRS=(
  src/bioetl/domain
  src/bioetl/application
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
    echo "- Changed files in scope (git estimate): **${files}**"
    echo
    echo '```text'
  } >>"${SUMMARY}"

  set +e
  echo "[$(date -Is)] coderabbit agent ${d} (files=${files})"
  log="/tmp/cr_agent_${d//\//_}.log"
  coderabbit review --agent --base arch-base --base-commit="${BASE}" --dir "${d}" 2>&1 | tee -a "${AGENT_ALL}" | tee "${log}"
  st_agent=${PIPESTATUS[0]}
  echo "[$(date -Is)] coderabbit plain ${d}"
  coderabbit review --base arch-base --base-commit="${BASE}" --dir "${d}" 2>&1 | tee -a "${SUMMARY}"
  st_plain=${PIPESTATUS[0]}
  coderabbit review findings --agent 2>&1 | tee -a "${AGENT_ALL}" || true
  set -e

  {
    echo '```'
    echo
    echo "exit: agent=${st_agent} plain=${st_plain}"
    echo
  } >>"${SUMMARY}"
done

{
  echo "## Outputs"
  echo
  echo "- Summary: \`${SUMMARY}\`"
  echo "- Agent NDJSON: \`${AGENT_ALL}\`"
} >>"${SUMMARY}"

echo "SUMMARY_FILE=${SUMMARY}"
echo "AGENT_FILE=${AGENT_ALL}"
echo DONE
