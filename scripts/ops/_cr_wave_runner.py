#!/usr/bin/env python3
"""Write + optionally invoke the CodeRabbit residual wave bash runner."""
from __future__ import annotations

from pathlib import Path

BASH_SCRIPT = r'''#!/usr/bin/env bash
# CodeRabbit residual wave runner (orphan-scope: empty base -> scope commit)
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
export GH_TOKEN
GH_TOKEN="$(gh auth token 2>/dev/null || true)"
export GITHUB_TOKEN="${GH_TOKEN:-}"

MAIN_REPO="${MAIN_REPO:-/mnt/e/github/BioactivityDataAcquisition}"
WT_BASE="${WT_BASE:-/tmp/bioetl-cr-full-waves}"
ARTIFACT_HOST="${ARTIFACT_HOST:-/mnt/c/Users/Fedor/bioetl-cr-artifacts}"
AUDIT_DATE="$(date -u +%Y%m%d)"
OUT_DIR="${ARTIFACT_HOST}/${AUDIT_DATE}"

mkdir -p "$OUT_DIR" "$WT_BASE"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

ensure_main_fetch() {
  git -C "$MAIN_REPO" fetch origin main --quiet
  BASE_SHA="$(git -C "$MAIN_REPO" rev-parse origin/main)"
  log "BASE_SHA=$BASE_SHA"
  echo "$BASE_SHA" > "$OUT_DIR/BASE_SHA.txt"
}

prepare_scope_worktree() {
  local leaf_id="$1"
  shift
  local paths=("$@")
  local wt="$WT_BASE/$leaf_id"
  rm -rf "$wt"
  git -C "$MAIN_REPO" worktree prune 2>/dev/null || true
  git -C "$MAIN_REPO" worktree add --detach "$wt" origin/main --quiet
  pushd "$wt" >/dev/null
  git checkout --orphan "cr-scope-$leaf_id" --quiet
  git rm -rf --quiet . 2>/dev/null || true
  git -c user.email="coderabbit-audit@local" -c user.name="CR Residual Audit" \
    commit --allow-empty --quiet -m "cr-residual empty base for $leaf_id"
  git rev-parse HEAD > "$wt/.cr_empty_commit"
  local p
  for p in "${paths[@]}"; do
    git checkout origin/main -- "$p" 2>/dev/null || true
  done
  local count
  count="$(git ls-files | wc -l | tr -d ' ')"
  if [[ "$count" -eq 0 ]]; then
    log "WARN: leaf $leaf_id has 0 files; paths=${paths[*]}"
    popd >/dev/null
    return 2
  fi
  if [[ "$count" -gt 300 ]]; then
    log "ERROR: leaf $leaf_id has $count files (>300)"
    popd >/dev/null
    return 3
  fi
  git add -A
  git -c user.email="coderabbit-audit@local" -c user.name="CR Residual Audit" \
    commit --quiet -m "cr-residual scope $leaf_id ($count files)"
  echo "$count"
  popd >/dev/null
}

run_leaf_review() {
  local leaf_id="$1"
  shift
  local paths=("$@")
  local wt="$WT_BASE/$leaf_id"
  local logf="$OUT_DIR/review_${leaf_id}.log"
  local agentf="$OUT_DIR/review_${leaf_id}.agent.json"
  local meta="$OUT_DIR/review_${leaf_id}.meta.json"

  log "=== LEAF $leaf_id paths=${paths[*]} ==="
  local count
  set +e
  count="$(prepare_scope_worktree "$leaf_id" "${paths[@]}")"
  local prep_rc=$?
  set -e
  if [[ $prep_rc -ne 0 ]]; then
    echo "{\"leaf\":\"$leaf_id\",\"status\":\"prepare_failed\",\"rc\":$prep_rc}" > "$meta"
    log "prepare failed for $leaf_id rc=$prep_rc"
    return 0
  fi

  log "Prepared $leaf_id with $count files; running CodeRabbit..."
  pushd "$wt" >/dev/null
  local empty_commit
  empty_commit="$(cat "$wt/.cr_empty_commit")"

  set +e
  coderabbit review --base-commit "$empty_commit" --agent --light >"$agentf" 2>"$logf.err"
  local rc_agent=$?
  if [[ ! -s "$agentf" ]]; then
    coderabbit review --base-commit "$empty_commit" --plain --light >"$logf" 2>>"$logf.err"
  else
    cp "$agentf" "$logf"
  fi
  local rc_plain=$?
  coderabbit review findings >"$OUT_DIR/review_${leaf_id}.findings.txt" 2>/dev/null || true
  set -e
  popd >/dev/null

  git -C "$MAIN_REPO" worktree remove --force "$wt" 2>/dev/null || rm -rf "$wt"

  python3 -c "import json,pathlib; a=pathlib.Path(r'$agentf'); m={'leaf':r'$leaf_id','file_count':int('$count' or 0),'rc_agent':int('$rc_agent' or 1),'rc_plain':int('$rc_plain' or 1),'status':'ok' if a.exists() and a.stat().st_size>20 else 'review_failed'}; pathlib.Path(r'$meta').write_text(json.dumps(m,indent=2),encoding='utf-8'); print(json.dumps(m))"
  sleep 6
}

run_wave_A_priority() {
  run_leaf_review S09-composition src/bioetl/composition
  run_leaf_review S03-app-control-plane src/bioetl/application/services/control_plane
  run_leaf_review S02-app-core src/bioetl/application/core
  run_leaf_review S06-infra-adapters src/bioetl/infrastructure/adapters
  run_leaf_review S10-interfaces-cli src/bioetl/interfaces/cli
  run_leaf_review S11-interfaces-http src/bioetl/interfaces/http
  run_leaf_review S01-domain-ports src/bioetl/domain/ports
  run_leaf_review S01-domain-contracts src/bioetl/domain/contracts
  run_leaf_review S01-domain-aggregates src/bioetl/domain/aggregates
  run_leaf_review S01-domain-exceptions src/bioetl/domain/exceptions
  run_leaf_review S01-domain-entities src/bioetl/domain/entities
  run_leaf_review S01-domain-value_objects src/bioetl/domain/value_objects
  run_leaf_review S01-domain-control_plane src/bioetl/domain/control_plane
  run_leaf_review S01-domain-schemas src/bioetl/domain/schemas
  run_leaf_review S04-app-services-batch src/bioetl/application/services/batch
  run_leaf_review S04-app-services-quality src/bioetl/application/services/quality
}

run_wave_B() {
  run_leaf_review S05-app-pipelines src/bioetl/application/pipelines
  run_leaf_review S07-infra-http-storage src/bioetl/infrastructure/http src/bioetl/infrastructure/storage src/bioetl/infrastructure/delta
  run_leaf_review S16-configs-quality configs/quality
}

run_wave_C() {
  run_leaf_review S08-infra-observability src/bioetl/infrastructure/observability
  run_leaf_review S07-http-only src/bioetl/infrastructure/http
}

run_wave_D() {
  run_leaf_review S20-security-surface tests/security
  run_leaf_review S20-github-workflows .github/workflows
  run_leaf_review S20-security-config .gitleaks.toml .secrets.baseline .coderabbit.yaml
}

run_wave_E() {
  run_leaf_review S17-docs-decisions docs/02-architecture/decisions
  run_leaf_review S17-docs-governance docs/00-project/governance
  run_leaf_review S17-docs-normative-core docs/00-project/RULES.md docs/00-project/NORMATIVE_SOURCES.md docs/00-project/TOOLS.md docs/00-project/00-map.md docs/00-project/architecture-index.md docs/00-project/glossary.md docs/00-project/index.md docs/00-project/rules-summary.md docs/00-project/extended-docs-index.md
  run_leaf_review S18-grafana grafana docs/03-guides/dashboards
  run_leaf_review S19-scripts-engineering scripts/engineering
}

run_wave_F() {
  run_leaf_review S12-tests-arch-boundary tests/architecture/test_boundary_assertions.py tests/architecture/test_layer_dependencies.py tests/architecture/test_layer_matrix_guards.py tests/architecture/test_import_linter_workflow.py tests/architecture/test_strict_architecture_contracts.py tests/architecture/test_cli_registry_explicit_path.py
  run_leaf_review S14-tests-unit-application-services tests/unit/application/services
  run_leaf_review S14-tests-unit-application-core tests/unit/application/core
  run_leaf_review S14-tests-unit-application-pipelines tests/unit/application/pipelines
  run_leaf_review S14-tests-unit-application-composite tests/unit/application/composite
  run_leaf_review S15-tests-integration tests/integration
}

cmd="${1:-}"
ensure_main_fetch
coderabbit auth status || true

case "$cmd" in
  A|waveA) run_wave_A_priority ;;
  B|waveB) run_wave_B ;;
  C|waveC) run_wave_C ;;
  D|waveD) run_wave_D ;;
  E|waveE) run_wave_E ;;
  F|waveF) run_wave_F ;;
  leaf)
    shift
    leaf_id="$1"; shift
    run_leaf_review "$leaf_id" "$@"
    ;;
  *)
    echo "Usage: $0 {A|B|C|D|E|F|leaf <id> <paths...>}"
    exit 1
    ;;
esac

log "Done wave $cmd -> $OUT_DIR"
ls -la "$OUT_DIR" | head -80
'''


def main() -> None:
    out = Path("/mnt/c/Users/Fedor/_cr_wave_runner.sh")
    # When run from Windows Python, also write local copy
    candidates = [
        Path(r"C:\Users\Fedor\_cr_wave_runner.sh"),
        Path("/mnt/c/Users/Fedor/_cr_wave_runner.sh"),
    ]
    written = None
    for p in candidates:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(BASH_SCRIPT, encoding="utf-8", newline="\n")
            written = p
            break
        except OSError:
            continue
    if written is None:
        # workspace fallback
        written = Path(__file__).resolve().parent / "_cr_wave_runner.sh"
        written.write_text(BASH_SCRIPT, encoding="utf-8", newline="\n")
    print(f"wrote {written} ({written.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
