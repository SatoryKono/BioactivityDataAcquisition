#!/usr/bin/env bash
# Close known duplicate PRs with explicit superseded mapping.
# Default mode is dry-run; pass --execute to apply.

set -euo pipefail

REPO="SatoryKono/BioactivityDataAcquisition"
EXECUTE=0

usage() {
  cat <<'EOF'
Usage:
  bash scripts/close_duplicate_prs_wave2.sh [--execute] [--repo <owner/repo>]

Options:
  --execute                 Actually close PRs (default is dry-run).
  --repo <owner/repo>       Repository slug (default: SatoryKono/BioactivityDataAcquisition).
  -h, --help                Show this help.

Mapping used by this script:
  #2398 -> superseded by #2423
  #2412 #2413 #2414 #2415 #2416 #2417 #2391 #2392 #2393 #2395 #2400 #2401 #2402 -> superseded by #2422
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
      --execute)
        EXECUTE=1
        shift
        ;;
      --repo)
        REPO="${2:-}"
        shift 2
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

pr_status() {
  local pr="$1"
  gh pr view "$pr" --repo "$REPO" --json state,mergedAt --jq '.state + "|" + (if .mergedAt then "merged" else "not_merged" end)' 2>/dev/null || echo "UNKNOWN|unknown"
  return 0
}

process_pr() {
  local pr="$1"
  local superseded_by="$2"
  local comment status state merge_flag

  comment="Superseded by #${superseded_by}."
  status="$(pr_status "$pr")"
  state="${status%%|*}"
  merge_flag="${status##*|}"

  if [[ "$merge_flag" == "merged" ]]; then
    echo "SKIP #$pr: already merged."
    return 0
  fi

  if [[ "$state" == "CLOSED" ]]; then
    echo "SKIP #$pr: already closed."
    return 0
  fi

  if [[ "$state" != "OPEN" ]]; then
    echo "SKIP #$pr: state unknown/unavailable."
    return 0
  fi

  if [[ "$EXECUTE" -eq 1 ]]; then
    echo "Closing #$pr (superseded by #$superseded_by)..."
    gh pr close "$pr" --repo "$REPO" --comment "$comment"
  else
    echo "[DRY-RUN] gh pr close $pr --repo $REPO --comment \"$comment\""
  fi
  return 0
}

main() {
  parse_args "$@"
  require_cmd gh

  if ! gh auth status >/dev/null 2>&1; then
    echo "ERROR: gh is not authenticated. Run: gh auth login" >&2
    exit 1
  fi

  local -a superseded_by_2423=(2398)
  local -a superseded_by_2422=(2412 2413 2414 2415 2416 2417 2391 2392 2393 2395 2400 2401 2402)

  echo "Repository: $REPO"
  if [[ "$EXECUTE" -eq 1 ]]; then
    echo "Mode: EXECUTE"
  else
    echo "Mode: DRY-RUN"
  fi
  echo

  echo "Group A: superseded by #2423"
  for pr in "${superseded_by_2423[@]}"; do
    process_pr "$pr" 2423
  done

  echo
  echo "Group B: superseded by #2422"
  for pr in "${superseded_by_2422[@]}"; do
    process_pr "$pr" 2422
  done

  echo
  if [[ "$EXECUTE" -eq 1 ]]; then
    echo "Done. Current open PRs:"
    gh pr list --repo "$REPO" --state open
  else
    echo "Dry-run finished. Re-run with --execute to apply."
  fi
}

main "$@"
