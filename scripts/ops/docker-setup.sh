#!/usr/bin/env bash
# Compatibility adapter for the canonical fail-closed Docker runtime manager.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
manager="${repo_root}/scripts/ops/runtime/docker/runtime_manager.py"
python_bin="${BIOETL_PYTHON:-}"

if [[ -z "${python_bin}" ]]; then
  python_bin="$(command -v python3 || command -v python || true)"
fi
if [[ -z "${python_bin}" ]]; then
  printf 'Python is required for Docker lifecycle management.\n' >&2
  exit 127
fi

run_manager() {
  "${python_bin}" "${manager}" "$@"
}

run_for_stacks() {
  local action="$1"
  shift
  local stack status=0
  for stack in "$@"; do
    if ! run_manager "${action}" --stack "${stack}"; then
      status=1
    fi
  done
  return "${status}"
}

usage() {
  cat <<'EOF'
Usage: scripts/ops/docker-setup.sh <command> [argument]

Commands:
  check [stack]       Read-only preflight (default: main)
  start|basic         Start and verify main
  recover [stack]     Bounded recovery (default: main)
  start-full|full     Start all maintained helper stacks
  monitoring          Start and verify monitoring
  stop [stack]        Stop without deleting volumes (default: main)
  stop-full           Stop all maintained helper stacks without deleting volumes
  status|health       Structured main-stack readiness
  diagnose [stack]    Write a redacted diagnostic report
  logs [stack]        Print bounded recent logs
  clean [stack] CLEAN Explicit bounded cleanup; volumes/images are retained
EOF
}

command="${1:-help}"
argument="${2:-}"
case "${command}" in
  check|recover|stop|status|diagnose|logs)
    run_manager "${command}" --stack "${argument:-main}"
    ;;
  health)
    run_manager status --stack main
    ;;
  start|basic)
    run_manager start --stack main
    ;;
  monitoring)
    run_manager start --stack monitoring
    ;;
  start-full|full)
    run_for_stacks start main neo4j redis minio monitoring
    ;;
  stop-full)
    run_for_stacks stop monitoring minio redis neo4j main
    ;;
  clean)
    run_manager clean --stack "${argument:-main}" --confirm-destructive "${3:-}"
    ;;
  help|--help|-h|"")
    usage
    ;;
  *)
    printf 'Unknown command: %s\n' "${command}" >&2
    usage >&2
    exit 2
    ;;
esac
