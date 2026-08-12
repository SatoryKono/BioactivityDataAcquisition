#!/usr/bin/env bash

load_repo_env_if_present() {
  if [[ "${BIOETL_REPO_ENV_LOADED:-0}" == "1" ]]; then
    normalize_repo_env_aliases
    return $?
  fi

  local script_dir repo_root env_file env_local_file load_env_local
  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  repo_root="$(cd -- "${script_dir}/../../.." && pwd)"
  env_file="${BIOETL_ENV_FILE:-${repo_root}/.env}"
  env_local_file="${repo_root}/.env.local"
  load_env_local="${BIOETL_SKIP_ENV_LOCAL:-0}"

  if [[ "${load_env_local}" == "1" ]]; then
    env_local_file=""
  fi

  if [[ ! -f "${env_file}" && ! -f "${env_local_file}" ]]; then
    export BIOETL_REPO_ENV_LOADED=1
    normalize_repo_env_aliases
    return $?
  fi

  # Try Python-based loading first (most reliable)
  local python_bin
  python_bin="$(command -v python3 || command -v python || true)"

  if [[ -n "${python_bin}" ]]; then
    # Python version (original)
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
      printf -v "${key}" '%s' "${value}"
      export "${key}"
    done < <(
      "${python_bin}" - "${env_file}" "${env_local_file}" <<'PY'
from __future__ import annotations

import re
import os
import sys
from pathlib import Path

env_paths = [Path(p) for p in sys.argv[1:]]
shell_keys = set()
for key in os.environ:
    if os.environ.get(key):
        shell_keys.add(key)

values: dict[str, str] = {}
for env_path in env_paths:
    if not env_path.is_file():
        continue

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw:
            continue

        key, value = raw.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue

        if key in shell_keys:
            continue

        value = value.strip()
        if not value:
            parsed = ""
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            parsed = value[1:-1]
        else:
            parsed = re.sub(r"\s+#.*$", "", value).rstrip()

        values[key] = parsed

for key, parsed in values.items():
    sys.stdout.write(key)
    sys.stdout.write("\0")
    sys.stdout.write(parsed)
    sys.stdout.write("\0")
PY
    )
  else
    # Fallback: Pure bash parsing (no Python required)
    local -A env_vars

    # Load .env first
    if [[ -f "${env_file}" ]]; then
      while IFS='=' read -r key value; do
        key="${key##*( )}"      # Trim leading whitespace
        key="${key%%*( )}"      # Trim trailing whitespace

        # Skip empty lines and comments
        [[ -z "${key}" || "${key}" == "#"* ]] && continue

        # Trim value
        value="${value##*( )}"
        value="${value%%*( )}"

        # Remove quotes if present
        if [[ "${value}" =~ ^['\"](.*)['\"']$ ]]; then
          value="${BASH_REMATCH[1]}"
        else
          # Remove inline comments
          value="${value%% #*}"
          value="${value%%*( )}"
        fi

        env_vars["${key}"]="${value}"
      done < "${env_file}"
    fi

    # Load .env.local (overrides .env)
    if [[ -f "${env_local_file}" ]]; then
      while IFS='=' read -r key value; do
        key="${key##*( )}"
        key="${key%%*( )}"

        [[ -z "${key}" || "${key}" == "#"* ]] && continue

        value="${value##*( )}"
        value="${value%%*( )}"

        if [[ "${value}" =~ ^['\"](.*)['\"']$ ]]; then
          value="${BASH_REMATCH[1]}"
        else
          value="${value%% #*}"
          value="${value%%*( )}"
        fi

        env_vars["${key}"]="${value}"
      done < "${env_local_file}"
    fi

    # Export all loaded variables
    for key in "${!env_vars[@]}"; do
      if [[ -z "${!key:-}" ]]; then
        export "${key}=${env_vars[${key}]}"
      fi
    done
  fi

  export BIOETL_REPO_ENV_LOADED=1
  normalize_repo_env_aliases
}

normalize_neo4j_auth_aliases() {
  if [[ -z "${NEO4J_AUTH:-}" ]]; then
    return 0
  fi

  local parsed_username parsed_password
  if [[ "${NEO4J_AUTH}" != */* ]]; then
    printf 'error: NEO4J_AUTH must use non-empty username/password format\n' >&2
    return 1
  fi

  parsed_username="${NEO4J_AUTH%%/*}"
  parsed_password="${NEO4J_AUTH#*/}"
  if [[ -z "${parsed_username}" || -z "${parsed_password}" ]]; then
    printf 'error: NEO4J_AUTH must use non-empty username/password format\n' >&2
    return 1
  fi

  if [[ -n "${NEO4J_USERNAME:-}" && -n "${NEO4J_PASSWORD:-}" ]]; then
    return 0
  fi

  export NEO4J_USERNAME="${NEO4J_USERNAME:-${parsed_username}}"
  export NEO4J_PASSWORD="${NEO4J_PASSWORD:-${parsed_password}}"
}

normalize_repo_env_aliases() {
  # Rewrite unusable NPM cache paths (foreign home dirs, missing parents that
  # cannot be created). Keep the configured value when the directory is writable.
  if [[ -n "${NPM_CONFIG_CACHE:-}" ]]; then
    if ! mkdir -p "${NPM_CONFIG_CACHE}" 2>/dev/null; then
      local _npm_fallback="${TMPDIR:-/tmp}/bioetl-npm-cache"
      export NPM_CONFIG_CACHE="${_npm_fallback}"
      mkdir -p "${NPM_CONFIG_CACHE}" 2>/dev/null || true
    fi
    export npm_config_cache="${NPM_CONFIG_CACHE}"
  fi

  if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
    export GITHUB_PERSONAL_ACCESS_TOKEN="${GITHUB_TOKEN}"
  fi
  if [[ -z "${GITHUB_TOKEN:-}" && -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
    export GITHUB_TOKEN="${GITHUB_PERSONAL_ACCESS_TOKEN}"
  fi
  if [[ -z "${GITHUB_TOKEN:-}" && -n "${GH_TOKEN:-}" ]]; then
    export GITHUB_TOKEN="${GH_TOKEN}"
  fi
  if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" && -n "${GH_TOKEN:-}" ]]; then
    export GITHUB_PERSONAL_ACCESS_TOKEN="${GH_TOKEN}"
  fi

  if [[ -z "${NEEDLE_API_KEY:-}" && -n "${NEEDLE_TOKEN:-}" ]]; then
    export NEEDLE_API_KEY="${NEEDLE_TOKEN}"
  fi

  if [[ -z "${BRAVE_API_KEY:-}" ]]; then
    if [[ -n "${BRAVE_SEARCH_API_KEY:-}" ]]; then
      export BRAVE_API_KEY="${BRAVE_SEARCH_API_KEY}"
    elif [[ -n "${BRAVE_API_KEY1:-}" ]]; then
      export BRAVE_API_KEY="${BRAVE_API_KEY1}"
    fi
  fi

  if [[ -z "${REF_TOOL_API_KEY:-}" && -n "${REF_API_KEY:-}" ]]; then
    export REF_TOOL_API_KEY="${REF_API_KEY}"
  fi

  if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" && -n "${GITHUB_CDX_PERSONAL_ACCESS_TOKEN:-}" ]]; then
    export GITHUB_PERSONAL_ACCESS_TOKEN="${GITHUB_CDX_PERSONAL_ACCESS_TOKEN}"
  fi
  # Historical typo key kept for local compat only.
  if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" && -n "${GITHUB_ANY_PERSONAL_ADjCCESS_TOKEN:-}" ]]; then
    export GITHUB_PERSONAL_ACCESS_TOKEN="${GITHUB_ANY_PERSONAL_ADjCCESS_TOKEN}"
  fi

  if [[ -z "${CONTEXT7_API_KEY:-}" ]]; then
    if [[ -n "${CONTEXT7_API_TOKEN:-}" ]]; then
      export CONTEXT7_API_KEY="${CONTEXT7_API_TOKEN}"
    elif [[ -n "${UPSTASH_CONTEXT7_API_KEY:-}" ]]; then
      export CONTEXT7_API_KEY="${UPSTASH_CONTEXT7_API_KEY}"
    fi
  fi

  normalize_neo4j_auth_aliases || return 1
  if [[ -z "${NEO4J_URL:-}" && -n "${NEO4J_URI:-}" ]]; then
    export NEO4J_URL="${NEO4J_URI}"
  fi

  if [[ -z "${HUB_PAT_TOKEN:-}" ]]; then
    if [[ -n "${DOCKERHUB_PAT:-}" ]]; then
      export HUB_PAT_TOKEN="${DOCKERHUB_PAT}"
    elif [[ -n "${DOCKERHUB_TOKEN:-}" ]]; then
      export HUB_PAT_TOKEN="${DOCKERHUB_TOKEN}"
    elif [[ -n "${DOCKERHUB_PAT_TOKEN:-}" ]]; then
      export HUB_PAT_TOKEN="${DOCKERHUB_PAT_TOKEN}"
    elif [[ -n "${DOCKER_API_KEY:-}" ]]; then
      # Non-canonical alias used in some local .env files
      export HUB_PAT_TOKEN="${DOCKER_API_KEY}"
    fi
  fi
  if [[ -z "${DOCKERHUB_USERNAME:-}" && -n "${DOCKER_USERNAME:-}" ]]; then
    export DOCKERHUB_USERNAME="${DOCKER_USERNAME}"
  fi

  if [[ -z "${GRAFANA_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
    if [[ -n "${GRAFANA_TOKEN:-}" ]]; then
      export GRAFANA_SERVICE_ACCOUNT_TOKEN="${GRAFANA_TOKEN}"
    elif [[ -n "${GRAFANA_API_KEY:-}" ]]; then
      export GRAFANA_SERVICE_ACCOUNT_TOKEN="${GRAFANA_API_KEY}"
    fi
  fi
  if [[ -z "${GRAFANA_USERNAME:-}" && -n "${GF_SECURITY_ADMIN_USER:-}" ]]; then
    export GRAFANA_USERNAME="${GF_SECURITY_ADMIN_USER}"
  fi
  if [[ -z "${GRAFANA_PASSWORD:-}" && -n "${GF_SECURITY_ADMIN_PASSWORD:-}" ]]; then
    export GRAFANA_PASSWORD="${GF_SECURITY_ADMIN_PASSWORD}"
  fi
  return 0
}
