#!/usr/bin/env bash
# setup.sh - Environment setup script for BioETL
# Usage: ./scripts/setup.sh
#
# This script sets up the development environment using uv (preferred) or pip as fallback.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python version
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.11+"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    REQUIRED_VERSION="3.11"

    if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
        log_error "Python $REQUIRED_VERSION+ is required, but found $PYTHON_VERSION"
        exit 1
    fi

    log_info "Python $PYTHON_VERSION detected"
}

# Setup using uv (preferred)
setup_with_uv() {
    log_info "Setting up environment with uv..."

    if ! command -v uv &> /dev/null; then
        log_info "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add uv to PATH for current session
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    log_info "Installing dependencies with uv..."
    uv sync --extra dev --extra tracing

    log_success "Environment setup complete with uv!"
    log_info "Run tests with: uv run pytest tests/ -v"
}

# Setup using pip (fallback)
setup_with_pip() {
    log_info "Setting up environment with pip..."

    VENV_DIR=".venv"

    # Create virtual environment if it doesn't exist
    if [[ ! -d "$VENV_DIR" ]]; then
        log_info "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi

    # Determine the correct path for pip/python based on OS
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        VENV_BIN="$VENV_DIR/Scripts"
    else
        VENV_BIN="$VENV_DIR/bin"
    fi

    log_info "Upgrading pip..."
    "$VENV_BIN/pip" install --upgrade pip setuptools wheel

    log_info "Installing dependencies..."
    "$VENV_BIN/pip" install -e ".[dev,tracing]"

    log_success "Environment setup complete with pip!"
    log_info "Activate the environment with: source $VENV_BIN/activate"
    log_info "Run tests with: $VENV_BIN/pytest tests/ -v"
}

# Main
main() {
    log_info "BioETL Development Environment Setup"
    echo ""

    check_python

    # Prefer uv if available or if --uv flag is passed
    if [[ "${1:-}" == "--uv" ]] || command -v uv &> /dev/null; then
        setup_with_uv
    elif [[ "${1:-}" == "--pip" ]]; then
        setup_with_pip
    else
        # Default: try uv first, fall back to pip
        if command -v curl &> /dev/null; then
            setup_with_uv
        else
            log_warn "curl not available, falling back to pip"
            setup_with_pip
        fi
    fi

    echo ""
    log_success "Setup complete! You can now run tests."
}

main "$@"
