#!/usr/bin/env bash
# Helper: Load Ollama image from tar file
# Usage: ./load-image.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() {
    local message="${1:-}"
    echo -e "${GREEN}[✓]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1:-}"
    echo -e "${YELLOW}[⚠]${NC} ${message}"
    return 0
}

log_error() {
    local message="${1:-}"
    echo -e "${RED}[✗]${NC} ${message}" >&2
    return 0
}

log_info() {
    local message="${1:-}"
    echo -e "${BLUE}[i]${NC} ${message}"
    return 0
}

echo ""
echo "=================================================="
echo "  Ollama Image - Load from Tar"
echo "=================================================="
echo ""

INPUT_FILE="${ROOT_DIR}/ollama-image.tar.gz"

if [[ ! -f "${INPUT_FILE}" ]]; then
    log_error "Image file not found: ${INPUT_FILE}"
    log_info "Transfer ollama-image.tar.gz to this directory first"
    exit 1
fi

FILE_SIZE=$(du -h "${INPUT_FILE}" | cut -f1)
log_info "Loading image from: ${INPUT_FILE} (${FILE_SIZE})"
log_warn "This may take 2-5 minutes..."
echo ""

if gunzip -c "${INPUT_FILE}" | docker load; then
    log_success "Image loaded successfully"
    
    # Verify
    if docker image inspect ollama/ollama:latest >/dev/null 2>&1; then
        log_success "Verification passed - image is ready"
        docker images --filter reference=ollama/ollama
    else
        log_warn "Image loaded but verification failed"
        exit 1
    fi
else
    log_error "Failed to load image"
    exit 1
fi

exit 0
