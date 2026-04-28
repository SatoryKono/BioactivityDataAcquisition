#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/engineering/repo/cleanup_branch_candidates.sh
  bash scripts/engineering/repo/cleanup_branch_candidates.sh --apply
  bash scripts/engineering/repo/cleanup_branch_candidates.sh --apply --with-remote
  bash scripts/engineering/repo/cleanup_branch_candidates.sh --apply --archive-date 2026-04-24

Behavior:
  - Dry-run is the default mode.
  - Deletes only the curated local branch candidates agreed during the branch audit.
  - Creates archive tags before deleting the archive group.
  - Removes origin/cleanup-backup only when --with-remote is provided.
  - Skips missing branches and refuses to delete the current branch.
  - Skips protected branches and branches that are still attached to a worktree.
EOF
  return 0
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "[FAIL] Must be run inside a git repository." >&2
  exit 1
fi

APPLY=0
WITH_REMOTE=0
ARCHIVE_DATE="$(date +%F)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --with-remote)
      WITH_REMOTE=1
      shift
      ;;
    --archive-date)
      if [[ $# -lt 2 ]]; then
        echo "[FAIL] --archive-date requires a value." >&2
        exit 2
      fi
      ARCHIVE_DATE="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "[FAIL] Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

CURRENT_BRANCH="$(git branch --show-current)"

MERGED_BRANCHES=(
  "cleanup-backup"
  "consolidate/recent-branches-20260422"
  "issue-2858-2861-normalization-cleanup"
  "main_20260414"
  "observability-2853-2857"
  "repro-2850-exact-replay-boundary"
  "repro-2851-composite-replay-reconstructability"
)

MIRROR_BRANCHES=(
  "consolidate/hygiene-low-risk"
  "consolidate/test-swarm-2649-clean"
  "docs/2685-normalization-sync"
  "feat/2712-audit-runtime-wiring"
  "feat/py-review-orchestrator-7377381600679085936"
  "fix-2793-neo4j-normalization-topology-v2"
  "issue/2733-bounded-observability-labels-v2"
  "main_20250404"
  "main_20250408"
  "main_20260404"
)

ARCHIVE_BRANCHES=(
  "main_20260410"
  "chore/consolidate-recent-branches"
  "fix-2728-fingerprint-contract"
  "fix-2749-normalization-matrix"
  "fix-2764-normalization-plan"
  "fix-2773-normalization-matrix-gate"
  "fix-2793-neo4j-normalization-topology"
  "integration/repro-2754-2761"
)

REMOTE_BRANCHES=(
  "cleanup-backup"
)

PROTECTED_BRANCHES=(
  "main_20260404"
)

branch_exists() {
  local branch="$1"
  git show-ref --verify --quiet "refs/heads/${branch}"
  return $?
}

remote_branch_exists() {
  local branch="$1"
  local status=1
  if git show-ref --verify --quiet "refs/remotes/origin/${branch}"; then
    status=0
  fi
  return "${status}"
}

archive_tag_for() {
  local branch="$1"
  printf 'archive/%s-%s' "${branch//\//-}" "${ARCHIVE_DATE}"
  return 0
}

log_action() {
  local action="$1"
  local subject="$2"
  printf '[%s] %s\n' "${action}" "${subject}"
  return 0
}

is_protected_branch() {
  local branch="$1"
  local protected
  for protected in "${PROTECTED_BRANCHES[@]}"; do
    if [[ "${branch}" == "${protected}" ]]; then
      return 0
    fi
  done
  return 1
}

delete_local_branch() {
  local branch="$1"
  local mode="$2"
  local output

  if [[ "${branch}" == "${CURRENT_BRANCH}" ]]; then
    log_action "SKIP" "${branch} (current branch)"
    return 0
  fi
  if is_protected_branch "${branch}"; then
    log_action "SKIP" "${branch} (protected)"
    return 0
  fi
  if ! branch_exists "${branch}"; then
    log_action "SKIP" "${branch} (missing)"
    return 0
  fi

  if [[ "${APPLY}" -eq 0 ]]; then
    log_action "PLAN" "git branch ${mode} ${branch}"
    return 0
  fi

  if ! output="$(git branch "${mode}" "${branch}" 2>&1)"; then
    if [[ "${output}" == *"used by worktree"* ]]; then
      log_action "SKIP" "${branch} (used by worktree)"
      return 0
    fi
    printf '%s\n' "${output}" >&2
    return 1
  fi
  if [[ -n "${output}" ]]; then
    printf '%s\n' "${output}"
  fi
  log_action "DONE" "deleted ${branch}"
  return 0
}

archive_then_delete() {
  local branch="$1"
  local tag
  local output

  if [[ "${branch}" == "${CURRENT_BRANCH}" ]]; then
    log_action "SKIP" "${branch} (current branch)"
    return 0
  fi
  if is_protected_branch "${branch}"; then
    log_action "SKIP" "${branch} (protected)"
    return 0
  fi
  if ! branch_exists "${branch}"; then
    log_action "SKIP" "${branch} (missing)"
    return 0
  fi

  tag="$(archive_tag_for "${branch}")"
  if [[ "${APPLY}" -eq 0 ]]; then
    log_action "PLAN" "git tag ${tag} ${branch}"
    log_action "PLAN" "git branch -D ${branch}"
    return 0
  fi

  if git rev-parse --verify --quiet "${tag}" >/dev/null; then
    log_action "SKIP" "${tag} (tag exists)"
  else
    git tag "${tag}" "${branch}"
    log_action "DONE" "tagged ${branch} as ${tag}"
  fi
  if ! output="$(git branch -D "${branch}" 2>&1)"; then
    if [[ "${output}" == *"used by worktree"* ]]; then
      log_action "SKIP" "${branch} (used by worktree)"
      return 0
    fi
    printf '%s\n' "${output}" >&2
    return 1
  fi
  if [[ -n "${output}" ]]; then
    printf '%s\n' "${output}"
  fi
  log_action "DONE" "deleted ${branch}"
  return 0
}

delete_remote_branch() {
  local branch="$1"
  local output
  local askpass="${GIT_ASKPASS:-}"
  local -a git_cmd=(git push origin --delete "${branch}")
  local -a env_cmd=()

  if ! remote_branch_exists "${branch}"; then
    log_action "SKIP" "origin/${branch} (missing)"
    return 0
  fi
  if [[ "${WITH_REMOTE}" -eq 0 ]]; then
    log_action "PLAN" "git push origin --delete ${branch}"
    return 0
  fi
  if [[ "${APPLY}" -eq 0 ]]; then
    log_action "PLAN" "git push origin --delete ${branch}"
    return 0
  fi

  if [[ -n "${askpass}" && ! -e "${askpass}" ]]; then
    log_action "INFO" "unsetting stale GIT_ASKPASS=${askpass}"
    env_cmd=(env -u GIT_ASKPASS)
  fi

  if ! output="$("${env_cmd[@]}" "${git_cmd[@]}" 2>&1)"; then
    if [[ "${output}" == *"github-askpass.sh"* || "${output}" == *"No such file or directory"* ]]; then
      log_action "FAIL" "origin/${branch} (stale askpass helper; run 'unset GIT_ASKPASS' and retry)"
      printf '%s\n' "${output}" >&2
      return 0
    fi
    if [[ "${output}" == *"Authentication failed"* || "${output}" == *"could not read Username"* || "${output}" == *"Password for"* ]]; then
      log_action "FAIL" "origin/${branch} (authentication required; retry after gh auth or PAT setup)"
      printf '%s\n' "${output}" >&2
      return 0
    fi
    printf '%s\n' "${output}" >&2
    return 1
  fi
  if [[ -n "${output}" ]]; then
    printf '%s\n' "${output}"
  fi
  log_action "DONE" "deleted origin/${branch}"
  return 0
}

echo "== Branch Cleanup Candidates =="
echo "repo: ${REPO_ROOT}"
echo "current branch: ${CURRENT_BRANCH}"
echo "mode: $([[ "${APPLY}" -eq 1 ]] && echo apply || echo dry-run)"
echo "archive date: ${ARCHIVE_DATE}"
echo

echo "-- merged local branches --"
for branch in "${MERGED_BRANCHES[@]}"; do
  delete_local_branch "${branch}" -d
done
echo

echo "-- mirror local branches --"
for branch in "${MIRROR_BRANCHES[@]}"; do
  delete_local_branch "${branch}" -D
done
echo

echo "-- archive then delete local branches --"
for branch in "${ARCHIVE_BRANCHES[@]}"; do
  archive_then_delete "${branch}"
done
echo

echo "-- remote branches --"
for branch in "${REMOTE_BRANCHES[@]}"; do
  delete_remote_branch "${branch}"
done
