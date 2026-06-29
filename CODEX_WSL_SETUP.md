# Codex WSL Setup — Complete Configuration

## ✅ Your Current Setup

All components are installed and configured:

- **WSL2** ✓ Running (Ubuntu distro)
- **Node.js** ✓ v20.10.0
- **npm** ✓ 10.2.3
- **Codex CLI** ✓ 0.118.0 installed and working
- **Docker Desktop** ✓ Running
- **OpenAI API Key** ✓ Configured in `.env.codex`

## 🚀 Quick Start — 3 Ways to Run Codex

### Option 1: From Repo Root (Fastest)

```powershell
# Interactive mode
.\codex.ps1

# With a prompt (auto-exec)
.\codex.ps1 exec "analyze the ChemBL data parser"
```

### Option 2: Canonical Launcher

```powershell
cd scripts\ai\codex
.\run-codex.ps1

# With a prompt
.\run-codex.ps1 exec "refactor the ETL pipeline"
```

### Option 3: From WSL/Bash

```bash
wsl -d Ubuntu
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex

bash run-codex.sh
bash run-codex.sh exec "list Docker images"
```

## 📋 All Available Commands

```powershell
# Interactive launch (Codex will ask before executing changes)
.\codex.ps1

# Auto-exec (skip confirmations)
.\codex.ps1 exec "your prompt here"

# Check environment (verifies all dependencies)
.\codex.ps1 check

# Run setup (install missing components)
.\codex.ps1 setup

# Configure MCP servers
.\codex.ps1 mcp-setup
.\codex.ps1 mcp-check

# Authentication
.\codex.ps1 login              # API key auth
.\codex.ps1 device-login       # Device code auth
```

## 📂 Scripts Architecture

The Codex setup uses a **canonical WSL/Bash launcher** that all Windows scripts delegate to:

```
scripts/ai/codex/
├── run-codex.ps1              ← PowerShell transport (delegates to run-codex.sh)
├── run-codex.sh               ⭐ CANONICAL — Main WSL/Bash entry point
├── .env.codex                 ← Your OpenAI API key (in .gitignore)
├── .env.codex.example         ← Template
│
└── helper/
    ├── run-codex-impl.sh      ← Actual Codex CLI executor
    ├── ensure-codex-cli.sh    ← Install/verify Codex binary
    ├── ensure-mcp.sh          ← Sync MCP configuration
    ├── setup-wsl-complete.sh  ← Full WSL setup
    └── ...
```

### What `run-codex.sh` Does

1. **Check** — Verify WSL, Node.js, npm, Codex CLI
2. **Setup** (if needed) — Install missing components
3. **MCP Sync** — Keep `~/.codex/config.toml` in sync with repo MCP servers
4. **Launch** — Run Codex CLI with the repo root as working directory

## 🔐 OpenAI API Key

Currently configured in: `scripts/ai/codex/.env.codex` (in .gitignore)

To view or update:
```powershell
notepad .\scripts\ai\codex\.env.codex
```

To get a new key:
1. Go to https://platform.openai.com/api-keys
2. Create a new secret key
3. Copy (starts with `sk-`)
4. Paste into `.env.codex`

## 🌐 WSL Path Mapping

Your repo is accessible from both Windows and WSL:

| OS | Path |
|----|------|
| Windows | `E:\g-drive\05_AI\github\BioactivityDataAcquisition2` |
| WSL | `/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2` |

All launchers automatically convert paths between Windows and WSL.

## 🔧 How to Use Codex with Your Project

### Example 1: Analyze Code

```powershell
.\codex.ps1 exec "analyze the ChemBL data acquisition pipeline and suggest optimizations"
```

### Example 2: Fix a Bug

```powershell
.\codex.ps1 exec "there's a timeout in the data validation step, debug and fix it"
```

### Example 3: Refactor

```powershell
.\codex.ps1 exec "refactor the ETL pipeline to use async/await"
```

### Example 4: Review Tests

```powershell
.\codex.ps1 exec "review the test suite coverage and add missing tests for edge cases"
```

## ⚙️ Advanced Usage

### Skip MCP Synchronization

If you want to launch Codex without syncing MCP config:

```powershell
$env:CODEX_SKIP_MCP_SETUP = 1
.\codex.ps1 exec "your prompt"
```

### Use a Specific WSL Distro

By default, uses your default WSL distro (Ubuntu). To use a different one:

```powershell
$env:BIOETL_WSL_DISTRO = "Ubuntu"
.\codex.ps1 exec "your prompt"
```

### Validate MCP Configuration

Check if all MCP servers are properly configured:

```powershell
.\codex.ps1 mcp-check
```

If needed, resynchronize:

```powershell
.\codex.ps1 mcp-setup
```

## 🐛 Troubleshooting

### "Command 'codex' not found"

Install Codex CLI:
```powershell
.\codex.ps1 setup
```

### Setup hangs/freezes

Run diagnostics:
```powershell
.\scripts\ai\codex\helper\diagnose-hang.ps1
```

Common causes:
- `apt-get update` hanging in WSL → skipped now
- Slow npm install → retries 3 times
- Docker daemon not running → ensure Docker Desktop is running

### API key errors

Verify the key is set:
```powershell
$env:OPENAI_API_KEY = "sk-..."
.\codex.ps1 check
```

Or edit the file:
```powershell
notepad .\scripts\ai\codex\.env.codex
```

### Docker connectivity issues

Ensure Docker Desktop is running on Windows, then verify from WSL:
```bash
wsl -e docker ps
```

## 📚 Documentation Files

- **Quick Start** (this directory): `scripts\ai\codex\QUICKSTART_WSL.md`
- **Main README**: `scripts\ai\codex\README.md`
- **Setup Instructions** (Russian): `scripts\ai\codex\WSL_SETUP_INSTRUCTIONS.md`
- **Setup Guide**: `CODEX_SETUP.txt` (repo root)
- **Troubleshooting**: `scripts\ai\codex\md\SETUP_HANG_FIX.md`

## 🎯 Next Steps

1. **Test interactive mode** (you'll see Codex's interface):
   ```powershell
   .\codex.ps1
   ```

2. **Test with a prompt** (auto-exec):
   ```powershell
   .\codex.ps1 exec "list all Docker containers"
   ```

3. **Check environment**:
   ```powershell
   .\codex.ps1 check
   ```

4. **Explore MCP servers**:
   ```powershell
   .\codex.ps1 mcp-check
   ```

## 🔗 External Resources

- Codex Documentation: https://docs.docker.com/ai/sandboxes/agents/codex/
- Docker Sandboxes: https://docs.docker.com/ai/sandboxes/
- OpenAI API Keys: https://platform.openai.com/api-keys
- WSL Documentation: https://learn.microsoft.com/en-us/windows/wsl/

---

**Status**: ✅ **Ready to use**

Run `.\codex.ps1` from repo root to start Codex, or see examples above.
