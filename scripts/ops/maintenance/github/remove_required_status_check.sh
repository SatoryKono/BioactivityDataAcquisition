#!/usr/bin/env bash
set -euo pipefail

# Remove a required status-check *context* from a branch's classic protection.
#
# Context: "Mintlify Deployment" is posted by the external Mintlify GitHub App,
# not by any workflow in .github/workflows. After you disconnect the Mintlify
# App from the repo, a still-required "Mintlify Deployment" check would block
# merges with "Expected - Waiting for status to be reported". This script strips
# that stale required context from classic branch protection so PRs are not
# wedged. It does not touch workflow files (there is nothing Mintlify there).

DEFAULT_OWNER="SatoryKono"
DEFAULT_REPO="BioactivityDataAcquisition"
DEFAULT_BRANCH="main"
DEFAULT_CONTEXT="Mintlify Deployment"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/maintenance/github/remove_required_status_check.sh [options]

Removes a required status-check context from a branch's classic protection.

Options:
  --context TEXT   Status-check context to remove (default: "Mintlify Deployment")
  --branch NAME    Protected branch (default: main)
  --owner NAME     Repository owner (default: SatoryKono)
  --repo NAME      Repository name (default: BioactivityDataAcquisition)
  --dry-run        Show current contexts and the planned change; do not modify
  --yes            Do not prompt for confirmation before deleting
  -h, --help       Show this help

Environment (first match wins; token needs repo admin, not just issues:write):
  GITHUB_PERSONAL_ACCESS_TOKEN | GH_TOKEN | GITHUB_TOKEN

Examples:
  # Preview only (no changes)
  bash scripts/ops/maintenance/github/remove_required_status_check.sh --dry-run

  # Remove the default "Mintlify Deployment" required check from main
  bash scripts/ops/maintenance/github/remove_required_status_check.sh --yes

  # Remove a different context from a release branch
  bash scripts/ops/maintenance/github/remove_required_status_check.sh \
    --branch release/1.x --context "mintlify" --yes
EOF
  return 0
}

OWNER="$DEFAULT_OWNER"
REPO="$DEFAULT_REPO"
BRANCH="$DEFAULT_BRANCH"
CONTEXT="$DEFAULT_CONTEXT"
DRY_RUN=0
ASSUME_YES=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --context) CONTEXT="${2:-}"; shift 2 ;;
    --branch)  BRANCH="${2:-}"; shift 2 ;;
    --owner)   OWNER="${2:-}"; shift 2 ;;
    --repo)    REPO="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --yes)     ASSUME_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$CONTEXT" ]]; then
  printf 'Empty --context\n' >&2
  exit 2
fi

resolve_auth_token() {
  if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then printf '%s' "${GITHUB_PERSONAL_ACCESS_TOKEN}"; return 0; fi
  if [[ -n "${GH_TOKEN:-}" ]]; then printf '%s' "${GH_TOKEN}"; return 0; fi
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then printf '%s' "${GITHUB_TOKEN}"; return 0; fi
  return 1
}

if ! AUTH_TOKEN="$(resolve_auth_token)"; then
  printf '%s\n' 'Missing GitHub token. Set one of: GITHUB_PERSONAL_ACCESS_TOKEN, GH_TOKEN, GITHUB_TOKEN' >&2
  exit 1
fi

API="https://api.github.com/repos/${OWNER}/${REPO}"
HEADERS=(
  -H "Accept: application/vnd.github+json"
  -H "Authorization: Bearer ${AUTH_TOKEN}"
  -H "X-GitHub-Api-Version: 2022-11-28"
)

resp_file="$(mktemp)"
del_file="$(mktemp)"
trap 'rm -f "$resp_file" "$del_file"' EXIT

checks_path="/branches/${BRANCH}/protection/required_status_checks"
http_code="$(curl -sS -o "$resp_file" -w "%{http_code}" "${HEADERS[@]}" "${API}${checks_path}")"

if [[ "$http_code" == "404" ]]; then
  printf 'No classic required-status-checks on %s/%s@%s (HTTP 404).\n' "$OWNER" "$REPO" "$BRANCH"
  printf 'Nothing to remove here. If the check is enforced via a ruleset, edit it under:\n'
  printf '  Settings -> Rules -> Rulesets   (or: gh api repos/%s/%s/rulesets)\n' "$OWNER" "$REPO"
  exit 0
fi
if [[ "$http_code" -lt 200 || "$http_code" -ge 300 ]]; then
  printf '[FAIL] GET required_status_checks returned HTTP %s\n' "$http_code" >&2
  [[ -s "$resp_file" ]] && { cat "$resp_file" >&2; printf '\n' >&2; }
  if [[ "$http_code" == "401" || "$http_code" == "403" ]]; then
    printf '%s\n' 'Token likely lacks repo admin permission required to read/edit branch protection.' >&2
  fi
  exit 1
fi

printf 'Current required contexts on %s/%s@%s:\n' "$OWNER" "$REPO" "$BRANCH"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); c=d.get("contexts",[]); print("\n".join("  - "+x for x in c) if c else "  (none)")' "$resp_file"

present="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("1" if sys.argv[2] in d.get("contexts",[]) else "0")' "$resp_file" "$CONTEXT")"

if [[ "$present" != "1" ]]; then
  printf '\nContext "%s" is NOT a required check on %s. Nothing to do.\n' "$CONTEXT" "$BRANCH"
  printf 'Tip: newer required checks may live in a ruleset: gh api repos/%s/%s/rulesets\n' "$OWNER" "$REPO"
  exit 0
fi

printf '\nPlanned: remove required context "%s" from %s.\n' "$CONTEXT" "$BRANCH"

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf '[DRY-RUN] DELETE %s%s/contexts  body={"contexts":["%s"]}\n' "$API" "$checks_path" "$CONTEXT"
  exit 0
fi

if [[ "$ASSUME_YES" -ne 1 ]]; then
  read -r -p 'Proceed? [y/N] ' ans
  case "$ans" in
    y|Y|yes|YES) ;;
    *) printf 'Aborted.\n'; exit 0 ;;
  esac
fi

body="$(python3 -c 'import json,sys; print(json.dumps({"contexts":[sys.argv[1]]}))' "$CONTEXT")"
del_code="$(curl -sS -o "$del_file" -w "%{http_code}" -X DELETE "${HEADERS[@]}" \
  -H "Content-Type: application/json" \
  "${API}${checks_path}/contexts" --data "$body")"

if [[ "$del_code" -lt 200 || "$del_code" -ge 300 ]]; then
  printf '[FAIL] DELETE contexts returned HTTP %s\n' "$del_code" >&2
  [[ -s "$del_file" ]] && { cat "$del_file" >&2; printf '\n' >&2; }
  exit 1
fi

printf 'Removed. Remaining required contexts:\n'
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d=d if isinstance(d,list) else d.get("contexts",[]); print("\n".join("  - "+x for x in d) if d else "  (none)")' "$del_file"
printf '\nDone: "%s" is no longer a required status check on %s/%s@%s.\n' "$CONTEXT" "$OWNER" "$REPO" "$BRANCH"
