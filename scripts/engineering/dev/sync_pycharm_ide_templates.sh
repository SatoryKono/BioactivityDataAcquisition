#!/usr/bin/env bash
# Sync portable PyCharm templates from configs/ide/pycharm into local .idea/
# Does NOT overwrite machine-local surfaces (workspace.xml, .iml, shelves, etc.)
# unless --force-all is passed.
#
# Usage:
#   bash scripts/engineering/dev/sync_pycharm_ide_templates.sh
#   bash scripts/engineering/dev/sync_pycharm_ide_templates.sh --dry-run
#   bash scripts/engineering/dev/sync_pycharm_ide_templates.sh --skip-policy-check

set -euo pipefail

DRY_RUN=0
FORCE_ALL=0
SKIP_POLICY=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --force-all) FORCE_ALL=1 ;;
    --skip-policy-check) SKIP_POLICY=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "[sync_pycharm_ide_templates][error] Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$REPO_ROOT"

SOURCE_ROOT="${REPO_ROOT}/configs/ide/pycharm"
DEST_ROOT="${REPO_ROOT}/.idea"

REQUIRED_RUN_CONFIGS=(
  "Pytest_Fast.xml"
  "Pytest_Full.xml"
  "Pytest_Coverage.xml"
  "Pytest_Debug.xml"
  "Pytest_Architecture.xml"
  "Pytest_Architecture_Full.xml"
  "Mypy_Full.xml"
  "Ruff_Check.xml"
  "Ruff_Format_Check.xml"
  "Quality_Gate.xml"
  "BioETL_Smoke_Offline.xml"
)

SHARED_REL_PATHS=(
  "codeStyles"
  "inspectionProfiles"
  "runConfigurations"
  "pyLspTools.xml"
)

log() {
  local level="$1"
  shift
  echo "[sync_pycharm_ide_templates][${level}] $*"
}

policy_check() {
  local run_dir="$1"
  local failures=0
  local f name text

  if [[ ! -d "$run_dir" ]]; then
    log error "Missing shared runConfigurations at ${run_dir}"
    return 1
  fi

  for required in "${REQUIRED_RUN_CONFIGS[@]}"; do
    if [[ ! -f "${run_dir}/${required}" ]]; then
      log error "missing required shared run config: ${required}"
      failures=1
    fi
  done

  shopt -s nullglob
  for f in "${run_dir}"/*.xml; do
    name="$(basename "$f")"
    text="$(cat "$f")"

    if grep -q 'name="PYTHONPATH"' <<<"$text"; then
      log error "${name}: forbidden PYTHONPATH env"
      failures=1
    fi
    if grep -q 'ADD_CONTENT_ROOTS" value="true"' <<<"$text"; then
      log error "${name}: ADD_CONTENT_ROOTS must be false"
      failures=1
    fi
    if grep -q 'ADD_SOURCE_ROOTS" value="true"' <<<"$text"; then
      log error "${name}: ADD_SOURCE_ROOTS must be false"
      failures=1
    fi

    if grep -qE 'factoryName="py\.test"|type="tests"' <<<"$text"; then
      if [[ "$name" == "Pytest_Coverage.xml" ]] || grep -q 'name="pytest-coverage"' <<<"$text"; then
        if ! grep -q -- '--cov=' <<<"$text"; then
          log error "${name}: pytest-coverage must include --cov="
          failures=1
        fi
      else
        if ! grep -q -- '--no-cov' <<<"$text"; then
          log error "${name}: non-coverage pytest config must include --no-cov"
          failures=1
        fi
        if grep -qE -- '--cov(=|[[:space:]])' <<<"$text"; then
          log error "${name}: --cov is only allowed on pytest-coverage"
          failures=1
        fi
      fi
    fi
  done
  shopt -u nullglob

  return "$failures"
}

if [[ ! -d "$SOURCE_ROOT" ]]; then
  log error "Source templates not found: ${SOURCE_ROOT}"
  exit 1
fi

if [[ "$SKIP_POLICY" -eq 0 ]]; then
  if ! policy_check "${SOURCE_ROOT}/runConfigurations"; then
    log error "Shared template policy check failed"
    exit 2
  fi
  log ok "Shared runConfiguration policy check passed"
fi

if [[ ! -d "$DEST_ROOT" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log dry-run "Would create ${DEST_ROOT}"
  else
    mkdir -p "$DEST_ROOT"
    log ok "Created ${DEST_ROOT}"
  fi
fi

sync_one() {
  local rel="$1"
  local src="${SOURCE_ROOT}/${rel}"
  local dst="${DEST_ROOT}/${rel}"

  if [[ ! -e "$src" ]]; then
    log error "Expected shared surface missing: ${rel}"
    exit 1
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    log dry-run "Would sync ${rel} -> .idea/${rel}"
    return 0
  fi

  if [[ -d "$src" ]]; then
    mkdir -p "$dst"
    # shellcheck disable=SC2086
    cp -R "${src}/." "${dst}/"
  else
    mkdir -p "$(dirname "$dst")"
    cp -f "$src" "$dst"
  fi
  log ok "Synced ${rel}"
}

if [[ "$FORCE_ALL" -eq 1 ]]; then
  log warn "--force-all copies entire shared tree; still avoid committing machine-local .idea state"
  # shellcheck disable=SC2012
  while IFS= read -r -d '' entry; do
    sync_one "$(basename "$entry")"
  done < <(find "$SOURCE_ROOT" -mindepth 1 -maxdepth 1 -print0)
else
  for rel in "${SHARED_REL_PATHS[@]}"; do
    sync_one "$rel"
  done
fi

if [[ "$DRY_RUN" -eq 0 ]]; then
  for required in "${REQUIRED_RUN_CONFIGS[@]}"; do
    if [[ ! -f "${DEST_ROOT}/runConfigurations/${required}" ]]; then
      log error "After sync missing: .idea/runConfigurations/${required}"
      exit 3
    fi
  done
fi

echo
log hint "Post-sync checklist:"
echo "  1. Interpreter: \$PROJECT_DIR/.venv-win/Scripts/python.exe (editable install, no PYTHONPATH)"
echo "  2. Run Configurations: pytest-fast, pytest-architecture, pytest-architecture-full, pytest-debug, pytest-coverage, mypy-full, ruff-check, quality-gate, BioETL smoke (offline fixture)"
echo "  3. Formatter: Ruff only (Black disabled in Actions on Save)"
echo "  4. AI: exactly one inline completion provider"
echo "  5. Do not commit .idea/workspace.xml, shelves, SDK paths, MCP tokens, or .env"
echo "  6. Docs: docs/03-guides/development/pycharm-setup.md"

if [[ "$DRY_RUN" -eq 1 ]]; then
  log ok "Dry-run complete (no files written)"
else
  log ok "Sync complete"
fi
