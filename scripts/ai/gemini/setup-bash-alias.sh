#!/usr/bin/env bash
# Optional: Add to ~/.bashrc or ~/.bash_aliases for quick access to Gemini
# This enables: `gemini` and `gemini "prompt"` from anywhere

# Find repo root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
GEMINI_SCRIPT="${REPO_ROOT}/scripts/ai/gemini/gemini-interactive.sh"

if [[ -x "${GEMINI_SCRIPT}" ]]; then
    # Create function
    gemini() {
        local rc=0
        bash "${GEMINI_SCRIPT}" "$@"
        rc=$?
        return "${rc}"
    }
    
    export -f gemini
    
    echo "[OK] Gemini alias installed: 'gemini' command is now available"
    echo "     Try: gemini"
    echo "     Or:  gemini \"your prompt here\""
    return 0
else
    echo "[ERROR] Gemini launcher not found at ${GEMINI_SCRIPT}" >&2
    return 1
fi
