#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
EXPECTED_MEMORY_PATH="${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json"
EXPECTED_GITHUB_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/github-mcp-wrapper.sh"
EXPECTED_DOCKER_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_docker_wrapper.sh"
EXPECTED_DOCKER_DOCS_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_docker_docs_wrapper.sh"
EXPECTED_CONTEXT7_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_context7_wrapper.sh"
EXPECTED_PAPER_SEARCH_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_paper_search_wrapper.sh"
EXPECTED_DOCKERHUB_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_dockerhub_wrapper.sh"
EXPECTED_PROMETHEUS_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_prometheus_wrapper.sh"
EXPECTED_GRAFANA_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_grafana_wrapper.sh"
EXPECTED_BRAVE_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_brave_search_wrapper.sh"
EXPECTED_SONARQUBE_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_sonarqube_wrapper.sh"
EXPECTED_NEO4J_CYPHER_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_neo4j_cypher_wrapper.sh"
EXPECTED_NEO4J_MEMORY_WRAPPER_PATH="${REPO_ROOT}/scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh"
# shellcheck source=./support/load_repo_env.sh
source "${SCRIPT_DIR}/support/load_repo_env.sh"

load_repo_env_if_present

ok() {
  printf "[OK] %s\n" "$1"
}

warn() {
  printf "[WARN] %s\n" "$1"
}

fail() {
  printf "[FAIL] %s\n" "$1" >&2
}

require_contains() {
  local text="$1"
  local pattern="$2"
  local message="$3"
  if grep -Fq -- "$pattern" <<<"$text"; then
    ok "$message"
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

for server in memory filesystem sequential-thinking fetch pdf github docker docker-docs context7 paper-search dockerhub prometheus grafana brave-search neo4j-cypher neo4j-memory openaiDeveloperDocs; do
  if grep -Eq "^${server}[[:space:]]" <<<"$list_out"; then
    ok "Server '${server}' is registered"
  else
    fail "Server '${server}' is missing"
    status=1
  fi
done

memory_out="$(codex mcp get memory 2>&1 || true)"
filesystem_out="$(codex mcp get filesystem 2>&1 || true)"
sequential_out="$(codex mcp get sequential-thinking 2>&1 || true)"
fetch_out="$(codex mcp get fetch 2>&1 || true)"
pdf_out="$(codex mcp get pdf 2>&1 || true)"
github_out="$(codex mcp get github 2>&1 || true)"
docker_out="$(codex mcp get docker 2>&1 || true)"
docker_docs_out="$(codex mcp get docker-docs 2>&1 || true)"
context7_out="$(codex mcp get context7 2>&1 || true)"
paper_search_out="$(codex mcp get paper-search 2>&1 || true)"
dockerhub_out="$(codex mcp get dockerhub 2>&1 || true)"
prometheus_out="$(codex mcp get prometheus 2>&1 || true)"
grafana_out="$(codex mcp get grafana 2>&1 || true)"
brave_out="$(codex mcp get brave-search 2>&1 || true)"
sonarqube_out="$(codex mcp get sonarqube 2>&1 || true)"
neo4j_cypher_out="$(codex mcp get neo4j-cypher 2>&1 || true)"
neo4j_memory_out="$(codex mcp get neo4j-memory 2>&1 || true)"
openai_docs_out="$(codex mcp get openaiDeveloperDocs 2>&1 || true)"

require_contains "$memory_out" "@modelcontextprotocol/server-memory@2026.1.26" "memory is pinned to @2026.1.26" || status=1
require_contains "$filesystem_out" "@modelcontextprotocol/server-filesystem@2026.1.14" "filesystem is pinned to @2026.1.14" || status=1
require_contains "$sequential_out" "@modelcontextprotocol/server-sequential-thinking@2025.12.18" "sequential-thinking is pinned to @2025.12.18" || status=1
require_contains "$fetch_out" "mcp-server-fetch==2025.4.7" "fetch is pinned to mcp-server-fetch==2025.4.7" || status=1
require_contains "$pdf_out" "@modelcontextprotocol/server-pdf@1.3.1" "pdf is pinned to @1.3.1" || status=1
require_wrapper_path "$github_out" "$EXPECTED_GITHUB_WRAPPER_PATH" "github is routed through the project wrapper" || status=1
require_wrapper_path "$docker_out" "$EXPECTED_DOCKER_WRAPPER_PATH" "docker is routed through the project wrapper" || status=1
require_wrapper_path "$docker_docs_out" "$EXPECTED_DOCKER_DOCS_WRAPPER_PATH" "docker-docs is routed through the project wrapper" || status=1
require_wrapper_path "$context7_out" "$EXPECTED_CONTEXT7_WRAPPER_PATH" "context7 is routed through the project wrapper" || status=1
require_wrapper_path "$paper_search_out" "$EXPECTED_PAPER_SEARCH_WRAPPER_PATH" "paper-search is routed through the project wrapper" || status=1
require_wrapper_path "$dockerhub_out" "$EXPECTED_DOCKERHUB_WRAPPER_PATH" "dockerhub is routed through the project wrapper" || status=1
require_wrapper_path "$prometheus_out" "$EXPECTED_PROMETHEUS_WRAPPER_PATH" "prometheus is routed through the project wrapper" || status=1
require_wrapper_path "$grafana_out" "$EXPECTED_GRAFANA_WRAPPER_PATH" "grafana is routed through the project wrapper" || status=1
require_wrapper_path "$brave_out" "$EXPECTED_BRAVE_WRAPPER_PATH" "brave-search is routed through the project wrapper" || status=1
require_wrapper_path "$sonarqube_out" "$EXPECTED_SONARQUBE_WRAPPER_PATH" "sonarqube is routed through the project wrapper" || status=1
require_wrapper_path "$neo4j_cypher_out" "$EXPECTED_NEO4J_CYPHER_WRAPPER_PATH" "neo4j-cypher is routed through the project wrapper" || status=1
require_wrapper_path "$neo4j_memory_out" "$EXPECTED_NEO4J_MEMORY_WRAPPER_PATH" "neo4j-memory is routed through the project wrapper" || status=1
require_contains "$openai_docs_out" "https://developers.openai.com/mcp" "openaiDeveloperDocs points to official OpenAI MCP endpoint" || status=1

if grep -Fq -- "${REPO_ROOT}" <<<"$filesystem_out"; then
  ok "filesystem scope is restricted to repo root"
else
  fail "filesystem scope is not restricted to ${REPO_ROOT}"
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
else
  warn "GITHUB_PERSONAL_ACCESS_TOKEN is not set in shell or .env (GitHub MCP auth may fail)"
fi

exit "$status"
