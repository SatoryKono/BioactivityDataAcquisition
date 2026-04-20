#!/usr/bin/env bash
# Close superseded pull requests after opening a consolidated PR.
# Default mode is dry-run; use --execute to perform changes.

set -euo pipefail

REPO="SatoryKono/BioactivityDataAcquisition"
NEW_PR=""
EXECUTE=0
TARGET_PRS=(2430 2431 2432 2436)

usage() {
  cat <<'EOF'
Usage:
  bash scripts/close_superseded_prs.sh --new-pr <PR_NUMBER> [options]

Options:
  --new-pr <number>         Consolidated PR number (required).
  --repo <owner/repo>       Repository slug (default: SatoryKono/BioactivityDataAcquisition).
  --prs "<list>"            Space-separated PR numbers to close.
                            Default: "2430 2431 2432 2436"
  --execute                 Actually close PRs (default is dry-run).
  -h, --help                Show this help.

Examples:
  bash scripts/close_superseded_prs.sh --new-pr 2440
  bash scripts/close_superseded_prs.sh --new-pr 2440 --execute
  bash scripts/close_superseded_prs.sh --new-pr 2440 --prs "2430 2431 2432 2436 2441" --execute
EOF
  return 0
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $cmd" >&2
    exit 1
  fi
  return 0
}

parse_args() {
  local arg=""
  while [[ $# -gt 0 ]]; do
    arg="$1"
    case "$arg" in
      --new-pr)
        NEW_PR="${2:-}"
        shift 2
        ;;
      --repo)
        REPO="${2:-}"
        shift 2
        ;;
      --prs)
        IFS=' ' read -r -a TARGET_PRS <<< "${2:-}"
        shift 2
        ;;
      --execute)
        EXECUTE=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "ERROR: unknown argument: $arg" >&2
        usage
        exit 1
        ;;
    esac
  done
  return 0
}

validate_inputs() {
  if [[ -z "$NEW_PR" ]]; then
    echo "ERROR: --new-pr is required." >&2
    usage
    exit 1
  fi

  if ! [[ "$NEW_PR" =~ ^[0-9]+$ ]]; then
    echo "ERROR: --new-pr must be numeric, got: $NEW_PR" >&2
    exit 1
  fi

  if [[ "${#TARGET_PRS[@]}" -eq 0 ]]; then
    echo "ERROR: target PR list is empty." >&2
    exit 1
  fi
  return 0
}

print_plan() {
  echo "Repository: $REPO"
  echo "Consolidated PR: #$NEW_PR"
  echo "Target PRs: ${TARGET_PRS[*]}"
  if [[ "$EXECUTE" -eq 1 ]]; then
    echo "Mode: EXECUTE"
  else
    echo "Mode: DRY-RUN"
  fi
  echo
  return 0
}

run() {
  local pr comment
  comment="Superseded by #${NEW_PR} (consolidation/wave1-3)."

  for pr in "${TARGET_PRS[@]}"; do
    if ! [[ "$pr" =~ ^[0-9]+$ ]]; then
      echo "SKIP: invalid PR number '$pr'"
      continue
    fi

    if [[ "$pr" == "$NEW_PR" ]]; then
      echo "SKIP: #$pr matches --new-pr."
      continue
    fi

    if [[ "$EXECUTE" -eq 1 ]]; then
      echo "Closing #$pr..."
      gh pr close "$pr" --repo "$REPO" --comment "$comment"
    else
      echo "[DRY-RUN] gh pr close $pr --repo $REPO --comment \"$comment\""
    fi
  done
  return 0
}

main() {
  parse_args "$@"
  validate_inputs
  require_cmd gh

  if ! gh auth status >/dev/null 2>&1; then
    echo "ERROR: gh is not authenticated. Run: gh auth login" >&2
    exit 1
  fi

  print_plan
  run

  if [[ "$EXECUTE" -eq 1 ]]; then
    echo
    echo "Done. Open PRs now:"
    gh pr list --repo "$REPO" --state open
  else
    echo
    echo "Dry-run finished. Re-run with --execute to apply."
  fi
  return 0
}

main "$@"
