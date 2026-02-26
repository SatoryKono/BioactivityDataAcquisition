#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting BioETL environment setup...${NC}"

# 1. Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv not found. Please install uv manually: https://github.com/astral-sh/uv${NC}"
    # Using return instead of exit to be safe in sourced scripts, though this runs in subshell
    false
else
    echo -e "${GREEN}uv is already installed.${NC}"
fi

# 2. Create Virtual Environment
echo -e "${BLUE}Creating virtual environment...${NC}"
uv venv

# 3. Install Dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
# Using --all-extras --dev to ensure full development environment
uv sync --all-extras --dev

# 4. Setup .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}.env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}.env file created.${NC}"
    else
        echo -e "${YELLOW}Warning: .env.example not found. Skipping .env creation.${NC}"
    fi
else
    echo -e "${GREEN}.env file already exists.${NC}"
fi

# 5. Setup Pre-commit
if [ -f .pre-commit-config.yaml ]; then
    echo -e "${BLUE}Setting up pre-commit hooks...${NC}"
    # Ensure we use the pre-commit installed in the venv
    uv run pre-commit install
else
    echo -e "${YELLOW}No .pre-commit-config.yaml found. Skipping pre-commit setup.${NC}"
fi

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}To activate the virtual environment, run:${NC}"
echo -e "source .venv/bin/activate"
