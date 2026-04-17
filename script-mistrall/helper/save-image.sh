#!/usr/bin/env bash
# Helper: Save Ollama image to tar file for transfer
# Usage: ./save-image.sh

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
    local message="${1}"
    echo -e "${GREEN}[✓]${NC} ${message}"
    return 0
}

log_warn() {
    local message="${1}"
    echo -e "${YELLOW}[⚠]${NC} ${message}"
    return 0
}

log_error() {
    local message="${1}"
    echo -e "${RED}[✗]${NC} ${message}" >&2
    return 0
}

log_info() {
    local message="${1}"
    echo -e "${BLUE}[i]${NC} ${message}"
    return 0
}

echo ""
echo "=================================================="
echo "  Ollama Image - Save to Tar"
echo "=================================================="
echo ""

OUTPUT_FILE="${ROOT_DIR}/ollama-image.tar.gz"

log_info "Checking if ollama/ollama:latest exists..."
if ! docker image inspect ollama/ollama:latest >/dev/null 2>&1; then
    log_error "Image not found locally"
    log_info "Pull it first: docker pull ollama/ollama:latest"
    exit 1
fi

log_success "Image found"

log_info "Saving image to: ${OUTPUT_FILE}"
log_warn "This may take 2-5 minutes and create a ~2GB file..."
echo ""

if docker save ollama/ollama:latest | gzip > "${OUTPUT_FILE}"; then
    FILE_SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
    log_success "Image saved: ${OUTPUT_FILE} (${FILE_SIZE})"
    log_info "Transfer this file to target machine and run: ./load-image.sh"
else
    log_error "Failed to save image"
    exit 1
fi

exit 0
