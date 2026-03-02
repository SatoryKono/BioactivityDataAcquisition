#!/bin/bash
# Wrapper: injects GitHub token from gh CLI into MCP server
export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token 2>/dev/null)
exec npx -y @modelcontextprotocol/server-github "$@"
