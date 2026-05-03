# Gemini WSL Interactive Setup - Complete

## ✅ Status Summary

Your Gemini CLI is fully configured and ready for interactive use:

| Component | Status | Details |
|-----------|--------|---------|
| **WSL** | ✅ Active | Running in Ubuntu on WSL |
| **Node.js** | ✅ Installed | v18.19.1 |
| **npm** | ✅ Installed | v9.2.0 |
| **Gemini CLI** | ✅ Installed | v0.39.1 (managed in `.cache/tools/gemini-cli/`) |
| **API Key** | ✅ Configured | Set in `.env.gemini` |
| **MCP Servers** | ✅ Ready | `filesystem`, `git`, `docker` (if running) |
| **Workspace Config** | ✅ Synced | `.gemini/settings.json` auto-created at startup |

## 🚀 Quick Start Commands

### Interactive Mode (Type multi-line prompts, follow AI guidance)

**Windows (PowerShell):**
```powershell
.\scripts\ai\gemini\gemini-interactive.ps1
```

**WSL/Bash:**
```bash
bash scripts/ai/gemini/gemini-interactive.sh
```

### Single Prompt Mode (Send one command and exit)

```powershell
.\scripts\ai\gemini\gemini-interactive.ps1 "analyze this codebase"
```

```bash
bash scripts/ai/gemini/gemini-interactive.sh "explain quantum computing"
```

### Auto-Execute Mode (No approval prompts—all actions auto-approved)

```bash
bash scripts/ai/gemini/run-gemini.sh exec "refactor all Python files"
```

## 📂 New Files Created

| File | Purpose |
|------|---------|
| `gemini-interactive.ps1` | PowerShell quick launcher (Windows) |
| `gemini-interactive.sh` | Bash quick launcher (WSL) |
| `GEMINI_INTERACTIVE_GUIDE.md` | Full setup & configuration guide |
| `QUICK_REFERENCE.md` | Cheat sheet with common commands |
| `setup-bash-alias.sh` | Optional: Add `gemini` command alias to bash |

## 🎯 Available Commands in Interactive Mode

Once Gemini CLI launches, you can use:

```
/help                    # Show Gemini CLI help
/exit or /quit or Ctrl+C # Exit interactive mode
/clear or /cls           # Clear screen

/mcp list               # Show MCP servers
/mcp enable <name>      # Enable MCP server
/mcp disable <name>     # Disable MCP server
/mcp status <name>      # Check server status

/model list             # List available models
/model set <name>       # Switch model

/model set gemini-2.5-pro  # More capable but slower/costlier
/model set gemini-2.5-flash  # Default: fast & cheap
```

## 💡 Example Workflows

### Code Review + Fix
```
User: analyze src/main.py for issues

Gemini: [reviews code, identifies bugs]

User: fix these issues
Gemini: [proposes fixes with file operations via MCP filesystem]

User: yes
Gemini: [writes updated files]
```

### Documentation Generation
```
User: write comprehensive README.md for this project

Gemini: [reads project files via MCP, generates docs]

User: add architecture diagram

Gemini: [appends diagram section]

User: save it

Gemini: [writes README.md to disk]
```

### Docker Troubleshooting
```
User: why is my Docker build failing?

Gemini: [asks clarifying questions]

User: [provides error output]

Gemini: [analyzes, suggests fixes]

User: apply the fixes

Gemini: [uses MCP filesystem + docker to modify and rebuild]
```

## 🔌 MCP Server Integration

Gemini can execute commands on your behalf through MCP servers:

- **filesystem** — Read, write, create, delete files
- **git** — Clone repos, commit changes, view history
- **docker** — Build images, run containers (requires Docker Desktop running)

### Check Available Servers

```bash
bash scripts/ai/gemini/run-gemini.sh mcp-check
```

### Resync MCP Servers (if you add new ones to `.mcp.json`)

```bash
bash scripts/ai/gemini/run-gemini.sh mcp-setup
```

## 📋 Setup Checklist

- [x] WSL environment verified
- [x] Node.js 18+ installed
- [x] npm installed
- [x] Gemini CLI v0.39.1 installed (managed in `.cache/tools/gemini-cli/`)
- [x] API key configured in `.env.gemini`
- [x] MCP servers configured and synced
- [x] Interactive launchers created (`gemini-interactive.ps1/sh`)
- [x] Documentation written

## 🔄 Workflow for Regular Use

1. **Every session:**
   ```powershell
   .\scripts\ai\gemini\gemini-interactive.ps1
   ```

2. **Type your request** (multi-line OK):
   ```
   analyze the repository and suggest Docker optimizations
   ```

3. **Gemini responds** with analysis and actionable suggestions

4. **Approve or iterate:**
   - Type "yes" to approve file changes
   - Type follow-ups for refinement
   - Type "/exit" to quit

5. **Changes persist** in your repository via MCP filesystem integration

## 🛠️ Maintenance Commands

```bash
# Check everything is OK
bash scripts/ai/gemini/run-gemini.sh check

# Update Gemini CLI to latest
bash scripts/ai/gemini/run-gemini.sh update

# Show all available commands
bash scripts/ai/gemini/run-gemini.sh help
```

## 📝 Configuration Files

| File | Purpose | Edit? |
|------|---------|-------|
| `.env.gemini` | API key & model choice | ✅ Yes (add your API key) |
| `.gemini/settings.json` | MCP configuration | ⚠️ Auto-generated, don't edit |
| `.cache/tools/gemini-cli/` | Managed runtime | ❌ Don't touch |

## 🚨 Troubleshooting

### "GEMINI_API_KEY not set"
→ Edit `scripts/ai/gemini/.env.gemini` and add your API key

### "WSL not found"
→ Run: `wsl --install` (Windows 11) or download from Microsoft Store

### "Node.js not found"
→ Run: `bash scripts/ai/gemini/run-gemini.sh setup`

### "Docker MCP server disconnected"
→ Start Docker Desktop

### "Permission denied"
→ Run: `chmod +x scripts/ai/gemini/*.sh scripts/ai/gemini/helper/*.sh`

## 📚 More Information

- **Full Guide:** `scripts/ai/gemini/GEMINI_INTERACTIVE_GUIDE.md`
- **Quick Reference:** `scripts/ai/gemini/QUICK_REFERENCE.md`
- **Original Documentation:** `scripts/ai/gemini/README.md`
- **API Keys:** https://aistudio.google.com/app/apikeys
- **Gemini CLI Docs:** https://github.com/google/genai-cli

## 🎉 You're Ready!

Launch interactive Gemini now:

**Windows:**
```powershell
.\scripts\ai\gemini\gemini-interactive.ps1
```

**WSL:**
```bash
bash scripts/ai/gemini/gemini-interactive.sh
```

Start by asking: `"analyze this repository and suggest improvements"`
