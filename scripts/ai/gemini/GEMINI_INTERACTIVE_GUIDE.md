# Gemini Interactive Setup & Usage Guide

## Quick Start

### From PowerShell (Windows):
```powershell
# First time setup (one-time)
.\scripts\ai\gemini\run-gemini.ps1 check
.\scripts\ai\gemini\run-gemini.ps1 setup

# Interactive mode
.\scripts\ai\gemini\gemini-interactive.ps1

# With a prompt
.\scripts\ai\gemini\gemini-interactive.ps1 "analyze this code"
```

### From WSL/Bash:
```bash
# First time setup (one-time)
bash scripts/ai/gemini/run-gemini.sh check
bash scripts/ai/gemini/run-gemini.sh setup

# Interactive mode
bash scripts/ai/gemini/gemini-interactive.sh

# With a prompt
bash scripts/ai/gemini/gemini-interactive.sh "explain this repository"
```

## Configuration

### API Key Setup
1. Get your API key from: https://aistudio.google.com/app/apikeys
2. Edit `scripts/ai/gemini/.env.gemini`:
   ```bash
   GEMINI_API_KEY="your-api-key-here"
   # Optional: override model
   # GEMINI_MODEL=gemini-2.5-flash
   ```

### Supported Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `start` | `run-gemini.sh start` | Interactive CLI (default) |
| `prompt` | `run-gemini.sh prompt "task"` | Headless prompt execution |
| `exec` | `run-gemini.sh exec "task"` | Auto-approve all actions (YOLO mode) |
| `check` | `run-gemini.sh check` | Verify environment setup |
| `setup` | `run-gemini.sh setup` | Install/configure Gemini CLI |
| `mcp-check` | `run-gemini.sh mcp-check` | Verify MCP servers |
| `mcp-setup` | `run-gemini.sh mcp-setup` | Sync MCP configuration |
| `update` | `run-gemini.sh update` | Update Gemini CLI to latest |

## Runtime Environment

The managed Gemini CLI is installed in `.cache/tools/gemini-cli/`:
- `npm-global/` — Node.js 22 + Gemini CLI
- `npm-cache/` — npm package cache
- `home/` — Gemini CLI home directory (settings, cache, MCP state)

## MCP Integration

Gemini CLI automatically loads MCP servers from `.gemini/settings.json` in the repository root. Configuration is synchronized on startup.

### Environment Variables

- `GEMINI_SKIP_MCP_SETUP=1` — Skip MCP sync
- `GEMINI_RESPECT_MCP_DISABLES=1` — Keep existing `/mcp disable` choices
- `GEMINI_VALIDATE_MCP_LIST=1` — Validate MCP list on startup
- `GEMINI_REQUIRE_MCP_LIST=1` — Fail if MCP validation fails
- `GEMINI_MCP_CHECK_TIMEOUT=15` — MCP validation timeout (seconds)

## Troubleshooting

### "GEMINI_API_KEY not set"
→ Edit `scripts/ai/gemini/.env.gemini` and add your API key

### "WSL not available"
→ Install WSL: https://learn.microsoft.com/en-us/windows/wsl/install

### "Node.js not found"
→ Run `bash scripts/ai/gemini/run-gemini.sh setup` to install managed Node 22

### "Docker-backed MCP servers disconnected"
→ Ensure Docker Desktop is running

### "Permission denied"
→ Make scripts executable:
```bash
chmod +x scripts/ai/gemini/*.sh
chmod +x scripts/ai/gemini/helper/*.sh
chmod +x scripts/ai/gemini/*.ps1
```

## Advanced Usage

### Headless Auto-Execute
```bash
bash scripts/ai/gemini/run-gemini.sh exec "fix all formatting issues"
```
⚠️ Use only for trusted tasks — all actions are auto-approved.

### Custom Model
```bash
GEMINI_MODEL=gemini-2.0-flash .\scripts\ai\gemini\gemini-interactive.ps1
```

### Debug Mode
```bash
set -x
bash scripts/ai/gemini/run-gemini.sh check
```

## Architecture

```
scripts/ai/gemini/
├── run-gemini.ps1                  # PowerShell delegator
├── run-gemini.sh                   # Main WSL entrypoint
├── gemini-interactive.ps1          # Quick PowerShell launcher
├── gemini-interactive.sh           # Quick WSL launcher
├── .env.gemini                     # API key config (git-ignored)
├── helper/
│   ├── run-gemini-impl.sh          # Runtime launcher
│   ├── check-env.sh                # Verify setup
│   ├── setup-env.sh                # Initial setup
│   ├── ensure-gemini-cli.sh        # Managed CLI bootstrap
│   └── ensure-mcp.sh               # MCP configuration sync
└── README.md                       # Documentation

.cache/tools/gemini-cli/            # Managed runtime
├── npm-global/                     # Node 22 + @google/gemini-cli
├── npm-cache/                      # npm cache
└── home/                           # GEMINI_CLI_HOME

.gemini/settings.json               # Workspace MCP config (synced at startup)
```
