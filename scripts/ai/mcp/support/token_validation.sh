#!/usr/bin/env bash

mcp_warn() {
  printf 'warning: %s\n' "$*" >&2
  return 0
}

mcp_fail() {
  printf 'error: %s\n' "$*" >&2
  return 1
}

mcp_validate_required_token() {
  local name="$1"
  local min_length="$2"
  local purpose="$3"
  shift 3

  local value="${!name:-}"
  if [[ -z "${value}" ]]; then
    mcp_fail "${name} is required for ${purpose}. Configure it in the shell or local .env; do not commit secrets."
    return 1
  fi

  if (( ${#value} < min_length )); then
    mcp_fail "${name} for ${purpose} is too short; expected at least ${min_length} characters."
    return 1
  fi

  if (( $# > 0 )); then
    local matched=0
    local prefix
    for prefix in "$@"; do
      if [[ "${value}" == "${prefix}"* ]]; then
        matched=1
        break
      fi
    done
    if (( matched == 0 )); then
      mcp_warn "${name} for ${purpose} has a non-standard prefix; verify token source and scopes."
    fi
  fi
  return 0
}

mcp_validate_optional_token() {
  local name="$1"
  local min_length="$2"
  local purpose="$3"
  shift 3

  local value="${!name:-}"
  if [[ -z "${value}" ]]; then
    mcp_warn "${name} is not set for ${purpose}; continuing with unauthenticated or local-default behavior."
    return 0
  fi

  if (( ${#value} < min_length )); then
    mcp_warn "${name} for ${purpose} is shorter than expected; verify the configured secret."
  fi

  if (( $# > 0 )); then
    local matched=0
    local prefix
    for prefix in "$@"; do
      if [[ "${value}" == "${prefix}"* ]]; then
        matched=1
        break
      fi
    done
    if (( matched == 0 )); then
      mcp_warn "${name} for ${purpose} has a non-standard prefix; verify token source and scopes."
    fi
  fi
  return 0
}

mcp_validate_neo4j_credentials() {
  local purpose="$1"
  if [[ -z "${NEO4J_URI:-}" ]]; then
    mcp_warn "NEO4J_URI is not set for ${purpose}; wrapper will use its local default."
  fi
  if [[ -z "${NEO4J_USERNAME:-}" ]]; then
    mcp_warn "NEO4J_USERNAME is not set for ${purpose}; wrapper will fail closed."
  fi
  if [[ -z "${NEO4J_PASSWORD:-}" ]]; then
    mcp_warn "NEO4J_PASSWORD is not set for ${purpose}; wrapper will fail closed."
  elif [[ "${NEO4J_PASSWORD}" == *_secure_password ]]; then
    mcp_warn "NEO4J_PASSWORD for ${purpose} matches a legacy placeholder pattern; rotate it."
  fi
  return 0
}

mcp_exit_if_validate_only() {
  local server_name="$1"
  if [[ "${BIOETL_MCP_VALIDATE_ONLY:-0}" == "1" ]]; then
    printf '[OK] %s MCP wrapper validation completed\n' "${server_name}"
    exit 0
  fi
  return 0
}
