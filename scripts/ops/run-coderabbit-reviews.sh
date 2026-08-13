#!/usr/bin/env bash

set -euo pipefail

BASE_COMMIT="${CODERABBIT_BASE_COMMIT:-}"
RUN_CODERABBIT_ONLY=0
LOG_DIR="${CODERABBIT_REVIEW_LOG_DIR:-/tmp/coderabbit-reviews}"
TOPIC="all"
if [[ $# -gt 0 && "$1" != --* ]]; then
  TOPIC="$1"
  shift
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

usage() {
  cat <<'EOF'
Usage:
  run-coderabbit-reviews.sh [topic] [--coderabbit-only] [--base <commit>] [--log-dir <path>]

Topics:
  1) architecture-boundaries
  2) adapters-resilience
  3) pipelines-determinism
  4) security
  5) contracts-docs-drift
  all) all five reviews in sequence

Environment:
  CODERABBIT_API_KEY (optional when `coderabbit auth login` credentials are cached)

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
    run_cmd "CodeRabbit auth/login" coderabbit auth login --api-key "$CODERABBIT_API_KEY"
    return 0
  fi

  # A prior `coderabbit auth login` persists credentials in ~/.coderabbit/auth.json,
  # so an unset key is not by itself a failure.
  if run_cmd "CodeRabbit auth/status" coderabbit auth status; then
    return 0
  fi

  echo "[ERROR] No CodeRabbit credentials: export CODERABBIT_API_KEY or run 'coderabbit auth login'" >&2
  return 1
}

run_coderabbit() {
  command -v coderabbit >/dev/null || {
    echo "[ERROR] coderabbit CLI not installed. Install with: curl -fsSL https://cli.coderabbit.ai/install.sh | sh" >&2
    return 1
  }

  ensure_coderabbit_auth || return 1

  mkdir -p "$LOG_DIR"
  local log_file="$LOG_DIR/coderabbit-${TOPIC}-$(date +%Y%m%d-%H%M%S).log"

  run_cmd "CodeRabbit review against $BASE_COMMIT" coderabbit review --base-commit="$BASE_COMMIT" | tee "$log_file"
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

ensure_base

case "$TOPIC" in
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
