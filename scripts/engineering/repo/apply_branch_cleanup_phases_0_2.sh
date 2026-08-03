#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

STAMP="$(date +%F)"
INVENTORY="reports/quality/branch-cleanup-inventory-${STAMP}.json"
PHASE1_REPORT="reports/quality/branch-cleanup-apply-phase1-${STAMP}.json"
PHASE2_REPORT="reports/quality/branch-cleanup-apply-phase2-${STAMP}.json"

APPLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --inventory)
      if [[ $# -lt 2 ]]; then
        echo "[FAIL] --inventory requires a path." >&2
        exit 2
      fi
      INVENTORY="$2"
      shift 2
      ;;
    --help|-h)
      cat <<'EOF'
Usage:
  bash scripts/engineering/repo/apply_branch_cleanup_phases_0_2.sh
  bash scripts/engineering/repo/apply_branch_cleanup_phases_0_2.sh --apply
  bash scripts/engineering/repo/apply_branch_cleanup_phases_0_2.sh --apply --inventory reports/quality/branch-cleanup-inventory-2026-07-10.json

Runs phase 0 inventory generation, then phases 1-2 apply via the Python GitHub API helper.
EOF
      exit 0
      ;;
    *)
      echo "[FAIL] Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${GITHUB_TOKEN:-}" && -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" && -z "${GH_TOKEN:-}" ]] \
  && command -v gh >/dev/null 2>&1; then
  export GITHUB_TOKEN="$(gh auth token)"
fi

echo "== Branch cleanup phases 0-2 =="
echo "repo: ${REPO_ROOT}"
echo "inventory: ${INVENTORY}"
echo "mode: $([[ "${APPLY}" -eq 1 ]] && echo apply || echo dry-run)"
echo

python -m scripts.engineering.repo generate-branch-cleanup-inventory --output "${INVENTORY}"

APPLY_ARGS=()
if [[ "${APPLY}" -eq 1 ]]; then
  APPLY_ARGS+=(--apply)
fi

python -m scripts.engineering.repo apply-branch-cleanup \
  --phases 1 \
  --inventory "${INVENTORY}" \
  "${APPLY_ARGS[@]}" \
  --report "${PHASE1_REPORT}"

python -m scripts.engineering.repo apply-branch-cleanup \
  --phases 2 \
  --inventory "${INVENTORY}" \
  "${APPLY_ARGS[@]}" \
  --report "${PHASE2_REPORT}"

echo
echo "[DONE] inventory: ${INVENTORY}"
echo "[DONE] phase1 report: ${PHASE1_REPORT}"
echo "[DONE] phase2 report: ${PHASE2_REPORT}"
