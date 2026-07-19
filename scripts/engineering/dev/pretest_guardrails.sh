#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CONFIG_PATH="$REPO_ROOT/configs/quality/pretest_guardrails.yaml"
cd "$REPO_ROOT"

MODE="check"
SCOPE="light"
STRICT_DOCS=0
SKIP_CLEANUP=0
SKIP_REPO=0
SKIP_DOCS=0
SKIP_ARCHITECTURE=0
SKIP_MEMORY=0
DRY_RUN=0
REPORT_JSON=""
RUN_CLEANUP=1
RUN_AUTO_FIX=1
RUN_REPO_CHECKS=1
RUN_DOCS_IDENTITY_CHECKS=1
RUN_DOCS_VERIFY=0
RUN_MEMORY_CHECKS=1
ARCHITECTURE_GROUP=""
PYTHON_BIN=""
STEP_LOG_FILE=""
SESSION_STATUS="ok"
PRETEST_START_TS=""
MEMORY_TMP_OUTPUT=""

usage() {
    cat <<'EOF'
Usage:
  bash scripts/engineering/dev/pretest_guardrails.sh [options]

Purpose:
  Run the repository preflight that catches common docs/governance/
  architecture regressions before the full pytest suite starts.

Options:
  --mode auto|check             auto: refresh deterministic repo metadata before checks
                                check: validate only (default)
  --scope light|governance|full|strict
                                light: cleanup + repo sync/check + targeted doc/policy drift checks
                                governance: light + governance guardrails
                                full: governance + docs verify --skip-build + full architecture fail-fast
                                strict: full + strict docs build
  --strict-docs                 Force strict docs verification regardless of profile
  --skip-cleanup                Skip cache/build artifact cleanup
  --skip-repo                   Skip inventory/catalog governance checks
  --skip-docs                   Skip docs identity + docs verification
  --skip-architecture           Skip targeted architecture fail-fast checks
  --skip-memory                 Skip memory validation + refresh smoke checks
  --report-json PATH            Write machine-readable summary to PATH
  --dry-run                     Print commands without executing them
  -h, --help                    Show this help
EOF
    return 0
}

require_python() {
    if [[ -n "$PYTHON_BIN" ]]; then
        printf '%s\n' "$PYTHON_BIN"
        return 0
    fi
    if [[ -n "${BIOETL_PYTEST_RUNTIME_PYTHON:-}" && -x "${BIOETL_PYTEST_RUNTIME_PYTHON:-}" ]]; then
        PYTHON_BIN="$BIOETL_PYTEST_RUNTIME_PYTHON"
        printf '%s\n' "$PYTHON_BIN"
        return 0
    fi
    if [[ -x "${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" ]]; then
        PYTHON_BIN="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python"
        printf '%s\n' "$PYTHON_BIN"
        return 0
    fi
    if [[ -x ".venv/bin/python" ]]; then
        PYTHON_BIN=".venv/bin/python"
        printf '%s\n' "$PYTHON_BIN"
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
        printf '%s\n' "$PYTHON_BIN"
        return 0
    fi
    if command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
        printf '%s\n' "$PYTHON_BIN"
        return 0
    fi
    echo "[pretest-guardrails][error] Python runtime is not available." >&2
    return 1
}

record_step() {
    local label="$1"
    local status="$2"
    local duration_seconds="$3"
    local command_text="$4"
    printf '%s\t%s\t%s\t%s\n' "$label" "$status" "$duration_seconds" "$command_text" >>"$STEP_LOG_FILE"
    return 0
}

run_step() {
    local label="$1"
    shift

    printf '[pretest-guardrails] %s: ' "$label"
    printf '%q ' "$@"
    printf '\n'

    local started ended duration command_text
    started="$("$PYTHON_BIN" -c 'import time; print(time.time())')"
    command_text="$(printf '%q ' "$@")"

    if [[ "$DRY_RUN" == "1" ]]; then
        record_step "$label" "dry-run" "0.0" "$command_text"
        return 0
    fi

    if "$@"; then
        ended="$("$PYTHON_BIN" -c 'import time; print(time.time())')"
        duration="$("$PYTHON_BIN" - "$started" "$ended" <<'PY'
import sys
start = float(sys.argv[1])
end = float(sys.argv[2])
print(f"{end - start:.3f}")
PY
)"
        record_step "$label" "ok" "$duration" "$command_text"
        return 0
    fi

    ended="$("$PYTHON_BIN" -c 'import time; print(time.time())')"
    duration="$("$PYTHON_BIN" - "$started" "$ended" <<'PY'
import sys
start = float(sys.argv[1])
end = float(sys.argv[2])
print(f"{end - start:.3f}")
PY
)"
    record_step "$label" "failed" "$duration" "$command_text"
    SESSION_STATUS="failed"
    return 1
}

config_profile_value() {
    local profile="$1"
    local key="$2"
    "$PYTHON_BIN" - "$CONFIG_PATH" "$profile" "$key" <<'PY'
from pathlib import Path
import sys
import yaml

config_path = Path(sys.argv[1])
profile = sys.argv[2]
key = sys.argv[3]
data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
profiles = data.get("profiles", {})
profile_data = profiles.get(profile, {})
value = profile_data.get(key, "")
if isinstance(value, bool):
    print("1" if value else "0")
else:
    print(value)
PY
    return 0
}

config_architecture_targets() {
    local group="$1"
    [[ -n "$group" ]] || return 0
    "$PYTHON_BIN" - "$CONFIG_PATH" "$group" <<'PY'
from pathlib import Path
import sys
import yaml

config_path = Path(sys.argv[1])
group = sys.argv[2]
data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
for item in data.get("architecture_groups", {}).get(group, []):
    print(item)
PY
}

write_report() {
    local report_path="$REPORT_JSON"
    [[ -n "$PYTHON_BIN" ]] || PYTHON_BIN="$(require_python || true)"
    [[ -n "$PYTHON_BIN" ]] || return 0

    if [[ -z "$report_path" ]]; then
        mkdir -p reports/quality
        report_path="reports/quality/pretest_guardrails_$(date -u +%Y%m%d_%H%M%S).json"
    fi

    mkdir -p "$(dirname "$report_path")"
    "$PYTHON_BIN" - "$STEP_LOG_FILE" "$report_path" "$MODE" "$SCOPE" "$SESSION_STATUS" "$PRETEST_START_TS" "$STRICT_DOCS" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import sys
from datetime import datetime, timezone

step_file = Path(sys.argv[1])
report_path = Path(sys.argv[2])
mode = sys.argv[3]
scope = sys.argv[4]
status = sys.argv[5]
started_at = sys.argv[6]
strict_docs = sys.argv[7] == "1"

steps = []
if step_file.exists():
    for line in step_file.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        label, step_status, duration_seconds, command = line.split("\t", 3)
        steps.append(
            {
                "label": label,
                "status": step_status,
                "duration_seconds": float(duration_seconds),
                "command": command.strip(),
            }
        )

payload = {
    "tool": "pretest_guardrails",
    "mode": mode,
    "scope": scope,
    "strict_docs": strict_docs,
    "status": status,
    "started_at": started_at,
    "completed_at": datetime.now(timezone.utc).isoformat(),
    "steps": steps,
    "auto_fixed": [step["label"] for step in steps if step["label"].endswith("-sync") and step["status"] == "ok"],
    "failed_steps": [step["label"] for step in steps if step["status"] == "failed"],
}

report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(f"[pretest-guardrails] report: {report_path}")
PY
}

cleanup_temp() {
    if [[ -n "$MEMORY_TMP_OUTPUT" && -d "$MEMORY_TMP_OUTPUT" ]]; then
        rm -rf "$MEMORY_TMP_OUTPUT"
    fi
    if [[ -n "$STEP_LOG_FILE" && -f "$STEP_LOG_FILE" ]]; then
        rm -f "$STEP_LOG_FILE"
    fi
    return 0
}

on_exit() {
    local rc="$1"
    if [[ "$rc" != "0" ]]; then
        SESSION_STATUS="failed"
    fi
    write_report
    cleanup_temp
    return 0
}

parse_args() {
    while (($# > 0)); do
        local arg="$1"
        case "$arg" in
            --mode)
                [[ $# -ge 2 ]] || {
                    echo "[pretest-guardrails][error] --mode requires a value" >&2
                    exit 2
                }
                MODE="$2"
                shift 2
                ;;
            --scope)
                [[ $# -ge 2 ]] || {
                    echo "[pretest-guardrails][error] --scope requires a value" >&2
                    exit 2
                }
                SCOPE="$2"
                shift 2
                ;;
            --strict-docs)
                STRICT_DOCS=1
                shift
                ;;
            --skip-cleanup)
                SKIP_CLEANUP=1
                shift
                ;;
            --skip-repo)
                SKIP_REPO=1
                shift
                ;;
            --skip-docs)
                SKIP_DOCS=1
                shift
                ;;
            --skip-architecture)
                SKIP_ARCHITECTURE=1
                shift
                ;;
            --skip-memory)
                SKIP_MEMORY=1
                shift
                ;;
            --report-json)
                [[ $# -ge 2 ]] || {
                    echo "[pretest-guardrails][error] --report-json requires a value" >&2
                    exit 2
                }
                REPORT_JSON="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                echo "[pretest-guardrails][error] Unknown argument: $arg" >&2
                usage >&2
                exit 2
                ;;
        esac
    done

    case "$MODE" in
        auto|check) ;;
        *)
            echo "[pretest-guardrails][error] Unsupported mode: $MODE" >&2
            exit 2
            ;;
    esac

    case "$SCOPE" in
        light|governance|full|strict) ;;
        *)
            echo "[pretest-guardrails][error] Unsupported scope: $SCOPE" >&2
            exit 2
            ;;
    esac
    return 0
}

load_profile() {
    PYTHON_BIN="$(require_python)"
    RUN_CLEANUP="$(config_profile_value "$SCOPE" "run_cleanup")"
    RUN_AUTO_FIX="$(config_profile_value "$SCOPE" "run_auto_fix")"
    RUN_REPO_CHECKS="$(config_profile_value "$SCOPE" "run_repo_checks")"
    RUN_DOCS_IDENTITY_CHECKS="$(config_profile_value "$SCOPE" "run_docs_identity_checks")"
    RUN_DOCS_VERIFY="$(config_profile_value "$SCOPE" "run_docs_verify")"
    RUN_MEMORY_CHECKS="$(config_profile_value "$SCOPE" "run_memory_checks")"
    ARCHITECTURE_GROUP="$(config_profile_value "$SCOPE" "architecture_group")"
    if [[ "$STRICT_DOCS" != "1" ]]; then
        STRICT_DOCS="$(config_profile_value "$SCOPE" "strict_docs")"
    fi
    return 0
}

run_cleanup() {
    [[ "$SKIP_CLEANUP" == "0" ]] || return 0
    [[ "$RUN_CLEANUP" == "1" ]] || return 0
    run_step cleanup env BIOETL_PREFLIGHT_PRESERVE_PYTEST_CACHE=1 bash scripts/engineering/repo/preflight_cleanup.sh
}

run_auto_fix() {
    [[ "$MODE" == "auto" ]] || return 0
    [[ "$RUN_AUTO_FIX" == "1" ]] || return 0

    echo "[pretest-guardrails][write] auto mode enabled; running repository metadata sync steps"
    run_step integration-vcr-policy-sync \
        "$PYTHON_BIN" -m scripts.engineering.qa sync-integration-vcr-policy --write
    run_step repo-identity-sync \
        "$PYTHON_BIN" -m scripts.docs sync-repo-identity --write
    # Keep inventory refresh last because upstream auto-fix steps may rewrite
    # tracked files that contribute script references.
    run_step inventory-sync \
        "$PYTHON_BIN" -m scripts.engineering.repo sync-inventory --write
    # Refresh the hotspot-family baseline after inventory sync because the
    # baseline report consumes inventory-derived metadata.
    run_step hotspot-family-baseline-sync \
        "$PYTHON_BIN" -m scripts.engineering.qa report-family-baseline \
        --update
}

run_repo_checks() {
    [[ "$SKIP_REPO" == "0" ]] || return 0
    [[ "$RUN_REPO_CHECKS" == "1" ]] || return 0

    if [[ "$MODE" == "auto" ]]; then
        # Ensure the inventory is completely up to date before running checks that depend on it.
        run_step inventory-sync-final "$PYTHON_BIN" -m scripts.engineering.repo sync-inventory --write
    fi

    # The inventory-check MUST be the final check for inventory consistency related to auto-fixes
    if ! run_step inventory-check \
        "$PYTHON_BIN" -m scripts.engineering.repo check-inventory \
        --check \
        --manifest configs/quality/scripts_inventory_manifest.json \
        --check-lifecycle \
        --forbid-evaluate-active \
        --lifecycle-registry configs/quality/scripts_lifecycle_registry.json
    then
        if [[ "$MODE" != "auto" ]]; then
            return 1
        fi

        echo "[pretest-guardrails] inventory drift persisted after sync; retrying once" >&2
        run_step inventory-sync-retry \
            "$PYTHON_BIN" -m scripts.engineering.repo sync-inventory --write || return 1
        run_step inventory-check-retry \
            "$PYTHON_BIN" -m scripts.engineering.repo check-inventory \
            --check \
            --manifest configs/quality/scripts_inventory_manifest.json \
            --check-lifecycle \
            --forbid-evaluate-active \
            --lifecycle-registry configs/quality/scripts_lifecycle_registry.json || return 1
    fi

    # Remaining checks can follow
    run_step catalog-check \
        "$PYTHON_BIN" -m scripts.engineering.repo check-catalog \
        --catalog scripts/engineering/repo/catalog.yaml

    if [[ "$MODE" != "auto" ]]; then
        run_step hotspot-family-baseline-check \
            "$PYTHON_BIN" -m scripts.engineering.qa report-family-baseline \
            --check
    fi
}

run_docs_identity_checks() {
    [[ "$SKIP_DOCS" == "0" ]] || return 0
    [[ "$RUN_DOCS_IDENTITY_CHECKS" == "1" ]] || return 0

    run_step repo-identity-check \
        "$PYTHON_BIN" -m scripts.docs sync-repo-identity --check
    run_step integration-vcr-policy-check \
        "$PYTHON_BIN" -m scripts.engineering.qa sync-integration-vcr-policy --check
}

run_docs_verify() {
    [[ "$SKIP_DOCS" == "0" ]] || return 0
    [[ "$RUN_DOCS_VERIFY" == "1" ]] || return 0

    local -a cmd=("$PYTHON_BIN" -m scripts.docs verify)
    if [[ "$STRICT_DOCS" != "1" ]]; then
        cmd+=(--skip-build)
    fi
    run_step docs-verify "${cmd[@]}"
}

run_memory_checks() {
    [[ "$SKIP_MEMORY" == "0" ]] || return 0
    [[ "$RUN_MEMORY_CHECKS" == "1" ]] || return 0

    run_step memory-validate \
        "$PYTHON_BIN" -m memory.tooling.validate

    run_step memory-workflow-smoke \
        "$PYTHON_BIN" -m memory.tooling.workflow smoke \
        --validation-timeout-seconds 15 \
        --json

    if [[ "$DRY_RUN" == "1" ]]; then
        MEMORY_TMP_OUTPUT="/tmp/bioetl-memory-refresh-dry-run"
    else
        MEMORY_TMP_OUTPUT="$(mktemp -d)"
    fi

    run_step memory-refresh-smoke \
        "$PYTHON_BIN" -m memory.tooling.refresh_all \
        --output-root "$MEMORY_TMP_OUTPUT" \
        --rag-build-scope full \
        --json

    run_step memory-rag-manifest-validate \
        "$PYTHON_BIN" -m memory.rag.validation \
        --root "$REPO_ROOT" \
        --manifest-dir "$MEMORY_TMP_OUTPUT/rag/manifests" \
        --require-build-scope full \
        --json

    run_step memory-prune-dry-run \
        "$PYTHON_BIN" -m memory.tooling.prune --json
}

run_architecture_checks() {
    [[ "$SKIP_ARCHITECTURE" == "0" ]] || return 0
    [[ -n "$ARCHITECTURE_GROUP" ]] || return 0

    mapfile -t architecture_targets < <(config_architecture_targets "$ARCHITECTURE_GROUP")
    [[ "${#architecture_targets[@]}" -gt 0 ]] || return 0

    local -a cmd=(
        bash scripts/engineering/dev/run_pytest.sh
        --skip-preflight
        --narrow
    )
    cmd+=("${architecture_targets[@]}")
    cmd+=(
        -q
        -x
        --tb=short
    )

    run_step architecture-fail-fast env \
        BIOETL_SKIP_PREFLIGHT=1 \
        BIOETL_PREFLIGHT_DONE=1 \
        "${cmd[@]}"
}

main() {
    parse_args "$@"
    load_profile
    STEP_LOG_FILE="$(mktemp)"
    PRETEST_START_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    trap 'on_exit "$?"' EXIT

    echo "[pretest-guardrails] mode=$MODE scope=$SCOPE strict_docs=$STRICT_DOCS"

    run_cleanup
    run_auto_fix
    run_repo_checks
    run_docs_identity_checks
    run_docs_verify
    run_memory_checks
    run_architecture_checks

    echo "[pretest-guardrails] OK"

    return 0
}

main "$@"
exit "$?"
