#!/usr/bin/env bash
# ==============================================================================
# run/setup.sh — Консолидированный скрипт настройки окружения BioETL
#
# Использование:
#   ./run/setup.sh              # Полная настройка
#   ./run/setup.sh --quick      # Быстрая установка (без линтеров/тестов)
#   ./run/setup.sh --skip-tests # Запуск линтеров без тестов
#   ./run/setup.sh --force      # Пересоздание .venv
# ==============================================================================

set -euo pipefail

readonly MIN_PYTHON_MAJOR=3
readonly MIN_PYTHON_MINOR=11
readonly VENV_DIR=".venv"

QUICK_MODE=false
SKIP_TESTS=false
FORCE=false
PYTHON_CMD=""
VENV_PYTHON=""

log() {
    printf "[setup] %s\n" "$1"
}

warn() {
    printf "[setup][warn] %s\n" "$1"
}

fail() {
    printf "[setup][error] %s\n" "$1" >&2
    exit 1
}

show_help() {
    cat <<'USAGE'
BioETL setup script

Usage:
  ./run/setup.sh [OPTIONS]

Options:
  --quick, -q     Быстрая установка без проверок качества
  --skip-tests    Пропустить тесты, но выполнить линтеры
  --force, -f     Пересоздать .venv
  --help, -h      Показать справку
USAGE
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --quick|-q)
                QUICK_MODE=true
                SKIP_TESTS=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
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
                fail "Unknown option: $1"
                ;;
        esac
    done
}

check_python_compatibility() {
    local cmd="$1"
    local major minor

    major="$($cmd -c 'import sys; print(sys.version_info.major)')"
    minor="$($cmd -c 'import sys; print(sys.version_info.minor)')"

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
        if command -v "$cmd" >/dev/null 2>&1 && check_python_compatibility "$cmd"; then
            echo "$cmd"
            return 0
        fi
    done

    return 1
}

ensure_repo_root() {
    [[ -f "pyproject.toml" ]] || fail "Run script from repository root (pyproject.toml not found)."
    [[ -f "Makefile" ]] || warn "Makefile not found. Some checks may be unavailable."
}

ensure_prerequisites() {
    log "Checking prerequisites"

    command -v git >/dev/null 2>&1 || fail "git is required"

    if command -v make >/dev/null 2>&1; then
        log "make found: $(make --version | head -1)"
    else
        warn "make not found (optional)."
    fi

    if ! PYTHON_CMD="$(find_python)"; then
        fail "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ is required"
    fi

    log "Using python: $($PYTHON_CMD --version 2>&1)"
}

create_venv_if_needed() {
    if [[ -d "$VENV_DIR" && "$FORCE" == true ]]; then
        log "Removing existing $VENV_DIR (--force)"
        rm -rf "$VENV_DIR"
    fi

    if [[ ! -d "$VENV_DIR" ]]; then
        log "Creating virtual environment: $VENV_DIR"
        "$PYTHON_CMD" -m venv "$VENV_DIR"
    else
        log "Using existing virtual environment: $VENV_DIR"
    fi

    if [[ -x "$VENV_DIR/bin/python" ]]; then
        VENV_PYTHON="$VENV_DIR/bin/python"
    elif [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
        VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
    else
        fail "Cannot find python inside $VENV_DIR"
    fi
}

install_with_uv() {
    if [[ "$FORCE" == true && -d "$VENV_DIR" ]]; then
        log "Resetting $VENV_DIR before uv sync (--force)"
        rm -rf "$VENV_DIR"
    fi

    if [[ "$QUICK_MODE" == true ]]; then
        log "Installing runtime deps with uv"
        uv sync
    else
        log "Installing dev/test/tracing deps with uv"
        uv sync --extra dev --extra tests --extra tracing
    fi

    if [[ -x "$VENV_DIR/bin/python" ]]; then
        VENV_PYTHON="$VENV_DIR/bin/python"
    elif [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
        VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
    else
        VENV_PYTHON="$PYTHON_CMD"
    fi
}

install_with_pip() {
    create_venv_if_needed

    log "Upgrading pip/setuptools/wheel"
    "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel

    if [[ "$QUICK_MODE" == true ]]; then
        log "Installing package (editable)"
        "$VENV_PYTHON" -m pip install -e .
    else
        log "Installing package with extras [dev,tests,tracing]"
        "$VENV_PYTHON" -m pip install -e '.[dev,tests,tracing]'
    fi
}

install_dependencies() {
    log "Installing dependencies"

    if command -v uv >/dev/null 2>&1; then
        install_with_uv
    else
        warn "uv not found, fallback to pip + .venv"
        install_with_pip
    fi
}

setup_env_file() {
    if [[ -f ".env" ]]; then
        log ".env already exists"
        return
    fi

    if [[ -f ".env.example" ]]; then
        log "Creating .env from .env.example"
        cp .env.example .env
    else
        warn ".env.example not found, skipping .env creation"
    fi
}

setup_precommit() {
    [[ -f ".pre-commit-config.yaml" ]] || return 0

    if ! "$VENV_PYTHON" -m pip show pre-commit >/dev/null 2>&1; then
        log "Installing pre-commit"
        "$VENV_PYTHON" -m pip install pre-commit
    fi

    log "Installing pre-commit hooks"
    "$VENV_PYTHON" -m pre_commit install --install-hooks >/dev/null 2>&1 || \
        warn "Could not install pre-commit hooks (possibly outside git repo)"
}

verify_installation() {
    log "Verifying import"
    "$VENV_PYTHON" -c 'import bioetl; print(f"bioetl {bioetl.__version__}")'

    log "Verifying CLI"
    "$VENV_PYTHON" -m bioetl --help >/dev/null
}

run_quality_checks() {
    if [[ "$QUICK_MODE" == true ]]; then
        warn "Quick mode enabled, skipping lint/tests"
        return
    fi

    log "Running ruff"
    "$VENV_PYTHON" -m ruff check src/ tests/ || warn "ruff reported issues"

    log "Running mypy"
    "$VENV_PYTHON" -m mypy src/bioetl --no-error-summary || warn "mypy reported issues"

    if [[ "$SKIP_TESTS" == true ]]; then
        warn "Tests skipped (--skip-tests)"
        return
    fi

    log "Running tests"
    "$VENV_PYTHON" -m pytest tests/ -q --tb=short || warn "tests reported failures"
}

print_summary() {
    cat <<'SUMMARY'

Setup complete.

Next steps:
  1) Activate environment:
     source .venv/bin/activate
  2) Run checks:
     make lint && make test
  3) Run sample pipeline:
     make run-local
SUMMARY
}

main() {
    parse_args "$@"
    ensure_repo_root
    ensure_prerequisites
    install_dependencies
    setup_env_file
    setup_precommit
    verify_installation
    run_quality_checks
    print_summary
}

main "$@"
