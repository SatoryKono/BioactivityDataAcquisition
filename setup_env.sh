#!/bin/bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✔ $1${NC}"
}

print_error() {
    echo -e "${RED}✖ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

main() {
    print_header "BioETL Environment Setup"

    # 1. Check/Install uv
    print_step "Checking uv..."
    if ! command -v uv &> /dev/null; then
        print_warning "uv not found. Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # Load env for current session
        if [ -f "$HOME/.cargo/env" ]; then
            source "$HOME/.cargo/env"
        else
            print_error "Failed to load uv environment. Please restart your shell."
            exit 1
        fi
    else
        print_success "uv is installed: $(uv --version)"
    fi

    # 2. Sync dependencies
    print_step "Syncing dependencies with uv..."
    # Using flags from Makefile/CI
    uv sync --extra dev --extra tracing --extra performance
    print_success "Dependencies synced."

    # 3. Setup .env
    print_step "Checking .env configuration..."
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            print_success "Created .env from .env.example"
        else
            print_warning ".env.example not found, skipping .env creation."
        fi
    else
        print_success ".env already exists."
    fi

    # 4. Setup pre-commit
    print_step "Setting up pre-commit hooks..."
    if [ -f .pre-commit-config.yaml ]; then
        uv run pre-commit install
        print_success "Pre-commit hooks installed."
    else
        print_warning "No .pre-commit-config.yaml found."
    fi

    # 5. Show environment info (The "Show in the screen" part)
    print_header "Environment Information"

    echo -e "${BLUE}Python Version:${NC}"
    uv run python --version

    echo -e "\n${BLUE}BioETL Version:${NC}"
    uv run python -c "import bioetl; print(f'BioETL v{bioetl.__version__}')" 2>/dev/null || echo "BioETL package not found/installed in editable mode"

    echo -e "\n${BLUE}Virtual Environment:${NC}"
    uv run python -c "import sys; print(sys.prefix)"

    echo -e "\n${BLUE}Installed Packages (Summary):${NC}"
    uv run pip list | head -n 10
    echo -e "... (use 'uv pip list' to see all)"

    print_header "Setup Complete!"
    echo -e "To activate the environment, use: ${GREEN}source .venv/bin/activate${NC}"
    echo -e "Or run commands with: ${GREEN}uv run <command>${NC}"
}

main
