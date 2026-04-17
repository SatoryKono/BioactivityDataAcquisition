# Gemini + WSL Setup Guide

This document describes the Gemini runtime setup for BioETL, analogous to the existing Codex configuration.

## Overview

**Goal:** Launch Gemini from WSL with full MCP integration, agent profiles, and memory persistence—matching the Codex workflow.

**Key Files Created:**

| File | Purpose | Analogue |
|------|---------|---------|
| `.gemini/config.toml` | Runtime configuration | `.codex/config.toml` |
| `.gemini/settings.json` | MCP servers definition | `.codex/settings.json` |
| `.gemini/agents/GEMINI-RUNTIME.md` | Agent role mapping | `.codex/agents/CODEX-RUNTIME.md` |
| `scripts/ai/setup-gemini-wsl.sh` | Initialize Gemini environment | (new) |
| `scripts/ai/launch-gemini.sh` | Launch Gemini with context | (new) |
| `scripts/ai/sync-agents-codex-to-gemini.sh` | Sync profiles Codex → Gemini | (new) |

---

## Quick Start (WSL)

### 1. Initialize Gemini Environment

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2
bash scripts/ai/setup-gemini-wsl.sh
```

**What it does:**
- Creates `.gemini/agents/` and `.gemini/skills/` directories
- Initializes `gemini-memory.json` for persistent context
- Validates MCP server configuration
- Sets up environment variables

**Output:**
```
🔧 Setting up Gemini runtime for BioETL (WSL)...
📝 Initializing Gemini memory store...
🔗 Linking Codex agent profiles for reference...
✓ Node.js environment available
✓ UV environment available
✅ Gemini runtime setup complete!
```

### 2. Sync Agent Profiles from Codex

```bash
bash scripts/ai/sync-agents-codex-to-gemini.sh
```

**Copies these profiles to `.gemini/agents/`:**
- `py-audit-bot.md`
- `py-architecture-debt-bot.md`
- `py-config-bot.md`
- `py-debug-bot.md`
- `py-doc-bot.md`
- `py-plan-bot.md`
- `py-test-bot.md`
- `py-test-swarm.md`
- `py-review-orchestrator.md`

### 3. Activate Gemini Environment

```bash
source .gemini/.env.sh
```

**Sets:**
- `GEMINI_HOME` → `.gemini`
- `GEMINI_CONFIG` → `.gemini/config.toml`
- `GEMINI_MCP_SETTINGS` → `.gemini/settings.json`
- `GEMINI_MEMORY_FILE` → `docs/00-project/ai/memory/gemini-memory.json`

### 4. Launch Gemini

```bash
bash scripts/ai/launch-gemini.sh [profile] [mode]
```

**Examples:**

```bash
# Launch with default review orchestrator
bash scripts/ai/launch-gemini.sh py-review-orchestrator

# Launch with audit bot
bash scripts/ai/launch-gemini.sh py-audit-bot

# Launch with config bot (implementation role)
bash scripts/ai/launch-gemini.sh py-config-bot
```

---

## Configuration Reference

### `.gemini/config.toml`

```toml
model = "gemini-3.5-pro"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
model_reasoning_effort = "high"
web_search = "cached"

[sandbox_workspace_write]
network_access = true

[features]
experimental_windows_sandbox = true
shell_snapshot = true
streaming_enabled = true
```

**Key Settings:**
- **model**: Switch to `gemini-3.5-sonnet` or `gemini-pro` as needed
- **sandbox_mode**: `workspace-write` allows file modifications in project
- **streaming_enabled**: Enables progressive output for long tasks

### `.gemini/settings.json`

Defines all MCP (Model Context Protocol) servers:

| Server | Purpose | WSL Path |
|--------|---------|----------|
| `memory` | Persistent context across sessions | `/tmp/gemini-memory.json` |
| `filesystem` | Read/write project files | Project root |
| `neo4j-cypher` | Graph DB queries | Via wrapper script |
| `docker` | Docker container operations | Via wrapper script |
| `fetch` | HTTP/HTTPS requests | Via UV |
| `sequential-thinking` | Complex decomposition | Native |

**All WSL paths use Linux-style `/mnt/e/` prefixes for cross-environment compatibility.**

---

## Agent Role Mapping

Profile → Gemini Role Routing:

```
py-audit-bot, py-debug-bot, py-test-bot
  ↓
  research    (read-only, analytical)

py-config-bot, py-doc-bot
  ↓
  implementation    (write scope: configs/, docs/)

py-review-orchestrator, py-plan-bot, py-architecture-debt-bot
  ↓
  default    (orchestration, delegation)
```

See `.gemini/agents/GEMINI-RUNTIME.md` for full mapping.

---

## Memory Persistence

Gemini maintains a separate memory file from Codex:

```json
docs/00-project/ai/memory/gemini-memory.json
```

**Structure:**
```json
{
  "memories": {
    "project_context": {...},
    "custom_instructions": {...},
    "session_history": [...]
  }
}
```

This allows:
- ✓ Independent context between Codex and Gemini sessions
- ✓ Session continuity within Gemini
- ✓ Memory replay on agent restart

---

## Usage Patterns

### Pattern 1: Code Review

```bash
bash scripts/ai/launch-gemini.sh py-review-orchestrator
```

Then instruct Gemini:
```
Review staged changes against .gemini/agents/py-review-orchestrator.md
Focus on: architecture compliance, test coverage, GEMINI.md adherence
```

### Pattern 2: Configuration Audit

```bash
bash scripts/ai/launch-gemini.sh py-config-bot implementation
```

Then instruct:
```
Audit configs/ directory following .gemini/agents/py-config-bot.md
Scope: medallion architecture, null vs full_scan_only loading
```

### Pattern 3: Test Coverage Generation

```bash
bash scripts/ai/launch-gemini.sh py-test-swarm
```

Then instruct:
```
Generate missing tests per .gemini/agents/py-test-swarm.md
Target: 85% coverage in src/bioetl/application/
```

---

## Troubleshooting

### Issue: MCP servers not connecting

**Check:**
```bash
echo $GEMINI_MCP_SETTINGS
cat ${GEMINI_MCP_SETTINGS} | head -20
```

**Verify Node.js/UV installed:**
```bash
which node npm uvx
```

**Solution:**
If missing, install via:
```bash
# Node.js (in WSL)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs

# UV (in WSL)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Issue: Memory file not persisting

**Check:**
```bash
ls -la docs/00-project/ai/memory/gemini-memory.json
```

**Reset:**
```bash
bash scripts/ai/setup-gemini-wsl.sh
```

### Issue: Agent profiles not found

**Resync:**
```bash
bash scripts/ai/sync-agents-codex-to-gemini.sh
ls -la .gemini/agents/
```

---

## Maintenance

### Update MCP Servers

Edit `.gemini/settings.json`:
```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory@2026.2.0"]
    }
  }
}
```

Then restart Gemini.

### Sync New Agent Profiles

When `.codex/agents/` gets new `py-*` profiles:

```bash
bash scripts/ai/sync-agents-codex-to-gemini.sh
```

### Clear Memory and Reset

```bash
rm -f docs/00-project/ai/memory/gemini-memory.json
bash scripts/ai/setup-gemini-wsl.sh
```

---

## Key Differences: Gemini vs. Codex

| Aspect | Codex | Gemini |
|--------|-------|--------|
| Config file | `.codex/config.toml` | `.gemini/config.toml` |
| MCP settings | `.codex/settings.json` | `.gemini/settings.json` |
| Memory file | `mcp-memory.json` | `gemini-memory.json` |
| Agent routing | Enum-based (default/explorer/worker) | Role-based (research/implementation/default) |
| Model | GPT-5.4 | Gemini-3.5-Pro |
| Output | Request-based | Streaming-enabled |

---

## Next Steps

1. **Run setup:**
   ```bash
   bash scripts/ai/setup-gemini-wsl.sh
   ```

2. **Sync profiles:**
   ```bash
   bash scripts/ai/sync-agents-codex-to-gemini.sh
   ```

3. **Test launch:**
   ```bash
   source .gemini/.env.sh
   bash scripts/ai/launch-gemini.sh
   ```

4. **Create shell alias (optional):**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc:
   alias gemini-setup='bash ${PROJECT_ROOT}/scripts/ai/setup-gemini-wsl.sh'
   alias gemini-launch='bash ${PROJECT_ROOT}/scripts/ai/launch-gemini.sh'
   ```

---

## References

- `.gemini/agents/GEMINI-RUNTIME.md` — Full agent role mapping
- `.codex/agents/CODEX-RUNTIME.md` — Reference (Codex equivalent)
- `GEMINI.md` — Project constraints & governance rules
- `docs/00-project/ai/` — Shared AI utilities & memory
