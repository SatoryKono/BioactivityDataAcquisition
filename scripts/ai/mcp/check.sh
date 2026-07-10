#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
PROJECT_MCP_CONFIG="${REPO_ROOT}/.mcp.json"
EXPECTED_MEMORY_PATH="${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json"
EXPECTED_GITHUB_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/github-mcp-wrapper.sh"
EXPECTED_DOCKER_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_docker_wrapper.sh"
EXPECTED_CONTEXT7_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_context7_wrapper.sh"
EXPECTED_AST_GREP_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_ast_grep_wrapper.sh"
EXPECTED_CODE_INTERPRETER_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_code_interpreter_wrapper.sh"
EXPECTED_PROMETHEUS_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_prometheus_wrapper.sh"
EXPECTED_GRAFANA_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_grafana_wrapper.sh"
EXPECTED_BRAVE_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_brave_search_wrapper.sh"
EXPECTED_NEO4J_CYPHER_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_neo4j_cypher_wrapper.sh"
EXPECTED_NEO4J_MEMORY_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh"
EXPECTED_MERMAID_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_mermaid_wrapper.sh"
EXPECTED_FILESYSTEM_SCOPE="${REPO_ROOT}"
# shellcheck source=./support/load_repo_env.sh
source "${SCRIPT_DIR}/support/load_repo_env.sh"

load_repo_env_if_present

if command -v python3 >/dev/null 2>&1 && [[ -f "$PROJECT_MCP_CONFIG" ]]; then
  expected_values="$(
    python3 - "$PROJECT_MCP_CONFIG" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
data = json.loads(config_path.read_text(encoding="utf-8"))
servers = data.get("mcpServers", {})

def resolve_project_path(value: object) -> str:
    path = Path(str(value))
    if path.is_absolute():
        return str(path)
    return str((config_path.parent / path).resolve())

keys = [
    ("EXPECTED_MEMORY_PATH", ("memory", "env", "MEMORY_FILE_PATH")),
    ("EXPECTED_GITHUB_WRAPPER_PATH", ("github", "args", 0)),
    ("EXPECTED_DOCKER_WRAPPER_PATH", ("docker", "args", 0)),
    ("EXPECTED_CONTEXT7_WRAPPER_PATH", ("context7", "args", 0)),
    ("EXPECTED_AST_GREP_WRAPPER_PATH", ("ast-grep", "args", 0)),
    ("EXPECTED_CODE_INTERPRETER_WRAPPER_PATH", ("mcp-code-interpreter", "args", 0)),
    ("EXPECTED_PROMETHEUS_WRAPPER_PATH", ("prometheus", "args", 0)),
    ("EXPECTED_GRAFANA_WRAPPER_PATH", ("grafana", "args", 0)),
    ("EXPECTED_BRAVE_WRAPPER_PATH", ("brave-search", "args", 0)),
    ("EXPECTED_NEO4J_CYPHER_WRAPPER_PATH", ("neo4j-cypher", "args", 0)),
    ("EXPECTED_NEO4J_MEMORY_WRAPPER_PATH", ("neo4j-memory", "args", 0)),
    ("EXPECTED_MERMAID_WRAPPER_PATH", ("mermaid", "args", 0)),
    ("EXPECTED_FILESYSTEM_SCOPE", ("filesystem", "args", 2)),
]

for env_name, path in keys:
    value = servers
    for segment in path:
        value = value[segment]
    print(f"{env_name}={resolve_project_path(value)}")
PY
  )"

  while IFS='=' read -r name value; do
    [[ -n "${name}" ]] || continue
    printf -v "${name}" '%s' "${value}"
  done <<<"$expected_values"
fi

ok() {
  local message="${1:-}"
  printf "[OK] %s\n" "$message"
  return 0
}

warn() {
  local message="${1:-}"
  printf "[WARN] %s\n" "$message"
  return 0
}

fail() {
  local message="${1:-}"
  printf "[FAIL] %s\n" "$message" >&2
  return 1
}

require_contains() {
  local text="$1"
  local pattern="$2"
  local message="$3"
  if grep -Fq -- "$pattern" <<<"$text"; then
    ok "$message"
    return 0
  else
    fail "$message"
    return 1
  fi
}

require_wrapper_path() {
  local text="$1"
  local expected_path="$2"
  local message="$3"
  require_contains "$text" "args: ${expected_path}" "$message"
  return $?
}

validate_wrapper_if_possible() {
  local server="$1"
  local wrapper="$2"
  shift 2

  local missing=()
  local required_name
  for required_name in "$@"; do
    if [[ -z "${!required_name:-}" ]]; then
      missing+=("${required_name}")
    fi
  done

  if (( ${#missing[@]} > 0 )); then
    warn "Skipping ${server} wrapper token preflight; missing required env: ${missing[*]}"
    return 0
  fi

  if BIOETL_MCP_VALIDATE_ONLY=1 "${wrapper}" >/dev/null; then
    ok "${server} wrapper token preflight passed"
  else
    fail "${server} wrapper token preflight failed"
    return 1
  fi
}

if ! command -v codex >/dev/null 2>&1; then
  fail "codex CLI not found in PATH"
  exit 1
fi

status=0

list_out="$(codex mcp list 2>&1 || true)"
if grep -Eq "No MCP servers configured|Error:" <<<"$list_out"; then
  fail "Unable to read MCP server list"
  printf "%s\n" "$list_out" >&2
  exit 1
fi

printf "=== MCP server list ===\n%s\n\n" "$list_out"

for server in memory filesystem fetch github docker context7 ast-grep mcp-code-interpreter prometheus grafana brave-search neo4j-cypher neo4j-memory mermaid biomoltechDocs mintlify deepwiki; do
  if grep -Eq "^${server}[[:space:]]" <<<"$list_out"; then
    ok "Server '${server}' is registered"
  else
    fail "Server '${server}' is missing"
    status=1
  fi
done

memory_out="$(codex mcp get memory 2>&1 || true)"
filesystem_out="$(codex mcp get filesystem 2>&1 || true)"
fetch_out="$(codex mcp get fetch 2>&1 || true)"
github_out="$(codex mcp get github 2>&1 || true)"
docker_out="$(codex mcp get docker 2>&1 || true)"
context7_out="$(codex mcp get context7 2>&1 || true)"
ast_grep_out="$(codex mcp get ast-grep 2>&1 || true)"
code_interpreter_out="$(codex mcp get mcp-code-interpreter 2>&1 || true)"
prometheus_out="$(codex mcp get prometheus 2>&1 || true)"
grafana_out="$(codex mcp get grafana 2>&1 || true)"
brave_out="$(codex mcp get brave-search 2>&1 || true)"
neo4j_cypher_out="$(codex mcp get neo4j-cypher 2>&1 || true)"
neo4j_memory_out="$(codex mcp get neo4j-memory 2>&1 || true)"
mermaid_out="$(codex mcp get mermaid 2>&1 || true)"
deepwiki_out="$(codex mcp get deepwiki 2>&1 || true)"

require_contains "$memory_out" "@modelcontextprotocol/server-memory@2026.1.26" "memory is pinned to @2026.1.26" || status=1
require_contains "$filesystem_out" "@modelcontextprotocol/server-filesystem@2026.1.14" "filesystem is pinned to @2026.1.14" || status=1
require_contains "$fetch_out" "mcp-server-fetch==2025.4.7" "fetch is pinned to mcp-server-fetch==2025.4.7" || status=1
require_wrapper_path "$github_out" "$EXPECTED_GITHUB_WRAPPER_PATH" "github is routed through the project wrapper" || status=1
require_wrapper_path "$docker_out" "$EXPECTED_DOCKER_WRAPPER_PATH" "docker is routed through the project wrapper" || status=1
require_wrapper_path "$context7_out" "$EXPECTED_CONTEXT7_WRAPPER_PATH" "context7 is routed through the project wrapper" || status=1
require_wrapper_path "$ast_grep_out" "$EXPECTED_AST_GREP_WRAPPER_PATH" "ast-grep is routed through the project wrapper" || status=1
require_wrapper_path "$code_interpreter_out" "$EXPECTED_CODE_INTERPRETER_WRAPPER_PATH" "mcp-code-interpreter is routed through the project wrapper" || status=1
require_wrapper_path "$prometheus_out" "$EXPECTED_PROMETHEUS_WRAPPER_PATH" "prometheus is routed through the project wrapper" || status=1
require_wrapper_path "$grafana_out" "$EXPECTED_GRAFANA_WRAPPER_PATH" "grafana is routed through the project wrapper" || status=1
require_wrapper_path "$brave_out" "$EXPECTED_BRAVE_WRAPPER_PATH" "brave-search is routed through the project wrapper" || status=1
require_wrapper_path "$neo4j_cypher_out" "$EXPECTED_NEO4J_CYPHER_WRAPPER_PATH" "neo4j-cypher is routed through the project wrapper" || status=1
require_wrapper_path "$neo4j_memory_out" "$EXPECTED_NEO4J_MEMORY_WRAPPER_PATH" "neo4j-memory is routed through the project wrapper" || status=1
require_wrapper_path "$mermaid_out" "$EXPECTED_MERMAID_WRAPPER_PATH" "mermaid is routed through the project wrapper" || status=1
biomoltech_out="$(codex mcp get biomoltechDocs 2>&1 || true)"
mintlify_out="$(codex mcp get mintlify 2>&1 || true)"
require_contains "$biomoltech_out" "https://biomoltech.mintlify.app/mcp" "biomoltechDocs is registered as a remote Mintlify MCP" || status=1
require_contains "$mintlify_out" "https://mcp.mintlify.com" "mintlify is registered as the OAuth-enabled Mintlify MCP" || status=1
require_contains "$deepwiki_out" "https://mcp.deepwiki.com/mcp" "deepwiki is registered as the official DeepWiki MCP" || status=1

if grep -Fq -- "${EXPECTED_FILESYSTEM_SCOPE}" <<<"$filesystem_out"; then
  ok "filesystem scope is restricted to repo root"
else
  fail "filesystem scope is not restricted to ${EXPECTED_FILESYSTEM_SCOPE}"
  status=1
fi

if [[ -f "$EXPECTED_MEMORY_PATH" ]]; then
  ok "memory file exists at ${EXPECTED_MEMORY_PATH}"
else
  fail "memory file missing at ${EXPECTED_MEMORY_PATH}"
  status=1
fi

if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
  ok "GITHUB_PERSONAL_ACCESS_TOKEN is set (shell or .env)"
elif [[ -n "${GITHUB_TOKEN:-}" ]]; then
  ok "GITHUB_TOKEN is set and will be mapped for GitHub MCP auth"
else
  warn "Neither GITHUB_PERSONAL_ACCESS_TOKEN nor GITHUB_TOKEN is set (GitHub MCP auth may fail)"
fi

validate_wrapper_if_possible "github" "${EXPECTED_GITHUB_WRAPPER_PATH}" "GITHUB_PERSONAL_ACCESS_TOKEN" || status=1
validate_wrapper_if_possible "brave-search" "${EXPECTED_BRAVE_WRAPPER_PATH}" "BRAVE_API_KEY" || status=1
validate_wrapper_if_possible "prometheus" "${EXPECTED_PROMETHEUS_WRAPPER_PATH}" || status=1
validate_wrapper_if_possible "grafana" "${EXPECTED_GRAFANA_WRAPPER_PATH}" || status=1
validate_wrapper_if_possible "neo4j-cypher" "${EXPECTED_NEO4J_CYPHER_WRAPPER_PATH}" || status=1
validate_wrapper_if_possible "neo4j-memory" "${EXPECTED_NEO4J_MEMORY_WRAPPER_PATH}" || status=1

exit "$status"
