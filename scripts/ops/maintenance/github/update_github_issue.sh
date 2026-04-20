#!/usr/bin/env bash
set -euo pipefail

DEFAULT_OWNER="SatoryKono"
DEFAULT_REPO="BioactivityDataAcquisition"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/maintenance/update_github_issue.sh --issue NUMBER [options]

Options:
  --issue NUMBER         GitHub issue number to update (required)
  --title TEXT           Set updated title directly from CLI text
  --title-file PATH      Read updated title from file
  --body TEXT            Set updated body directly from CLI text
  --body-file PATH       Read updated body from file
  --comment TEXT         Post a comment directly from CLI text
  --comment-file PATH    Post a comment from file contents
  --state STATE          Patch issue state: open | closed
  --owner NAME           Repository owner (default: SatoryKono)
  --repo NAME            Repository name (default: BioactivityDataAcquisition)
  --dry-run              Print API operations without sending them
  -h, --help             Show this help

Environment:
  GITHUB_PERSONAL_ACCESS_TOKEN   Preferred fine-grained or classic token with issue write access
  GH_TOKEN                       Alternative token env var
  GITHUB_TOKEN                   Alternative token env var

Examples:
  bash scripts/ops/maintenance/update_github_issue.sh \
    --issue 2594 \
    --comment "Schema drift gate implemented" \
    --state closed

  bash scripts/ops/maintenance/update_github_issue.sh \
    --issue 2594 \
    --comment-file /tmp/comment.md \
    --state closed

  bash scripts/ops/maintenance/update_github_issue.sh \
    --issue 2511 \
    --title-file /tmp/title.txt \
    --body-file /tmp/body.md
EOF
  return 0
}

OWNER="$DEFAULT_OWNER"
REPO="$DEFAULT_REPO"
ISSUE_NUMBER=""
TITLE_TEXT=""
TITLE_FILE=""
BODY_TEXT=""
BODY_FILE=""
COMMENT_TEXT=""
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
    --title)
      TITLE_TEXT="${2:-}"
      shift 2
      ;;
    --body-file)
      BODY_FILE="${2:-}"
      shift 2
      ;;
    --body)
      BODY_TEXT="${2:-}"
      shift 2
      ;;
    --comment-file)
      COMMENT_FILE="${2:-}"
      shift 2
      ;;
    --comment)
      COMMENT_TEXT="${2:-}"
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
if [[ -n "$TITLE_TEXT" && -n "$TITLE_FILE" ]]; then
  printf 'Use only one of --title or --title-file\n' >&2
  exit 2
fi
if [[ -n "$BODY_FILE" && ! -f "$BODY_FILE" ]]; then
  printf 'Body file not found: %s\n' "$BODY_FILE" >&2
  exit 2
fi
if [[ -n "$BODY_TEXT" && -n "$BODY_FILE" ]]; then
  printf 'Use only one of --body or --body-file\n' >&2
  exit 2
fi
if [[ -n "$COMMENT_FILE" && ! -f "$COMMENT_FILE" ]]; then
  printf 'Comment file not found: %s\n' "$COMMENT_FILE" >&2
  exit 2
fi
if [[ -n "$COMMENT_TEXT" && -n "$COMMENT_FILE" ]]; then
  printf 'Use only one of --comment or --comment-file\n' >&2
  exit 2
fi

if [[ -z "$TITLE_TEXT" && -z "$TITLE_FILE" && -z "$BODY_TEXT" && -z "$BODY_FILE" && -z "$COMMENT_TEXT" && -z "$COMMENT_FILE" && -z "$STATE" ]]; then
  printf 'Nothing to do: provide at least one of --title, --title-file, --body, --body-file, --comment, --comment-file, or --state\n' >&2
  exit 2
fi

resolve_auth_token() {
  if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
    printf '%s' "${GITHUB_PERSONAL_ACCESS_TOKEN}"
    return 0
  fi
  if [[ -n "${GH_TOKEN:-}" ]]; then
    printf '%s' "${GH_TOKEN}"
    return 0
  fi
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    printf '%s' "${GITHUB_TOKEN}"
    return 0
  fi
  return 1
}

if ! AUTH_TOKEN="$(resolve_auth_token)"; then
  printf '%s\n' \
    'Missing GitHub token. Set one of: GITHUB_PERSONAL_ACCESS_TOKEN, GH_TOKEN, GITHUB_TOKEN' >&2
  exit 1
fi

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

  local response_file
  response_file="$(mktemp)"
  local http_code=""
  trap 'rm -f "$response_file"' RETURN

  if [[ -n "$data" ]]; then
    http_code="$(
      curl -sS -o "$response_file" -w "%{http_code}" -X "$method" \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        -H "Content-Type: application/json" \
        "${API}${path}" \
        --data "$data"
    )"
  else
    http_code="$(
      curl -sS -o "$response_file" -w "%{http_code}" -X "$method" \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "${API}${path}"
    )"
  fi

  if [[ "$http_code" -lt 200 || "$http_code" -ge 300 ]]; then
    printf '[FAIL] GitHub API %s %s returned HTTP %s\n' "$method" "$path" "$http_code" >&2
    if [[ -s "$response_file" ]]; then
      cat "$response_file" >&2
      printf '\n' >&2
    fi
    if [[ "$http_code" == "401" ]]; then
      printf '%s\n' \
        'Authentication failed. Check that the token is valid and has issue write access to the target repository.' >&2
    fi
    if [[ "$http_code" == "403" ]]; then
      printf '%s\n' \
        'Authorization failed. The token may be missing Issues:write / Repository issues permissions or be blocked by repo policy.' >&2
    fi
    if [[ "$http_code" == "404" ]]; then
      printf '%s\n' \
        'Resource not found. Check owner/repo/issue number and confirm the token can access this repository.' >&2
    fi
    exit 1
  fi
  return 0
}

json_from_stdin_as_comment() {
  python3 -c 'import json, sys; print(json.dumps({"body": sys.stdin.read()}, ensure_ascii=True))'
  return 0
}

build_issue_patch() {
  python3 - "$TITLE_TEXT" "$TITLE_FILE" "$BODY_TEXT" "$BODY_FILE" "$STATE" <<'PY'
import json
import pathlib
import sys

title_text, title_file, body_text, body_file, state = sys.argv[1:6]
payload = {}
if title_text:
    payload["title"] = title_text
elif title_file:
    payload["title"] = pathlib.Path(title_file).read_text(encoding="utf-8").strip()
if body_text:
    payload["body"] = body_text
elif body_file:
    payload["body"] = pathlib.Path(body_file).read_text(encoding="utf-8")
if state:
    payload["state"] = state
print(json.dumps(payload, ensure_ascii=True))
PY
  return 0
}

if [[ -n "$COMMENT_TEXT" ]]; then
  comment_payload="$(printf '%s' "$COMMENT_TEXT" | json_from_stdin_as_comment)"
  api POST "/issues/${ISSUE_NUMBER}/comments" "$comment_payload"
elif [[ -n "$COMMENT_FILE" ]]; then
  comment_payload="$(cat "$COMMENT_FILE" | json_from_stdin_as_comment)"
  api POST "/issues/${ISSUE_NUMBER}/comments" "$comment_payload"
fi

if [[ -n "$TITLE_TEXT" || -n "$TITLE_FILE" || -n "$BODY_TEXT" || -n "$BODY_FILE" || -n "$STATE" ]]; then
  issue_patch="$(build_issue_patch)"
  api PATCH "/issues/${ISSUE_NUMBER}" "$issue_patch"
fi

printf 'Done.\n'
printf 'Issue: #%s\n' "$ISSUE_NUMBER"
printf 'Repo: %s/%s\n' "$OWNER" "$REPO"
