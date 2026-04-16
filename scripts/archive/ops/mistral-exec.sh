#!/usr/bin/env bash
# Launch Mistral Vibe in non-interactive prompt mode from WSL.

set -euo pipefail

if [[ $# -eq 0 ]]; then
    echo "Usage: mistral-exec.sh \"prompt\" [extra vibe flags]"
    echo
    echo "Example: mistral-exec.sh \"fix the failing architecture test\" --max-turns 5"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"

if [[ -f "${HOME}/.local/bin/env" ]]; then
    # Ensure uv-installed user tools are available in fresh non-login shells.
    # shellcheck disable=SC1091
    source "${HOME}/.local/bin/env"
fi

if ! command -v vibe >/dev/null 2>&1; then
    echo "[mistral-exec] ERROR: Mistral Vibe CLI not found in PATH"
    echo "[mistral-exec] Install with one of:"
    echo "[mistral-exec]   curl -LsSf https://mistral.ai/vibe/install.sh | bash"
    echo "[mistral-exec]   python3 -m pip install --user mistral-vibe"
    exit 1
fi

PROMPT="$1"
shift

echo "[mistral-exec] Prompt: ${PROMPT}"
exec vibe --workdir "${REPO_ROOT}" --prompt "${PROMPT}" "$@"
