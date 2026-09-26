# Neo4j Memory MCP Documentation Index

**Last Updated**: 2026-04-08
**Status**: MCP Registered, Backend Ready to Start

______________________________________________________________________

## 📚 Documentation Map

### Getting Started

1. **[NEO4J-MCP-SESSION-SUMMARY.md](NEO4J-MCP-SESSION-SUMMARY.md)** ⭐ **START HERE**
   - What was completed in this session
   - What remains (quick backend startup)
   - Quick reference commands
   - Architecture overview

### Implementation Guides

2. **[NEO4J-STARTUP-GUIDE.md](NEO4J-STARTUP-GUIDE.md)**

   - Step-by-step backend startup instructions
   - Docker Compose alternative
   - Container management commands
   - Environment variable configuration
   - Troubleshooting guide

1. **[NEO4J-COMPLETION-GUIDE.md](NEO4J-COMPLETION-GUIDE.md)**

   - Why MCP needs a running backend
   - Verification commands
   - Integration with Codex
   - Issue resolution

### Configuration & Operations

4. **[neo4j-memory-setup.md](neo4j-memory-setup.md)** (Pre-existing)
   - Memory configuration profiles (Dev, Staging, Production)
   - Memory allocation rules
   - Performance tuning
   - Health checks

### Project Configuration Files

| File                                                 | Purpose               | Status        |
| ---------------------------------------------------- | --------------------- | ------------- |
| `.mcp.json`                                          | Codex CLI MCP servers | ✅ Configured |
| `.vscode/mcp.json`                                   | VS Code Copilot MCP   | ✅ Configured |
| `scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh`         | MCP wrapper script    | ✅ Ready      |
| `python -m scripts.engineering.dev setup-mcp`        | Public MCP setup command | ✅ Updated |
| `.env.example`                                       | Environment template  | ✅ Updated    |

______________________________________________________________________

## 🚀 Quick Start (Copy-Paste)

### Step 1: Start Neo4j Backend

```bash
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait
```

### Step 2: Verify MCP Connection

```bash
# Check Codex registration
codex mcp get neo4j-memory

# Run full diagnostic
bash scripts/ai/mcp/check_neo4j_memory.sh

# (Optional) Quick start helper
bash scripts/ops/runtime/neo4j/neo4j_quick_start.sh
```

### Step 3: Access Neo4j Browser

```
http://localhost:7474/browser/
Username: neo4j
Password: required value from `NEO4J_PASSWORD`
```

### Step 4: Use in Codex

```bash
codex interactive
# Then use @neo4j-memory in prompts
```

______________________________________________________________________

## 📋 Verification Scripts

| Script                    | Location          | Purpose                                          |
| ------------------------- | ----------------- | ------------------------------------------------ |
| **check.sh**              | `scripts/ai/mcp/` | General MCP validation across registered servers |
| **check_neo4j_memory.sh** | `scripts/ai/mcp/` | Full Neo4j Memory MCP + backend health check     |
| **neo4j_quick_start.sh**  | `scripts/ops/`    | One-command startup & verification               |

### Run checks:

```bash
# General MCP validation
bash scripts/ai/mcp/check.sh

# Comprehensive Neo4j MCP diagnostic
bash scripts/ai/mcp/check_neo4j_memory.sh

# Quick startup with auto-verification
bash scripts/ops/runtime/neo4j/neo4j_quick_start.sh
```

______________________________________________________________________

## 🔧 Environment Variables

Used by `wrapper.sh`:

```bash
# Required local configuration
NEO4J_URI=bolt://localhost:7687           # Bolt connection string
NEO4J_USERNAME=neo4j                      # Username
NEO4J_PASSWORD=                           # Required local secret
NEO4J_DATABASE=neo4j                      # Database name

# Alternative (parses to above)
NEO4J_AUTH=                               # Optional derived username/password form

# Individual credential overrides
NEO4J_AUTH_USERNAME=neo4j
NEO4J_AUTH_PASSWORD=
```

Set via:

- `.env` file (recommended)
- Shell `export` (overrides `.env`)
- Docker `-e` flag (for container)

______________________________________________________________________

## 🏗️ Architecture

```
┌──────────────────────────────────┐
│     Codex / VS Code Copilot      │ ← AI clients
└────────────────────┬─────────────┘
                     │
                     ↓
        ┌────────────────────────┐
        │ neo4j-memory MCP Server│ ← MCP registered
        └────────────┬───────────┘
                     │
        ┌────────────┴──────────────┐
        │                           │
        ↓                           ↓
 scripts/ai/mcp/       wrapper reads env
 mcp_neo4j_memory_     (NEO4J_URI, etc.)
 wrapper.sh
        │
        └──→ @knowall-ai/mcp-neo4j-agent-memory
             │
             └──→ bolt://localhost:7687
                      │
                      ↓
        ┌──────────────────────────┐
        │  Neo4j 5.15-community    │ ← Backend
        │  (Docker container)      │
        │  • HTTP: 7474            │
        │  • Bolt: 7687            │
        └──────────────────────────┘
```

______________________________________________________________________

## ✅ Status Checklist

- [x] MCP registered in Codex CLI (`codex mcp list`)
- [x] Wrapper script created and configured
- [x] Environment variables documented
- [x] Verification scripts written
- [x] Documentation complete
- [ ] **Neo4j backend running** ← You are here

**To activate MCP:**

```bash
# 1. Start backend
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait

# 2. Verify
bash scripts/ai/mcp/check_neo4j_memory.sh
```

______________________________________________________________________

## 🔗 Related Resources

- **Neo4j Official**: https://neo4j.com/docs/
- **Neo4j Docker**: https://hub.docker.com/_/neo4j
- **MCP Specification**: https://modelcontextprotocol.io/
- **Project MCP Config**: `python -m scripts.engineering.dev setup-mcp`
- **Codex Documentation**: https://docs.docker.com/ai/docker-agent/

______________________________________________________________________

## 🆘 Troubleshooting

**Problem**: `codex mcp get neo4j-memory` fails

- Solution: Run `docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d --wait`

**Problem**: "Port 7687 already in use"

- Solution: `docker stop $(docker ps -q)` or use different port

**Problem**: "Connection refused" when accessing MCP

- Solution: Check `docker logs bioetl-neo4j` for startup errors

**Problem**: Neo4j takes too long to start

- Solution: Normal — Neo4j 5.15 takes 10-15 seconds. Be patient.

See [NEO4J-STARTUP-GUIDE.md](NEO4J-STARTUP-GUIDE.md) for more troubleshooting.

______________________________________________________________________

## 📝 Files in This Directory

| File                           | Purpose                            |
| ------------------------------ | ---------------------------------- |
| `NEO4J-MCP-SESSION-SUMMARY.md` | Session summary & next steps       |
| `NEO4J-STARTUP-GUIDE.md`       | Step-by-step startup instructions  |
| `NEO4J-COMPLETION-GUIDE.md`    | What's left to do                  |
| `neo4j-memory-setup.md`        | Memory configuration (existing)    |
| `README.md`                    | General deployment docs (existing) |
| **This file**                  | Documentation index                |

______________________________________________________________________

**Next Step**: Follow [NEO4J-STARTUP-GUIDE.md](NEO4J-STARTUP-GUIDE.md) to start Neo4j backend on your machine.
