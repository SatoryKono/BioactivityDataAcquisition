#!/usr/bin/env bash

set -euo pipefail
if ! command -v coderabbit >/dev/null; then
  export PATH="$HOME/.local/bin:$PATH"
fi

BASE_COMMIT="${CODERABBIT_BASE_COMMIT:-}"
RUN_CODERABBIT_ONLY=0
LOG_DIR="${CODERABBIT_REVIEW_LOG_DIR:-}"
PREFLIGHT_ONLY=0
PREFLIGHT_DONE=0
REVIEW_ARGS=()
TOPIC="all"
if [[ $# -gt 0 && "$1" != --* ]]; then
  TOPIC="$1"
  shift
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/reports/quality/coderabbit/local}"

usage() {
  cat <<'EOF'
Usage:
  run-coderabbit-reviews.sh [topic] [--coderabbit-only] [--base <commit>] [--log-dir <path>]
                          [--preflight] [--uncommitted] [--dir <directory>]

Topics:
  1) architecture-boundaries
  2) adapters-resilience
  3) pipelines-determinism
  4) security
  5) contracts-docs-drift
  all) all five reviews in sequence
  changes) one diff review without additional test commands

Environment:
  Root .env is read as data (never sourced or changed); its non-empty
  CODERABBIT_API_KEY takes precedence over the process environment.
  CODERABBIT_API_KEY (optional when `coderabbit auth login` credentials are cached)
  BIOETL_CODERABBIT_PYTHON (optional Python with python-dotenv installed)

Examples:
  ./scripts/ops/run-coderabbit-reviews.sh 1
  ./scripts/ops/run-coderabbit-reviews.sh 5 --base origin/main
EOF
}

run_cmd() {
  local label="$1"
  shift
  echo
  echo "===> $label"
  "$@"
}

ensure_base() {
  if [[ -n "$BASE_COMMIT" ]]; then
    local base_ref
    base_ref="$(git -C "$ROOT_DIR" rev-parse -q --verify "$BASE_COMMIT^{commit}" 2>/dev/null || true)"
    if [[ -n "$base_ref" ]]; then
      BASE_COMMIT="$base_ref"
    else
      echo "[ERROR] Unknown base commit: $BASE_COMMIT" >&2
      return 1
    fi
    return
  fi

  if git -C "$ROOT_DIR" rev-parse --verify origin/main >/dev/null 2>&1; then
    BASE_COMMIT="$(git -C "$ROOT_DIR" merge-base HEAD origin/main)"
    return
  fi

  if git -C "$ROOT_DIR" rev-parse --verify main >/dev/null 2>&1; then
    BASE_COMMIT="$(git -C "$ROOT_DIR" merge-base HEAD main)"
    return
  fi

  BASE_COMMIT="HEAD~1"
}

ensure_coderabbit_auth() {
  if [[ -n "${CODERABBIT_API_KEY:-}" ]]; then
    run_cmd "CodeRabbit auth/login" coderabbit auth login --api-key "$CODERABBIT_API_KEY" || return 1
    return 0
  fi

  # A prior `coderabbit auth login` persists credentials in ~/.coderabbit/auth.json,
  # so an unset key is not by itself a failure.
  if run_cmd "CodeRabbit auth/status" coderabbit auth status --agent; then
    return 0
  fi

  echo "[ERROR] No CodeRabbit credentials: export CODERABBIT_API_KEY or run 'coderabbit auth login'" >&2
  return 1
}

preflight() {
  [[ "$PREFLIGHT_DONE" -eq 0 ]] || return 0
  cd "$ROOT_DIR"
  command -v coderabbit >/dev/null || {
    echo "[ERROR] coderabbit CLI not installed. Install with: curl -fsSL https://cli.coderabbit.ai/install.sh | sh" >&2
    return 1
  }

  if [[ -f "$ROOT_DIR/.env" ]]; then
    local python_bin="${BIOETL_CODERABBIT_PYTHON:-${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python}"
    [[ -x "$python_bin" ]] || python_bin=python3
    local root_key
    root_key="$("$python_bin" -B -c 'import sys; from dotenv import dotenv_values; print(dotenv_values(sys.argv[1], interpolate=False).get("CODERABBIT_API_KEY") or "", end="")' "$ROOT_DIR/.env")" || return 1
    if [[ -n "$root_key" ]]; then
      export CODERABBIT_API_KEY="$root_key"
    fi
  fi
  mkdir -p "$LOG_DIR"
  run_cmd "CodeRabbit version" coderabbit --version
  ensure_coderabbit_auth 2>&1 | tee "$LOG_DIR/auth.log" >&2
  run_cmd "CodeRabbit connectivity" coderabbit doctor 2>&1 | tee "$LOG_DIR/doctor.log"
  run_cmd "CodeRabbit configuration" coderabbit config validate "$ROOT_DIR/.coderabbit.yaml" 2>&1 | tee "$LOG_DIR/config.log"
  PREFLIGHT_DONE=1
}

run_coderabbit() {
  preflight
  local log_file="$LOG_DIR/coderabbit-${TOPIC}-$(date -u +%Y%m%d-%H%M%S)-$$.jsonl"
  printf '%s\n' "$BASE_COMMIT" > "${log_file%.jsonl}.base"
  git -C "$ROOT_DIR" rev-parse HEAD > "${log_file%.jsonl}.head"
  git -C "$ROOT_DIR" status --short > "${log_file%.jsonl}.status"
  git -C "$ROOT_DIR" diff --binary "$BASE_COMMIT" -- > "${log_file%.jsonl}.diff"

  echo "CodeRabbit diff against $BASE_COMMIT; output: $log_file"
  coderabbit review --agent --base-commit="$BASE_COMMIT" "${REVIEW_ARGS[@]}" \
    -c "$ROOT_DIR/AGENTS.md" "$ROOT_DIR/.coderabbit.yaml" \
    2> >(tee "${log_file%.jsonl}.stderr" >&2) | tee "$log_file"
  python3 - "$log_file" <<'PY'
import json
import sys

complete = False
count = 0
with open(sys.argv[1], encoding="utf-8") as stream:
    for line in stream:
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("type") == "error":
            raise SystemExit("CodeRabbit returned an error; inspect the review log.")
        if event.get("type") == "finding":
            count += 1
        if event.get("type") == "complete":
            if event.get("status") == "review_skipped":
                raise SystemExit("CodeRabbit skipped this scope; no audit completed.")
            complete = True
if not complete:
    raise SystemExit("CodeRabbit returned no complete event; review is incomplete.")
print(f"CodeRabbit raised {count} issues.")
PY
}

review_architecture() {
  TOPIC="1-architecture-boundaries"
  run_coderabbit
  if [[ "$RUN_CODERABBIT_ONLY" -eq 1 ]]; then
    return 0
  fi
  run_cmd "Make QA architecture fast" bash -lc "cd '$ROOT_DIR' && make qa-arch-fast"
  run_cmd "Architecture guardrails subset" bash -lc "cd '$ROOT_DIR' && python3 -m pytest tests/architecture/test_boundary_assertions.py tests/architecture/test_layer_matrix_guards.py tests/architecture/test_import_linter_workflow.py -q"
}

review_adapters() {
  TOPIC="2-adapters-resilience"
  run_coderabbit
  if [[ "$RUN_CODERABBIT_ONLY" -eq 1 ]]; then
    return 0
  fi
  run_cmd "Adapters suite" bash -lc "cd '$ROOT_DIR' && python3 -m pytest tests/architecture/test_adapter_contracts.py tests/architecture/test_adapter_http_client_enforcement.py tests/architecture/test_adapter_port_conformance.py tests/architecture/test_no_inline_construction_in_adapters.py -q"
}

review_pipelines() {
  TOPIC="3-pipelines-determinism"
  run_coderabbit
  if [[ "$RUN_CODERABBIT_ONLY" -eq 1 ]]; then
    return 0
  fi
  run_cmd "Pipeline determinism + config ownership + idempotency" bash -lc "cd '$ROOT_DIR' && python3 -m pytest tests/architecture/test_reproducibility_config_policy.py tests/architecture/test_pipeline_config_contract_ownership_map_integrity.py tests/architecture/test_pipeline_config_contract_ownership_map_drift.py tests/architecture/test_pipeline_config_idempotency_contract.py -q"
}

review_security() {
  TOPIC="4-security"
  run_coderabbit
  if [[ "$RUN_CODERABBIT_ONLY" -eq 1 ]]; then
    return 0
  fi
  run_cmd "Make security lane" bash -lc "cd '$ROOT_DIR' && make security-check"
  run_cmd "Security architecture subset" bash -lc "cd '$ROOT_DIR' && python3 -m pytest tests/architecture/test_security_suite_coverage.py tests/security/ -q"
}

review_contracts_docs() {
  TOPIC="5-contracts-docs-drift"
  run_coderabbit
  if [[ "$RUN_CODERABBIT_ONLY" -eq 1 ]]; then
    return 0
  fi
  run_cmd "Regenerate docs cleanup inventory" bash -lc "cd '$ROOT_DIR' && python3 -m scripts.docs generate-cleanup-inventory --update"
  run_cmd "Docs and spec drift" bash -lc "cd '$ROOT_DIR' && python3 -m scripts.docs check-drift --ports --classes --configs"
  run_cmd "Docs links/spec/config checks" bash -lc "cd '$ROOT_DIR' && python3 -m scripts.docs check-links --links --specs --configs"
  run_cmd "Docs cleanup tests" bash -lc "cd '$ROOT_DIR' && python3 -m pytest tests/architecture/test_documentation_cleanup_inventory.py tests/architecture/test_documentation_sync.py -q"
}

run_all_reviews() {
  review_architecture
  review_adapters
  review_pipelines
  review_security
  review_contracts_docs
}

if [[ "$TOPIC" == "-h" || "$TOPIC" == "--help" ]]; then
  usage
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --coderabbit-only)
      RUN_CODERABBIT_ONLY=1
      ;;
    --preflight)
      PREFLIGHT_ONLY=1
      ;;
    --uncommitted)
      REVIEW_ARGS+=(--uncommitted)
      ;;
    --dir)
      if [[ $# -lt 2 || -z "$2" || "$2" == --* ]]; then
        echo "[ERROR] --dir requires a directory" >&2
        exit 1
      fi
      REVIEW_ARGS+=(--dir "$2")
      shift
      ;;
    --base)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --base requires argument" >&2
        usage
        exit 1
      fi
      BASE_COMMIT="$2"
      if [[ -z "$BASE_COMMIT" || "$BASE_COMMIT" == --* ]]; then
        echo "[ERROR] --base value cannot be empty" >&2
        usage
        exit 1
      fi
      shift
      ;;
    --base=*)
      BASE_COMMIT="${1#*=}"
      if [[ -z "$BASE_COMMIT" || "$BASE_COMMIT" == --* ]]; then
        echo "[ERROR] --base value cannot be empty" >&2
        usage
        exit 1
      fi
      ;;
    --log-dir)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --log-dir requires argument" >&2
        usage
        exit 1
      fi
      LOG_DIR="$2"
      if [[ -z "$LOG_DIR" || "$LOG_DIR" == --* ]]; then
        echo "[ERROR] --log-dir value cannot be empty" >&2
        usage
        exit 1
      fi
      shift
      ;;
    --log-dir=*)
      LOG_DIR="${1#*=}"
      if [[ -z "$LOG_DIR" || "$LOG_DIR" == --* ]]; then
        echo "[ERROR] --log-dir value cannot be empty" >&2
        usage
        exit 1
      fi
      ;;
    *)
      echo "[ERROR] Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

if [[ "$PREFLIGHT_ONLY" -eq 1 ]]; then
  preflight
  exit 0
fi

ensure_base

case "$TOPIC" in
  changes)
    run_coderabbit
    ;;
  1|architecture|architecture-boundaries)
    review_architecture
    ;;
  2|adapters|adapters-resilience)
    review_adapters
    ;;
  3|pipelines|pipelines-determinism)
    review_pipelines
    ;;
  4|security)
    review_security
    ;;
  5|contracts-docs-drift)
    review_contracts_docs
    ;;
  all)
    run_all_reviews
    ;;
  *)
    echo "[ERROR] Unknown topic: $TOPIC" >&2
    usage
    exit 1
    ;;
esac

echo
echo "Done: $TOPIC"
