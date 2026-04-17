#!/usr/bin/env bash
# Diagram docs agent pipeline:
# 1) lint/validate/render checks
# 2) regenerate with-descriptions DOCX bundles
# 3) regenerate with-descriptions PDF bundles
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT_GIT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
  REPO_ROOT="$REPO_ROOT_GIT"
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
PROFILE="pr"
TEXT_LAYER="${TEXT_LAYER:-fallback-only}"
DIAGRAM_PATH=""
SKIP_CHECKS=0
SKIP_RENDER=0
SKIP_DOCX=0
SKIP_PDF=0
ENFORCE_BUDGET=0
STRICT_NIGHTLY=0
INPUT_MD=()

usage() {
  cat <<'EOF'
Usage: scripts/diagrams/run_diagram_docs_agent.sh [options]

Options:
  --profile <pr|nightly|quick>   Diagram checks profile (default: pr)
  --diagram <path>               Scope checks/render to one .mmd/.mermaid file
  --text-layer <mode>            SVG text layer mode (default: fallback-only)
  --input-md <path>              Markdown bundle for DOCX/PDF generation (repeatable)
  --enforce-budget               Enable blocking diagram quality budget
  --strict-nightly               Fail nightly profile on warnings
  --skip-checks                  Skip run_diagram_checks phase
  --skip-render                  Skip render inside run_diagram_checks
  --skip-docx                    Skip DOCX generation phase
  --skip-pdf                     Skip PDF generation phase
  -h, --help                     Show this help

Examples:
  scripts/diagrams/run_diagram_docs_agent.sh
  scripts/diagrams/run_diagram_docs_agent.sh --profile pr --enforce-budget
  scripts/diagrams/run_diagram_docs_agent.sh --diagram <repo-relative-diagram-path>
  scripts/diagrams/run_diagram_docs_agent.sh --input-md <repo-relative-bundle-path>
EOF
}

log() { printf '[INFO] %s\n' "$*"; }

resolve_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    printf '%s\n' "$PYTHON_BIN"
    return
  fi
  if [[ -x "$REPO_ROOT/.venv-win/Scripts/python.exe" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv-win/Scripts/python.exe"
    return
  fi
  if [[ -x "${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python" ]]; then
    printf '%s\n' "${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python"
    return
  fi
  if [[ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/Scripts/python.exe"
    return
  fi
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/bin/python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi
  echo "Python interpreter not found. Set PYTHON_BIN." >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:-}"
      shift 2
      ;;
    --diagram)
      DIAGRAM_PATH="${2:-}"
      shift 2
      ;;
    --text-layer)
      TEXT_LAYER="${2:-}"
      shift 2
      ;;
    --input-md)
      INPUT_MD+=("${2:-}")
      shift 2
      ;;
    --enforce-budget)
      ENFORCE_BUDGET=1
      shift
      ;;
    --strict-nightly)
      STRICT_NIGHTLY=1
      shift
      ;;
    --skip-checks)
      SKIP_CHECKS=1
      shift
      ;;
    --skip-render)
      SKIP_RENDER=1
      shift
      ;;
    --skip-docx)
      SKIP_DOCX=1
      shift
      ;;
    --skip-pdf)
      SKIP_PDF=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

PYTHON_CMD="$(resolve_python)"
MD_ARGS=()
if [[ "${#INPUT_MD[@]}" -gt 0 ]]; then
  for item in "${INPUT_MD[@]}"; do
    MD_ARGS+=("--input-md" "$item")
  done
fi

if [[ "$SKIP_CHECKS" -eq 0 ]]; then
  CHECK_CMD=("bash" "$REPO_ROOT/scripts/diagrams/run_diagram_checks.sh" "--profile" "$PROFILE" "--text-layer" "$TEXT_LAYER")
  if [[ -n "$DIAGRAM_PATH" ]]; then
    CHECK_CMD+=("--diagram" "$DIAGRAM_PATH")
  fi
  if [[ "$ENFORCE_BUDGET" -eq 1 ]]; then
    CHECK_CMD+=("--enforce-budget")
  fi
  if [[ "$STRICT_NIGHTLY" -eq 1 ]]; then
    CHECK_CMD+=("--strict-nightly")
  fi
  if [[ "$SKIP_RENDER" -eq 1 ]]; then
    CHECK_CMD+=("--skip-render")
  fi

  log "Running diagram checks: ${CHECK_CMD[*]}"
  "${CHECK_CMD[@]}"
else
  log "Skipping diagram checks (--skip-checks)."
fi

if [[ "$SKIP_DOCX" -eq 0 ]]; then
  DOCX_CMD=("$PYTHON_CMD" "$REPO_ROOT/scripts/diagrams/generate_with_descriptions_docx.py")
  DOCX_CMD+=("${MD_ARGS[@]}")
  log "Generating DOCX bundles: ${DOCX_CMD[*]}"
  "${DOCX_CMD[@]}"
else
  log "Skipping DOCX generation (--skip-docx)."
fi

if [[ "$SKIP_PDF" -eq 0 ]]; then
  PDF_CMD=("$PYTHON_CMD" "$REPO_ROOT/scripts/diagrams/generate_with_descriptions_pdf.py")
  PDF_CMD+=("${MD_ARGS[@]}")
  log "Generating PDF bundles: ${PDF_CMD[*]}"
  "${PDF_CMD[@]}"
else
  log "Skipping PDF generation (--skip-pdf)."
fi

log "Diagram docs agent pipeline completed."
