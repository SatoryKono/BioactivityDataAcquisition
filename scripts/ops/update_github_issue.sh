#!/usr/bin/env bash
set -euo pipefail

DEFAULT_OWNER="SatoryKono"
DEFAULT_REPO="BioactivityDataAcquisition"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/update_github_issue.sh --issue NUMBER [options]

Options:
  --issue NUMBER         GitHub issue number to update (required)
  --title-file PATH      Read updated title from file
  --body-file PATH       Read updated body from file
  --comment-file PATH    Post a comment from file contents
  --state STATE          Patch issue state: open | closed
  --owner NAME           Repository owner (default: SatoryKono)
  --repo NAME            Repository name (default: BioactivityDataAcquisition)
  --dry-run              Print API operations without sending them
  -h, --help             Show this help

Environment:
  GITHUB_PERSONAL_ACCESS_TOKEN   Fine-grained or classic token with issue write access

Examples:
  bash scripts/ops/update_github_issue.sh \
    --issue 2594 \
    --comment-file /tmp/comment.md \
    --state closed

  bash scripts/ops/update_github_issue.sh \
    --issue 2511 \
    --title-file /tmp/title.txt \
    --body-file /tmp/body.md
EOF
}

OWNER="$DEFAULT_OWNER"
REPO="$DEFAULT_REPO"
ISSUE_NUMBER=""
TITLE_FILE=""
BODY_FILE=""
COMMENT_FILE=""
STATE=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      ISSUE_NUMBER="${2:-}"
      shift 2
      ;;
    --title-file)
      TITLE_FILE="${2:-}"
      shift 2
      ;;
    --body-file)
      BODY_FILE="${2:-}"
      shift 2
      ;;
    --comment-file)
      COMMENT_FILE="${2:-}"
      shift 2
      ;;
    --state)
      STATE="${2:-}"
      shift 2
      ;;
    --owner)
      OWNER="${2:-}"
      shift 2
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$ISSUE_NUMBER" ]]; then
  printf 'Missing required argument: --issue\n\n' >&2
  usage >&2
  exit 2
fi

if [[ -n "$STATE" && "$STATE" != "open" && "$STATE" != "closed" ]]; then
  printf 'Invalid --state: %s (expected open or closed)\n' "$STATE" >&2
  exit 2
fi

if [[ -n "$TITLE_FILE" && ! -f "$TITLE_FILE" ]]; then
  printf 'Title file not found: %s\n' "$TITLE_FILE" >&2
  exit 2
fi
if [[ -n "$BODY_FILE" && ! -f "$BODY_FILE" ]]; then
  printf 'Body file not found: %s\n' "$BODY_FILE" >&2
  exit 2
fi
if [[ -n "$COMMENT_FILE" && ! -f "$COMMENT_FILE" ]]; then
  printf 'Comment file not found: %s\n' "$COMMENT_FILE" >&2
  exit 2
fi

if [[ -z "$TITLE_FILE" && -z "$BODY_FILE" && -z "$COMMENT_FILE" && -z "$STATE" ]]; then
  printf 'Nothing to do: provide at least one of --title-file, --body-file, --comment-file, or --state\n' >&2
  exit 2
fi

: "${GITHUB_PERSONAL_ACCESS_TOKEN:?Set GITHUB_PERSONAL_ACCESS_TOKEN first}"

API="https://api.github.com/repos/${OWNER}/${REPO}"

api() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[DRY-RUN] %s %s\n' "$method" "$path"
    if [[ -n "$data" ]]; then
      printf '%s\n\n' "$data"
    fi
    return 0
  fi

  if [[ -n "$data" ]]; then
    curl -fsS -X "$method" \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      -H "Content-Type: application/json" \
      "${API}${path}" \
      --data "$data" >/dev/null
  else
    curl -fsS -X "$method" \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "${API}${path}" >/dev/null
  fi
}

json_from_stdin_as_comment() {
  python3 -c 'import json, sys; print(json.dumps({"body": sys.stdin.read()}))'
}

build_issue_patch() {
  python3 - "$TITLE_FILE" "$BODY_FILE" "$STATE" <<'PY'
import json
import pathlib
import sys

title_file, body_file, state = sys.argv[1:4]
payload = {}
if title_file:
    payload["title"] = pathlib.Path(title_file).read_text(encoding="utf-8").strip()
if body_file:
    payload["body"] = pathlib.Path(body_file).read_text(encoding="utf-8")
if state:
    payload["state"] = state
print(json.dumps(payload, ensure_ascii=False))
PY
}

if [[ -n "$COMMENT_FILE" ]]; then
  api POST "/issues/${ISSUE_NUMBER}/comments" "$(cat "$COMMENT_FILE" | json_from_stdin_as_comment)"
fi

if [[ -n "$TITLE_FILE" || -n "$BODY_FILE" || -n "$STATE" ]]; then
  api PATCH "/issues/${ISSUE_NUMBER}" "$(build_issue_patch)"
fi

printf 'Done.\n'
printf 'Issue: #%s\n' "$ISSUE_NUMBER"
printf 'Repo: %s/%s\n' "$OWNER" "$REPO"
