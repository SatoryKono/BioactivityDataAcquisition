#!/usr/bin/env bash
# Configure GitHub MCP for VS Code Copilot and Codex CLI.
set -euo pipefail

readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly VSCODE_MCP_PATH="${ROOT_DIR}/.vscode/mcp.json"
readonly GITHUB_MCP_PACKAGE="@modelcontextprotocol/server-github@2025.4.8"

print() {
    printf '%s\n' "$1"
}

print "[1/3] Writing VS Code MCP config: ${VSCODE_MCP_PATH}"
mkdir -p "$(dirname "${VSCODE_MCP_PATH}")"
cat > "${VSCODE_MCP_PATH}" <<'JSON'
{
  "servers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github@2025.4.8"
      ]
    }
  }
}
JSON

if ! command -v codex >/dev/null 2>&1; then
    print "[2/3] Codex CLI not found. Skipping Codex MCP registration."
    print "[3/3] Done."
    exit 0
fi

print "[2/3] Checking Codex MCP server registration: github"
if codex mcp get github >/dev/null 2>&1; then
    print "      github MCP already registered in Codex."
else
    codex mcp add github -- npx -y "${GITHUB_MCP_PACKAGE}"
    print "      github MCP registered in Codex."
fi

print "[3/3] Done."
print "Set GITHUB_PERSONAL_ACCESS_TOKEN in your shell before using GitHub MCP tools."
