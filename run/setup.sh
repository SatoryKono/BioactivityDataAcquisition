#!/usr/bin/env bash
# BioETL environment setup script
# Usage:
#   ./run/setup.sh
#   ./run/setup.sh --quick
#   ./run/setup.sh --force
#   ./run/setup.sh --pip

set -euo pipefail

readonly MIN_PYTHON_MAJOR=3
readonly MIN_PYTHON_MINOR=11
readonly VENV_DIR=".venv"

FORCE=false
QUICK=false
USE_PIP=false
SKIP_HOOKS=false

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_ok() { echo -e "${GREEN}✔${NC} $1"; }
print_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
print_err() { echo -e "${RED}✖${NC} $1"; }

show_help() {
  cat <<'USAGE'
BioETL setup

Options:
  --quick         Skip lint/test checks
  --force         Recreate virtual environment
  --pip           Force pip mode even if uv is available
  --skip-hooks    Skip pre-commit hook installation
  --help, -h      Show help
USAGE
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --quick) QUICK=true ;;
      --force) FORCE=true ;;
      --pip) USE_PIP=true ;;
      --skip-hooks) SKIP_HOOKS=true ;;
      --help|-h) show_help; exit 0 ;;
      *) print_err "Unknown argument: $1"; show_help; exit 1 ;;
    esac
    shift
  done
}

check_python_version() {
  local py_cmd="$1"
  local major minor
  major="$($py_cmd -c 'import sys; print(sys.version_info.major)')"
  minor="$($py_cmd -c 'import sys; print(sys.version_info.minor)')"

  if [[ "$major" -lt "$MIN_PYTHON_MAJOR" ]] || { [[ "$major" -eq "$MIN_PYTHON_MAJOR" ]] && [[ "$minor" -lt "$MIN_PYTHON_MINOR" ]]; }; then
    return 1
  fi
  return 0
}

find_python() {
  local candidates=("python3.12" "python3.11" "python3" "python")
  for cmd in "${candidates[@]}"; do
    if command -v "$cmd" >/dev/null 2>&1 && check_python_version "$cmd"; then
      echo "$cmd"
      return 0
    fi
  done
  return 1
}

setup_paths() {
  local script_dir repo_root
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  repo_root="$(cd "$script_dir/.." && pwd)"
  cd "$repo_root"

  if [[ ! -f "pyproject.toml" ]]; then
    print_err "Run script from BioETL repository (pyproject.toml not found)."
    exit 1
  fi
}

create_venv() {
  if [[ -d "$VENV_DIR" && "$FORCE" == true ]]; then
    print_warn "Removing existing virtual environment ($VENV_DIR)."
    rm -rf "$VENV_DIR"
  fi

  if [[ ! -d "$VENV_DIR" ]]; then
    print_info "Creating virtual environment..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    print_ok "Virtual environment created: $VENV_DIR"
  else
    print_ok "Using existing virtual environment: $VENV_DIR"
  fi
}

venv_python() {
  if [[ "${OS:-}" == "Windows_NT" ]]; then
    echo "$VENV_DIR/Scripts/python"
  else
    echo "$VENV_DIR/bin/python"
  fi
}

install_dependencies() {
  local py
  py="$(venv_python)"

  print_info "Upgrading pip tooling..."
  "$py" -m pip install --upgrade pip setuptools wheel >/dev/null

  if command -v uv >/dev/null 2>&1 && [[ "$USE_PIP" == false ]]; then
    print_info "Installing dependencies with uv (recommended)..."
    uv sync --extra dev --extra tests --extra tracing
  else
    print_info "Installing dependencies with pip..."
    "$py" -m pip install -e ".[dev,tests,tracing]"
  fi

  print_ok "Dependencies installed."
}

setup_env_file() {
  if [[ -f ".env" ]]; then
    print_ok ".env already exists"
    return 0
  fi

  if [[ -f ".env.example" ]]; then
    cp ".env.example" ".env"
    print_ok "Created .env from .env.example"
  else
    print_warn "No .env.example found, skipping env bootstrap"
  fi
}

setup_directories() {
  mkdir -p data logs
  print_ok "Ensured local directories: data/, logs/"
}

setup_precommit() {
  if [[ "$SKIP_HOOKS" == true ]]; then
    print_warn "Skipping pre-commit hook setup (--skip-hooks)."
    return 0
  fi

  if [[ ! -d .git ]]; then
    print_warn "Not a git checkout, skipping pre-commit setup."
    return 0
  fi

  local py
  py="$(venv_python)"

  if [[ -f ".pre-commit-config.yaml" ]]; then
    "$py" -m pip install pre-commit >/dev/null
    if "$py" -m pre_commit install --install-hooks >/dev/null 2>&1; then
      print_ok "Pre-commit hooks installed"
    else
      print_warn "Failed to install pre-commit hooks"
    fi
  else
    print_warn "No .pre-commit-config.yaml found"
  fi
}

verify_installation() {
  local py
  py="$(venv_python)"

  print_info "Verifying bioetl import..."
  "$py" -c "import bioetl; print(bioetl.__version__)" >/dev/null
  print_ok "bioetl package import is OK"

  print_info "Verifying CLI entrypoint..."
  "$py" -m bioetl --help >/dev/null
  print_ok "CLI check passed"
}

run_optional_checks() {
  if [[ "$QUICK" == true ]]; then
    print_warn "Quick mode enabled: skipped lint/test checks."
    return 0
  fi

  local py
  py="$(venv_python)"

  print_info "Running ruff check..."
  if "$py" -m ruff check src/ tests/ >/dev/null; then
    print_ok "ruff passed"
  else
    print_warn "ruff reported issues"
  fi

  print_info "Running fast architecture checks..."
  if "$py" -m pytest tests/architecture/ -q >/dev/null; then
    print_ok "architecture tests passed"
  else
    print_warn "architecture tests reported issues"
  fi
}

print_next_steps() {
  local activate
  if [[ "${OS:-}" == "Windows_NT" ]]; then
    activate=".venv\\Scripts\\activate"
  else
    activate="source .venv/bin/activate"
  fi

  cat <<MSG

Setup finished.

Next steps:
  1) Activate environment: $activate
  2) Run checks: make lint && make test
  3) Start pipeline: bioetl run --pipeline chembl_activity --limit 10
MSG
}

main() {
  parse_args "$@"
  setup_paths

  print_info "Checking prerequisites..."
  if ! PYTHON_CMD="$(find_python)"; then
    print_err "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ is required."
    exit 1
  fi

  print_ok "Found Python: $($PYTHON_CMD --version 2>&1)"
  create_venv
  install_dependencies
  setup_env_file
  setup_directories
  setup_precommit
  verify_installation
  run_optional_checks
  print_next_steps
}

main "$@"
