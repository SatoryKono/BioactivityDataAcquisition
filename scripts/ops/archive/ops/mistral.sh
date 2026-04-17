#!/usr/bin/env bash
# Launch Mistral Vibe from WSL in the current repository.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"

if [[ -f "${HOME}/.local/bin/env" ]]; then
    # Ensure uv-installed user tools are available in fresh non-login shells.
    # shellcheck disable=SC1091
    source "${HOME}/.local/bin/env"
fi

if ! command -v vibe >/dev/null 2>&1; then
    echo "[mistral] ERROR: Mistral Vibe CLI not found in PATH"
    echo "[mistral] Install with one of:"
    echo "[mistral]   curl -LsSf https://mistral.ai/vibe/install.sh | bash"
    echo "[mistral]   python3 -m pip install --user mistral-vibe"
    exit 1
fi

if [[ $# -eq 0 ]]; then
    echo "[mistral] Starting interactive mode in ${REPO_ROOT}"
    exec vibe --workdir "${REPO_ROOT}"
fi

echo "[mistral] Prompt: $*"
exec vibe --workdir "${REPO_ROOT}" "$@"
