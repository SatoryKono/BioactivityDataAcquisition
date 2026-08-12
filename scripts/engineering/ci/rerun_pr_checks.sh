#!/usr/bin/env bash
# Re-run failed GitHub Actions checks for a PR after billing/LFS unlock.
# Usage:
#   bash scripts/engineering/ci/rerun_pr_checks.sh 8658
#   bash scripts/engineering/ci/rerun_pr_checks.sh 8658 --empty-commit
set -euo pipefail

PR="${1:?usage: $0 <pr-number> [--empty-commit]}"
shift || true
EMPTY=0
for a in "$@"; do
  case "$a" in
    --empty-commit) EMPTY=1 ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

if ! command -v gh >/dev/null; then
  echo "gh CLI required" >&2
  exit 1
fi

echo "== PR $PR =="
gh pr view "$PR" --json number,url,state,headRefName,baseRefName,mergeable \
  --jq '"\(.url) state=\(.state) head=\(.headRefName) base=\(.baseRefName) mergeable=\(.mergeable)"'

# Sample annotation (billing lock detection)
ANN=$(gh api graphql -f query="
query {
  repository(owner:\"$(gh repo view --json owner -q .owner.login)\", name:\"$(gh repo view --json name -q .name)\") {
    pullRequest(number: $PR) {
      commits(last: 1) {
        nodes {
          commit {
            statusCheckRollup {
              contexts(first: 1) {
                nodes {
                  ... on CheckRun {
                    name
                    conclusion
                    annotations(first: 1) { nodes { message } }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}" --jq '..|objects|select(has("message"))|.message' 2>/dev/null | head -1 || true)

if [[ -n "${ANN:-}" ]]; then
  echo "sample annotation: $ANN"
  if echo "$ANN" | grep -qi 'billing'; then
    echo "WARNING: GitHub Actions still appears blocked by billing. Re-run will likely fail until unlocked." >&2
  fi
fi

HEAD=$(gh pr view "$PR" --json headRefName -q .headRefName)

if [[ "$EMPTY" -eq 1 ]]; then
  CURRENT=$(git branch --show-current 2>/dev/null || true)
  if [[ "$CURRENT" != "$HEAD" ]]; then
    echo "checkout $HEAD for empty commit"
    git fetch origin "$HEAD"
    git checkout "$HEAD"
  fi
  git commit --allow-empty -m "ci: re-trigger checks after Actions billing unlock (PR #${PR})"
  TOKEN=$(gh auth token)
  GIT_LFS_SKIP_PUSH=1 git push "https://x-access-token:${TOKEN}@github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner).git" "HEAD:${HEAD}"
  echo "empty commit pushed to $HEAD"
fi

echo "== re-run failed workflow runs on branch $HEAD =="
# List recent failed runs on the PR head branch and re-run failed jobs
mapfile -t RUNS < <(gh run list --branch "$HEAD" --limit 40 --json databaseId,conclusion,status,workflowName,url \
  --jq '.[] | select(.conclusion=="failure" or .conclusion=="cancelled" or .status=="completed") | select(.conclusion=="failure" or .conclusion=="cancelled") | "\(.databaseId)\t\(.workflowName)\t\(.url)"')

if [[ ${#RUNS[@]} -eq 0 ]]; then
  echo "no failed/cancelled runs found on branch $HEAD (limit 40)"
else
  echo "found ${#RUNS[@]} failed/cancelled runs"
  for line in "${RUNS[@]}"; do
    rid="${line%%$'\t'*}"
    echo "re-run failed: $line"
    gh run rerun "$rid" --failed || gh run rerun "$rid" || true
  done
fi

echo "== done =="
echo "watch: gh pr checks $PR --watch"
