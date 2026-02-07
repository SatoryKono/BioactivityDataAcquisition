#!/usr/bin/env bash
# ==============================================================================
# run/setup.sh — Базовая настройка окружения BioETL
#
# Использование:
#   ./run/setup.sh
#   ./run/setup.sh --force
#   ./run/setup.sh --mode uv
#   ./run/setup.sh --mode pip --with-dev --with-tracing
# ==============================================================================

set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

readonly MIN_PYTHON_MAJOR=3
readonly MIN_PYTHON_MINOR=11
readonly DEFAULT_VENV_DIR=".venv"

MODE="auto"               # auto|uv|pip
FORCE=false
WITH_DEV=false
WITH_TRACING=false
VENV_DIR="$DEFAULT_VENV_DIR"
PYTHON_CMD=""

print_header() {
    echo -e "\n${BLUE}──────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}──────────────────────────────────────────────────────────────${NC}\n"
}

print_step() { echo -e "${GREEN}▶ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✖ $1${NC}"; }
print_success() { echo -e "${GREEN}✔ $1${NC}"; }

show_help() {
    cat <<'USAGE'
BioETL setup script

Usage:
  ./run/setup.sh [options]

Options:
  --mode <auto|uv|pip>  Installation mode (default: auto)
  --with-dev            Install development dependencies
  --with-tracing        Install tracing extra dependencies
  --venv-dir <path>     Virtualenv path for pip mode (default: .venv)
  --python <cmd>        Python command override (e.g. python3.11)
  --force, -f           Recreate environment / force re-sync
  --help, -h            Show this help

Examples:
  ./run/setup.sh
  ./run/setup.sh --mode uv --with-dev --with-tracing
  ./run/setup.sh --mode pip --with-dev --python python3.12
USAGE
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --mode)
                MODE="${2:-}"
                shift 2
                ;;
            --with-dev)
                WITH_DEV=true
                shift
                ;;
            --with-tracing)
                WITH_TRACING=true
                shift
                ;;
            --venv-dir)
                VENV_DIR="${2:-}"
                shift 2
                ;;
            --python)
                PYTHON_CMD="${2:-}"
                shift 2
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
                print_error "Unknown argument: $1"
                show_help
                exit 1
                ;;
        esac
    done

    case "$MODE" in
        auto|uv|pip) ;;
        *)
            print_error "Invalid --mode: $MODE (allowed: auto|uv|pip)"
            exit 1
            ;;
    esac
}

check_python_version() {
    local cmd="$1"
    local major
    local minor

    major="$($cmd -c 'import sys; print(sys.version_info.major)')"
    minor="$($cmd -c 'import sys; print(sys.version_info.minor)')"

    if [[ "$major" -lt "$MIN_PYTHON_MAJOR" ]]; then
        return 1
    fi
    if [[ "$major" -eq "$MIN_PYTHON_MAJOR" && "$minor" -lt "$MIN_PYTHON_MINOR" ]]; then
        return 1
    fi
    return 0
}

find_python() {
    local candidates=("python3.13" "python3.12" "python3.11" "python3" "python")

    if [[ -n "$PYTHON_CMD" ]]; then
        if command -v "$PYTHON_CMD" >/dev/null 2>&1 && check_python_version "$PYTHON_CMD"; then
            echo "$PYTHON_CMD"
            return 0
        fi
        print_error "Requested Python command is unavailable or version < 3.11: $PYTHON_CMD"
        return 1
    fi

    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1 && check_python_version "$cmd"; then
            echo "$cmd"
            return 0
        fi
    done

    return 1
}

ensure_project_root() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local root_dir
    root_dir="$(cd "$script_dir/.." && pwd)"

    cd "$root_dir"

    if [[ ! -f "pyproject.toml" ]]; then
        print_error "pyproject.toml not found; expected project root: $root_dir"
        exit 1
    fi
}

resolve_mode() {
    if [[ "$MODE" == "auto" ]]; then
        if command -v uv >/dev/null 2>&1; then
            MODE="uv"
        else
            MODE="pip"
        fi
    fi

    if [[ "$MODE" == "uv" ]] && ! command -v uv >/dev/null 2>&1; then
        print_error "uv mode requested but uv is not installed"
        exit 1
    fi
}

build_pip_spec() {
    local extras=()

    if [[ "$WITH_DEV" == true ]]; then
        extras+=("dev")
    fi
    if [[ "$WITH_TRACING" == true ]]; then
        extras+=("tracing")
    fi

    if [[ ${#extras[@]} -eq 0 ]]; then
        echo "."
    else
        local joined
        joined=$(IFS=,; echo "${extras[*]}")
        echo ".[${joined}]"
    fi
}

setup_with_uv() {
    print_header "Setup mode: uv"

    local args=("sync")

    if [[ "$WITH_DEV" == true ]]; then
        args+=("--extra" "dev")
    fi
    if [[ "$WITH_TRACING" == true ]]; then
        args+=("--extra" "tracing")
    fi
    if [[ "$FORCE" == true ]]; then
        args+=("--reinstall")
    fi

    print_step "Running: uv ${args[*]}"
    uv "${args[@]}"
    print_success "Dependencies synchronized via uv"
}

setup_with_pip() {
    print_header "Setup mode: pip + venv"

    local python_cmd
    python_cmd="$(find_python)" || {
        print_error "Python 3.11+ is required"
        exit 1
    }

    print_step "Using Python: $($python_cmd --version 2>&1)"

    if [[ -d "$VENV_DIR" && "$FORCE" == true ]]; then
        print_warning "Removing existing virtual environment: $VENV_DIR"
        rm -rf "$VENV_DIR"
    fi

    if [[ ! -d "$VENV_DIR" ]]; then
        print_step "Creating virtual environment: $VENV_DIR"
        "$python_cmd" -m venv "$VENV_DIR"
    else
        print_step "Virtual environment already exists: $VENV_DIR"
    fi

    local venv_python="$VENV_DIR/bin/python"
    if [[ ! -x "$venv_python" ]]; then
        print_error "Python binary not found in virtualenv: $venv_python"
        exit 1
    fi

    print_step "Upgrading pip/setuptools/wheel"
    "$venv_python" -m pip install --upgrade pip setuptools wheel

    local install_spec
    install_spec="$(build_pip_spec)"
    print_step "Installing package spec: $install_spec"
    "$venv_python" -m pip install -e "$install_spec"

    print_success "Dependencies installed in $VENV_DIR"
    print_step "Activate with: source $VENV_DIR/bin/activate"
}

create_env_file_if_missing() {
    print_header "Environment file"

    if [[ -f ".env" ]]; then
        print_step ".env already exists"
        return 0
    fi

    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        print_success "Created .env from .env.example"
        print_warning "Review secrets/settings in .env before running pipelines"
    else
        print_warning ".env.example not found; skipping .env creation"
    fi
}

verify_installation() {
    print_header "Verification"

    if [[ "$MODE" == "uv" ]]; then
        print_step "Checking import through uv run"
        uv run python -c "import bioetl; print(bioetl.__version__)"
    else
        local venv_python="$VENV_DIR/bin/python"
        print_step "Checking import through venv python"
        "$venv_python" -c "import bioetl; print(bioetl.__version__)"
    fi

    print_success "BioETL environment is ready"
}

main() {
    ensure_project_root
    parse_args "$@"
    resolve_mode

    print_header "BioETL environment setup"
    print_step "Mode: $MODE"
    print_step "Extras: dev=$WITH_DEV, tracing=$WITH_TRACING"

    if [[ "$MODE" == "uv" ]]; then
        setup_with_uv
    else
        setup_with_pip
    fi

    create_env_file_if_missing
    verify_installation
}

main "$@"
