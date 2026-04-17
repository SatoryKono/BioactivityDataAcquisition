#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)"
# shellcheck source=../../support/load_repo_env.sh
source "${SCRIPT_DIR}/../../support/load_repo_env.sh"

REPORT_MODE="report"
MODE="$REPORT_MODE"
ASSUME_YES=0
DO_FETCH=1

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PROTECTED_BRANCHES=(
  "main"
  "main_20250408"
  "generate-review-reports-12039392608197755189"
  "bolt-optimize-column-orderer-helpers-17720322478388326854"
  "py-test-swarm-reports-17470800817558701356"
  "dependabot/github_actions/actions/cache-5"
  "codex/categorize-and-tidy-up-type-ignores"
  "perf-async-metrics-server-1814537927827611323"
)

DELETE_CANDIDATES=(
  "jules-run-code-review-orchestrator-6570426735123498990"
  "test-swarm-reports-11115732830350980092"
  "bolt-optimize-sorting-13782224520442588262"
  "ai-hierarchical-code-review-377991794209424974"
  "ai-code-review-11260436480377693745"
  "jules-code-review-orchestrator-17605596549365275139"
  "review/hierarchical-code-review-13047481877801782444"
  "review-orchestrator-analysis-8687423604472367922"
  "py-review-orchestrator-execution-7162427255251795129"
  "py-review-orchestrator-ast-script-12739399795982722227"
  "swarm-metrics-7763761693969922558"
  "test-swarm-reports-6841942603068135714"
  "test-swarm-reports-swarm-001-6464421493149807499"
  "add-review-reports-14140296571349509559"
  "add-py-review-reports-11144737295225843882"
  "docs-code-review-5155988922031284115"
  "tmp01"
)

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/maintenance/git/delete-stale-branches.sh [--mode report|delete-local|delete-remote|delete-both] [--yes] [--no-fetch]

Modes:
  report         Show cleanup ledger only. Default and non-destructive.
  delete-local   Delete only local candidate branches that are safe to remove.
  delete-remote  Delete only remote candidate branches that are safe to remove.
  delete-both    Delete local and remote candidate branches that are safe to remove.

Safety rules:
  - Protected branches are never deleted.
  - Branches with open PRs are never deleted.
  - Branches with unique commits ahead of origin/main are never deleted automatically.
  - Non-report modes require --yes.

Examples:
  bash scripts/ops/maintenance/git/delete-stale-branches.sh
  bash scripts/ops/maintenance/git/delete-stale-branches.sh --mode delete-remote --yes
EOF
  return 0
}

contains() {
  local needle="$1"
  shift
  local item
  for item in "$@"; do
    if [[ "$item" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

have_command() {
  local command_name="$1"
  if command -v "$command_name" >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

resolve_python_runner() {
  if have_command python3; then
    PYTHON_RUNNER=(python3)
  elif have_command python; then
    PYTHON_RUNNER=(python)
  elif have_command py; then
    PYTHON_RUNNER=(py -3)
  fi
  return 0
}

resolve_tool_variants() {
  if have_command gh; then
    GH_CMD="gh"
  elif have_command gh.exe; then
    GH_CMD="gh.exe"
  fi

  if have_command curl; then
    CURL_CMD="curl"
  elif have_command curl.exe; then
    CURL_CMD="curl.exe"
  fi
  return 0
}

prepare_git_auth() {
  local origin_url configured_askpass

  load_repo_env_if_present

  if [[ -n "${GH_TOKEN:-}" ]]; then
    GITHUB_AUTH_TOKEN="${GH_TOKEN}"
  elif [[ -n "${GITHUB_TOKEN:-}" ]]; then
    GITHUB_AUTH_TOKEN="${GITHUB_TOKEN}"
  elif [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
    GITHUB_AUTH_TOKEN="${GITHUB_PERSONAL_ACCESS_TOKEN}"
  fi

  origin_url="$(git remote get-url origin 2>/dev/null || true)"
  if [[ ! "$origin_url" =~ ^https://github\.com/ ]]; then
    return 0
  fi

  configured_askpass="$(git config --get core.askpass || true)"

  if [[ -n "$GITHUB_AUTH_TOKEN" ]]; then
    TEMP_GIT_ASKPASS="$(mktemp)"
    cat >"$TEMP_GIT_ASKPASS" <<'EOF'
#!/usr/bin/env sh
case "$1" in
  *Username*) printf '%s\n' "x-access-token" ;;
  *) printf '%s\n' "${BIOETL_GITHUB_PUSH_TOKEN:-}" ;;
esac
EOF
    chmod 700 "$TEMP_GIT_ASKPASS"
    export BIOETL_GITHUB_PUSH_TOKEN="$GITHUB_AUTH_TOKEN"
    export GIT_ASKPASS="$TEMP_GIT_ASKPASS"
    export GIT_TERMINAL_PROMPT=0
    return 0
  fi

  if [[ -n "$configured_askpass" && ! -x "$configured_askpass" ]]; then
    printf "%b[FAIL]%b git core.askpass points to a missing file: %s\n" "$RED" "$NC" "$configured_askpass" >&2
    printf "%b[FAIL]%b No GitHub token found in GH_TOKEN, GITHUB_TOKEN, or GITHUB_PERSONAL_ACCESS_TOKEN\n" "$RED" "$NC" >&2
    exit 1
  fi
}

validate_github_api_auth() {
  local http_code

  if [[ -z "${REMOTE_REPO_SLUG}" || -z "${GITHUB_AUTH_TOKEN}" || -z "${CURL_CMD}" ]]; then
    return 0
  fi

  http_code="$(
    "$CURL_CMD" -sS -o /dev/null -w '%{http_code}' \
      -H "Authorization: token ${GITHUB_AUTH_TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/user" || printf '000'
  )"

  case "$http_code" in
    200) return 0 ;;
    401)
      printf "%b[FAIL]%b GitHub API rejected the token with HTTP 401\n" "$RED" "$NC" >&2
      printf "%b[FAIL]%b Check GITHUB_PERSONAL_ACCESS_TOKEN / GH_TOKEN / GITHUB_TOKEN in .env and ensure it is still valid\n" "$RED" "$NC" >&2
      exit 1
      ;;
    403)
      printf "%b[FAIL]%b GitHub API rejected the token with HTTP 403\n" "$RED" "$NC" >&2
      printf "%b[FAIL]%b Token is present but likely lacks required repo/contents write permissions for branch deletion\n" "$RED" "$NC" >&2
      exit 1
      ;;
    *)
      printf "%b[FAIL]%b GitHub API auth preflight failed with HTTP %s\n" "$RED" "$NC" "$http_code" >&2
      exit 1
      ;;
  esac
}

print_status() {
  local color="$1"
  local text="$2"
  printf "%b%s%b" "$color" "$text" "$NC"
  return 0
}

resolve_repo_slug() {
  local remote_url
  remote_url="$(git remote get-url origin 2>/dev/null || true)"
  if [[ "$remote_url" =~ github\.com[:/]+([^/]+/[^/.]+)(\.git)?$ ]]; then
    printf "%s\n" "${BASH_REMATCH[1]}"
  fi
  return 0
}

REMOTE_REPO_SLUG="$(resolve_repo_slug)"
OPEN_PR_LOOKUP_AVAILABLE=0
PYTHON_RUNNER=()
GH_CMD=""
CURL_CMD=""
TEMP_GIT_ASKPASS=""
GITHUB_AUTH_TOKEN=""

if [[ ! -d "${REPO_ROOT}/.git" ]]; then
  printf "%b[FAIL]%b Not inside a git repository: %s\n" "$RED" "$NC" "$REPO_ROOT" >&2
  exit 1
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      [[ $# -ge 2 ]] || { usage; exit 1; }
      MODE="$2"
      shift 2
      ;;
    --yes)
      ASSUME_YES=1
      shift
      ;;
    --no-fetch)
      DO_FETCH=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf "%b[FAIL]%b Unknown argument: %s\n" "$RED" "$NC" "$1" >&2
      usage
      exit 1
      ;;
  esac
done

case "$MODE" in
  report|delete-local|delete-remote|delete-both) ;;
  *)
    printf "%b[FAIL]%b Unsupported mode: %s\n" "$RED" "$NC" "$MODE" >&2
    usage
    exit 1
    ;;
esac

if [[ "$MODE" != "$REPORT_MODE" && "$ASSUME_YES" -ne 1 ]]; then
  printf "%b[FAIL]%b Non-report modes require --yes\n" "$RED" "$NC" >&2
  exit 1
fi

cd "$REPO_ROOT"
resolve_python_runner
resolve_tool_variants

if [[ "$MODE" != "$REPORT_MODE" ]]; then
  prepare_git_auth
  validate_github_api_auth
fi

if [[ "$DO_FETCH" -eq 1 ]]; then
  printf "%b[INFO]%b git fetch --all --prune\n" "$BLUE" "$NC"
  git fetch --all --prune
fi

OPEN_PR_CACHE_FILE="$(mktemp)"
OPEN_PR_API_RAW_FILE="$(mktemp)"
cleanup() {
  rm -f "$OPEN_PR_CACHE_FILE"
  rm -f "$OPEN_PR_API_RAW_FILE"
  rm -f "$TEMP_GIT_ASKPASS"
  return 0
}
trap cleanup EXIT

if [[ ${#PYTHON_RUNNER[@]} -gt 0 ]] && [[ -n "${REMOTE_REPO_SLUG}" ]] && [[ -n "${GH_CMD}" || -n "${CURL_CMD}" ]]; then
  OPEN_PR_LOOKUP_AVAILABLE=1
  if [[ -n "${GH_CMD}" ]]; then
    "$GH_CMD" pr list --repo "$REMOTE_REPO_SLUG" --state open --limit 200 --json headRefName,number,url,title >"$OPEN_PR_CACHE_FILE" || printf "[]\n" >"$OPEN_PR_CACHE_FILE"
  else
    "$CURL_CMD" -fsSL "https://api.github.com/repos/${REMOTE_REPO_SLUG}/pulls?state=open&per_page=100" >"$OPEN_PR_API_RAW_FILE" || printf "[]\n" >"$OPEN_PR_API_RAW_FILE"
    "${PYTHON_RUNNER[@]}" - "$OPEN_PR_API_RAW_FILE" <<'PY' >"$OPEN_PR_CACHE_FILE"
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    payload = json.load(fh)
rows = [
    {
        "headRefName": pr.get("head", {}).get("ref"),
        "number": pr.get("number"),
        "url": pr.get("html_url"),
        "title": pr.get("title"),
    }
    for pr in payload
]
json.dump(rows, sys.stdout)
PY
  fi
else
  printf "[]\n" >"$OPEN_PR_CACHE_FILE"
fi

branch_has_open_pr() {
  local branch="$1"
  if [[ "$OPEN_PR_LOOKUP_AVAILABLE" -ne 1 ]]; then
    return 1
  fi
  "${PYTHON_RUNNER[@]}" - "$OPEN_PR_CACHE_FILE" "$branch" <<'PY'
import json
import sys

cache_path, branch = sys.argv[1], sys.argv[2]
with open(cache_path, "r", encoding="utf-8") as fh:
    prs = json.load(fh)
for pr in prs:
    if pr.get("headRefName") == branch:
        print(f"{pr.get('number')}|{pr.get('url')}")
        raise SystemExit(0)
raise SystemExit(1)
PY
}

remote_branch_exists() {
  local branch="$1"
  git show-ref --verify --quiet "refs/remotes/origin/$branch"
  return $?
}

local_branch_exists() {
  local branch="$1"
  git show-ref --verify --quiet "refs/heads/$branch"
  return $?
}

current_branch() {
  git symbolic-ref --quiet --short HEAD 2>/dev/null || true
  return 0
}

branch_is_merged_remote() {
  local branch="$1"
  git branch -r --merged origin/main | sed 's#^[ *]*origin/##' | grep -Fx -- "$branch" >/dev/null 2>&1
}

branch_ahead_count() {
  local branch="$1"
  local left_right
  left_right="$(git rev-list --left-right --count "origin/main...origin/$branch" 2>/dev/null || printf '0\t999999')"
  printf "%s\n" "${left_right#*	}"
  return 0
}

recommendation_for_branch() {
  local branch="$1"
  local open_pr_result
  if contains "$branch" "${PROTECTED_BRANCHES[@]}"; then
    printf "KEEP:protected"
    return 0
  fi
  if [[ "$OPEN_PR_LOOKUP_AVAILABLE" -ne 1 ]]; then
    printf "REVIEW:pr-check-unavailable"
    return 0
  fi
  if open_pr_result="$(branch_has_open_pr "$branch" 2>/dev/null)"; then
    printf "KEEP:open-pr:%s" "$open_pr_result"
    return 0
  fi
  if ! remote_branch_exists "$branch" && ! local_branch_exists "$branch"; then
    printf "SKIP:not-found"
    return 0
  fi
  if remote_branch_exists "$branch"; then
    local ahead
    ahead="$(branch_ahead_count "$branch")"
    if [[ "$ahead" != "0" ]]; then
      printf "REVIEW:unique-commits:%s" "$ahead"
      return 0
    fi
    if branch_is_merged_remote "$branch"; then
      printf "DELETE:merged"
      return 0
    fi
  fi
  printf "DELETE:candidate"
}

print_header() {
  printf "%-58s %-6s %-7s %-7s %-8s %-24s %s\n" "branch" "local" "remote" "merged" "ahead" "recommendation" "details"
  printf "%-58s %-6s %-7s %-7s %-8s %-24s %s\n" \
    "----------------------------------------------------------" \
    "------" "-------" "-------" "--------" \
    "------------------------" \
    "------------------------------"
  return 0
}

delete_local_branch() {
  local branch="$1"
  local current
  current="$(current_branch)"
  if [[ "$current" == "$branch" ]]; then
    printf "%b[SKIP]%b local %s (checked out)\n" "$YELLOW" "$NC" "$branch"
    return 0
  fi
  if local_branch_exists "$branch"; then
    git branch -D "$branch"
  fi
  return 0
}

delete_remote_branch() {
  local branch="$1"
  local encoded_branch api_url
  if ! remote_branch_exists "$branch"; then
    return 0
  fi

  if [[ -n "${REMOTE_REPO_SLUG}" && -n "${GITHUB_AUTH_TOKEN}" && -n "${CURL_CMD}" ]]; then
    encoded_branch="${branch//\//%2F}"
    api_url="https://api.github.com/repos/${REMOTE_REPO_SLUG}/git/refs/heads/${encoded_branch}"
    "$CURL_CMD" -fsSL -X DELETE \
      -H "Authorization: token ${GITHUB_AUTH_TOKEN}" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "$api_url" >/dev/null
    return 0
  fi

  git push origin --delete "$branch"
  return 0
}

print_header

for branch in "${DELETE_CANDIDATES[@]}"; do
  local_state="no"
  remote_state="no"
  merged_state="-"
  ahead_state="-"
  details=""
  recommendation="$(recommendation_for_branch "$branch")"

  if local_branch_exists "$branch"; then
    local_state="yes"
  fi
  if remote_branch_exists "$branch"; then
    remote_state="yes"
    if branch_is_merged_remote "$branch"; then
      merged_state="yes"
    else
      merged_state="no"
    fi
    ahead_state="$(branch_ahead_count "$branch")"
  fi

  case "$recommendation" in
    KEEP:protected)
      details="protected"
      rec_display="$(print_status "$GREEN" "KEEP")"
      ;;
    KEEP:open-pr:*)
      details="${recommendation#KEEP:open-pr:}"
      rec_display="$(print_status "$GREEN" "KEEP")"
      ;;
    REVIEW:unique-commits:*)
      details="ahead=${recommendation#REVIEW:unique-commits:}"
      rec_display="$(print_status "$YELLOW" "REVIEW")"
      ;;
    REVIEW:pr-check-unavailable)
      details="no gh/curl/python runtime for PR lookup"
      rec_display="$(print_status "$YELLOW" "REVIEW")"
      ;;
    DELETE:merged)
      details="merged into origin/main"
      rec_display="$(print_status "$RED" "DELETE")"
      ;;
    DELETE:candidate)
      details="candidate list, no open PR"
      rec_display="$(print_status "$RED" "DELETE")"
      ;;
    SKIP:not-found)
      details="not found locally/remotely"
      rec_display="$(print_status "$BLUE" "SKIP")"
      ;;
    *)
      details="$recommendation"
      rec_display="$(print_status "$YELLOW" "REVIEW")"
      ;;
  esac

  printf "%-58s %-6s %-7s %-7s %-8s %-24b %s\n" \
    "$branch" "$local_state" "$remote_state" "$merged_state" "$ahead_state" "$rec_display" "$details"

  if [[ "$MODE" == "$REPORT_MODE" ]]; then
    continue
  fi

  case "$recommendation" in
    DELETE:*)
      if [[ "$MODE" == "delete-local" || "$MODE" == "delete-both" ]]; then
        delete_local_branch "$branch"
      fi
      if [[ "$MODE" == "delete-remote" || "$MODE" == "delete-both" ]]; then
        delete_remote_branch "$branch"
      fi
      ;;
    *)
      ;;
  esac
done

printf "\n%b[OK]%b Completed mode=%s\n" "$GREEN" "$NC" "$MODE"
