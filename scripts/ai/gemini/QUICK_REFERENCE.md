# Gemini CLI - Quick Reference Card

## 🚀 Launch Interactive Mode

**From Windows (PowerShell):**
```powershell
# Optional when the default WSL distro is not the target distro:
# $env:BIOETL_WSL_DISTRO="Ubuntu-22.04"
.\scripts\ai\gemini\run-gemini.ps1
```

**From WSL/Bash:**
```bash
bash scripts/ai/gemini/run-gemini.sh
```


## 📝 Send a Single Prompt (No Interactive Loop)

**PowerShell:**
```powershell
.\scripts\ai\gemini\run-gemini.ps1 "analyze the repository structure"
```

**Bash:**
```bash
bash scripts/ai/gemini/run-gemini.sh "explain how Docker works"
```

## ⚡ Auto-Execute Mode (YOLO - Auto-Approve All Actions)

**PowerShell:**
```powershell
.\scripts\ai\gemini\run-gemini.ps1 exec "refactor all Python files"
```

**Bash:**
```bash
bash scripts/ai/gemini/run-gemini.sh exec "refactor all Python files"
```
⚠️ **Warning:** All file modifications and tool uses are auto-approved without prompting.

## 🔧 Administration Commands

**PowerShell:**
```powershell
# First-time setup through WSL
.\scripts\ai\gemini\setup.ps1

# Check environment (Node, npm, Gemini CLI, API key, MCP)
.\scripts\ai\gemini\run-gemini.ps1 check

# Install or repair managed Gemini CLI runtime
.\scripts\ai\gemini\run-gemini.ps1 setup

# Update Gemini CLI to latest version
.\scripts\ai\gemini\run-gemini.ps1 update

# Verify MCP server configuration
.\scripts\ai\gemini\run-gemini.ps1 mcp-check

# Sync MCP configuration
.\scripts\ai\gemini\run-gemini.ps1 mcp-setup
```

**Bash:**
```bash
# Check environment (Node, npm, Gemini CLI, API key, MCP)
bash scripts/ai/gemini/run-gemini.sh check

# First-time setup (installs Node 22 + Gemini CLI)
bash scripts/ai/gemini/run-gemini.sh setup

# Update Gemini CLI to latest version
bash scripts/ai/gemini/run-gemini.sh update

# Verify MCP server configuration
bash scripts/ai/gemini/run-gemini.sh mcp-check

# Sync MCP configuration (run this if you add new MCP servers)
bash scripts/ai/gemini/run-gemini.sh mcp-setup

# Show help
bash scripts/ai/gemini/run-gemini.sh help

# Launch without MCP sync for one run
bash scripts/ai/gemini/headless.sh
```

## 🔑 API Key Configuration

1. Get key: https://aistudio.google.com/app/apikeys
2. Edit: `scripts/ai/gemini/.env.gemini`
3. Set: `GEMINI_API_KEY="your-key-here"`

## 🎯 Available Models

- `gemini-2.5-flash` (default, fast, cheaper)
- `gemini-2.5-pro` (accurate, comprehensive)
- `gemini-2.0-flash` (alternative)

Override:
```bash
# Bash
GEMINI_MODEL=gemini-2.5-pro bash scripts/ai/gemini/run-gemini.sh

# PowerShell
$env:GEMINI_MODEL="gemini-2.5-pro"
.\scripts\ai\gemini\run-gemini.ps1
```

## 🧠 MCP Servers

Gemini CLI can execute file system operations and run tools via MCP servers:
- `filesystem` — Read/write files
- `git` — Git operations
- `docker` — Docker commands (if Docker is running)

Commands in interactive mode:
```
/mcp list      # Show available MCP servers
/mcp enable fs # Enable specific server
/mcp disable fs
```

## 📍 File Locations

```
.cache/tools/gemini-cli/
├── npm-global/bin/gemini     # ← Main executable
├── npm-global/lib/           # ← Gemini CLI code
├── npm-cache/                # ← npm package cache
└── home/                      # ← Settings & cache

.env.gemini                    # ← Your API key (git-ignored)
.gemini/settings.json          # ← Local-only workspace MCP config, created/synced at startup
```

## 🔍 Examples

**Code Review:**
```
bash scripts/ai/gemini/run-gemini.sh "review src/main.py for bugs"
```

**Generate Documentation:**
```
bash scripts/ai/gemini/run-gemini.sh "write README.md for this project"
```

**Architecture Analysis:**
```
.\scripts\ai\gemini\run-gemini.ps1 "analyze the system architecture and suggest improvements"
```

**Docker Troubleshooting:**
```
bash scripts/ai/gemini/run-gemini.sh "why is my Docker build failing?"
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "GEMINI_API_KEY not set" | Edit `.env.gemini` with your API key from https://aistudio.google.com/app/apikeys |
| "WSL not found" | Install WSL: `wsl --install` on Windows 11 |
| Wrong WSL distro | Set `BIOETL_WSL_DISTRO=<name>` before running the PowerShell launcher; unset it to use the default distro |
| "Node.js not found" | Run: `bash scripts/ai/gemini/run-gemini.sh setup` |
| "MCP servers disconnected" | Start Docker Desktop if using Docker MCP server |
| "Permission denied on scripts" | Fix: `chmod +x scripts/ai/gemini/*.sh scripts/ai/gemini/helper/*.sh` |
| "Connection timeout" | Check: Network proxy settings (see `.wsl_proxy_env.sh` if behind corporate proxy) |

## 📚 Full Documentation

See `GEMINI_INTERACTIVE_GUIDE.md` for detailed setup and advanced usage.
