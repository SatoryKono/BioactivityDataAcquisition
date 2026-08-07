#!/usr/bin/env bash
# Shared Codex auth probes for WSL launchers.
# Source this file; do not execute it directly.

# shellcheck shell=bash

codex_auth_file() {
    printf '%s\n' "${CODEX_HOME:-${HOME}/.codex}/auth.json"
}

codex_has_env_api_key() {
    [[ -n "${OPENAI_API_KEY:-}" ]] || return 1
    [[ "${OPENAI_API_KEY}" == sk-* ]] || return 1
    [[ "${OPENAI_API_KEY}" != sk-your-key-here ]] || return 1
    return 0
}

# True when ~/.codex/auth.json has usable ChatGPT tokens or a stored API key.
codex_has_persisted_auth() {
    local auth_file
    auth_file="$(codex_auth_file)"
    [[ -f "${auth_file}" ]] || return 1

    if command -v python3 >/dev/null 2>&1; then
        python3 - "${auth_file}" <<'PY'
import json
import sys

path = sys.argv[1]
try:
    data = json.load(open(path, encoding="utf-8"))
except Exception:
    raise SystemExit(1)

if data.get("OPENAI_API_KEY"):
    raise SystemExit(0)

if data.get("auth_mode") == "chatgpt":
    tokens = data.get("tokens") or {}
    if isinstance(tokens, dict) and tokens.get("access_token"):
        raise SystemExit(0)

raise SystemExit(1)
PY
        return $?
    fi

    # Fallback without Python: require a non-empty access_token field.
    grep -Eq '"access_token"[[:space:]]*:[[:space:]]*"[^"]+"' "${auth_file}" 2>/dev/null
}

codex_has_usable_auth() {
    codex_has_env_api_key || codex_has_persisted_auth
}

codex_auth_status_label() {
    if codex_has_env_api_key; then
        printf '%s\n' "api-key"
        return 0
    fi
    if codex_has_persisted_auth; then
        printf '%s\n' "chatgpt-auth"
        return 0
    fi
    printf '%s\n' "missing"
    return 1
}
