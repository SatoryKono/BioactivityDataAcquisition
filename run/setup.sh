#!/usr/bin/env bash
# BioETL environment setup script
# Usage:
#   ./run/setup.sh
#   ./run/setup.sh --quick
#   ./run/setup.sh --force

set -euo pipefail

readonly MIN_PYTHON_MAJOR=3
readonly MIN_PYTHON_MINOR=11
readonly VENV_DIR=".venv"

QUICK_MODE=false
FORCE=false

log() { printf "[setup] %s\n" "$1"; }
warn() { printf "[setup][warn] %s\n" "$1"; }
err() { printf "[setup][error] %s\n" "$1" >&2; }

show_help() {
    cat <<'USAGE'
BioETL setup script

Usage:
  ./run/setup.sh [OPTIONS]

Options:
  --quick, -q   Install only runtime dependencies (skip dev tooling)
  --force, -f   Recreate virtual environment even if it already exists
  --help, -h    Show this help
USAGE
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --quick|-q)
                QUICK_MODE=true
                shift
                ;;
            --force|-f)
                FORCE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                err "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

is_python_compatible() {
    local py_cmd="$1"
    local major minor
    major="$($py_cmd -c 'import sys; print(sys.version_info.major)')"
    minor="$($py_cmd -c 'import sys; print(sys.version_info.minor)')"

    if [[ "$major" -gt "$MIN_PYTHON_MAJOR" ]]; then
        return 0
    fi
    if [[ "$major" -eq "$MIN_PYTHON_MAJOR" && "$minor" -ge "$MIN_PYTHON_MINOR" ]]; then
        return 0
    fi
    return 1
}

find_python() {
    local candidates=("python3.12" "python3.11" "python3" "python")
    local cmd
    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1 && is_python_compatible "$cmd"; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

create_or_reuse_venv() {
    local py_cmd="$1"

    if [[ -d "$VENV_DIR" ]]; then
        if [[ "$FORCE" == true ]]; then
            log "Removing existing virtual environment ($VENV_DIR)"
            rm -rf "$VENV_DIR"
        else
            log "Virtual environment already exists: $VENV_DIR"
            return 0
        fi
    fi

    log "Creating virtual environment with $py_cmd"
    "$py_cmd" -m venv "$VENV_DIR"
}

venv_python_path() {
    if [[ -x "$VENV_DIR/bin/python" ]]; then
        echo "$VENV_DIR/bin/python"
    elif [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
        echo "$VENV_DIR/Scripts/python.exe"
    else
        err "Cannot locate python in virtual environment"
        exit 1
    fi
}

install_dependencies() {
    local py_cmd="$1"

    if command -v uv >/dev/null 2>&1; then
        if [[ "$QUICK_MODE" == true ]]; then
            log "Installing runtime dependencies with uv"
            uv sync
        else
            log "Installing development dependencies with uv"
            uv sync --extra dev --extra tracing --extra tests
        fi
        return 0
    fi

    warn "uv not found, using pip in local virtual environment"
    create_or_reuse_venv "$py_cmd"

    local vpy
    vpy="$(venv_python_path)"

    log "Upgrading pip/setuptools/wheel"
    "$vpy" -m pip install --upgrade pip setuptools wheel

    if [[ "$QUICK_MODE" == true ]]; then
        log "Installing package in editable mode"
        "$vpy" -m pip install -e .
    else
        log "Installing package with dev/test/tracing extras"
        "$vpy" -m pip install -e '.[dev,tests,tracing]'
    fi
}

setup_env_file() {
    if [[ -f ".env" ]]; then
        log ".env already exists, keeping current file"
    elif [[ -f ".env.example" ]]; then
        log "Creating .env from .env.example"
        cp .env.example .env
    else
        warn ".env.example not found, skipping .env creation"
    fi
}

print_next_steps() {
    cat <<'NEXT'

Setup complete.

Next steps:
  1) Activate virtual env (pip mode): source .venv/bin/activate
  2) Run checks: make lint && make test
  3) Run pipeline sample: make run-local
NEXT
}

main() {
    parse_args "$@"

    if [[ ! -f "pyproject.toml" ]]; then
        err "Run this script from repository root"
        exit 1
    fi

    local py_cmd
    if ! py_cmd="$(find_python)"; then
        err "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ not found"
        exit 1
    fi

    log "Using python: $($py_cmd --version 2>&1)"

    install_dependencies "$py_cmd"
    setup_env_file
    print_next_steps
}

main "$@"
