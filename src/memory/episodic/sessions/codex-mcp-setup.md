---
id: codex-mcp-setup
title: Configure MCP for Codex runtime
task_id: codex-mcp-setup
created_at: '2026-06-16T06:47:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
- scripts/ai/codex/setup_mcp.py
- scripts/ai/codex/helper/ensure-mcp.sh
- .mcp.json
- .codex/settings.json
summary: Active task session context.
query: mcp
---

# Session note

## Task

- Title: Configure MCP for Codex runtime
- Retrieval query: mcp

## Retrieved context

- Catalog hits: 0
- RAG hits: 4
- Timeline hits: 0

## Working notes

- Verified `.mcp.json`, `.vscode/mcp.json`, `.cursor/mcp.json`, and `.codex/settings.json`
  all reference the current repo root and the canonical wrapper paths.
- Verified `~/.codex/config.toml` already contains the managed MCP block for this
  workspace.
- `bash scripts/ai/codex/helper/ensure-mcp.sh --check` succeeded without drift.
- `codex mcp list --json` and `python3 -m scripts.ai.mcp check` both confirmed
  the expected servers are registered and enabled.
- No MCP config edits were required; only task-local memory notes changed.
