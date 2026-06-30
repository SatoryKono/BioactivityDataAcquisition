# Codex WSL Quick Start

Your system is fully configured. **WSL2 + Ubuntu** with **Node.js, npm, and Codex CLI** are ready.

## ✅ Verification

- ✓ WSL2 running (Ubuntu distro)
- ✓ Node.js v20.10.0
- ✓ npm 10.2.3
- ✓ Codex CLI 0.118.0
- ✓ OpenAI API key configured in `.env.codex`
- ✓ Docker Desktop running

## 🚀 Launch Codex

### Interactive Mode (Windows PowerShell)

```powershell
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2
.\scripts\ai\codex\run-codex.ps1
```

Or from repo root:

```powershell
.\run-codex-wsl.ps1
```

### With a Prompt

```powershell
.\scripts\ai\codex\run-codex.ps1 exec "analyze the pipeline"
```

### From WSL/Bash

```bash
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/scripts/ai/codex
bash run-codex.sh
```

With a prompt:

```bash
bash run-codex.sh exec "fix the failing test"
```

## 📋 Available Commands

| Command | Mode | Description |
|---------|------|-------------|
| `(no args)` | Interactive | Start Codex with confirmations |
| `exec "prompt"` | Auto-exec | Run without waiting for user confirmation |
| `check` | Diagnostic | Verify environment setup |
| `setup` | Maintenance | Install missing components |
| `mcp-check` | Config | Check MCP server configuration |
| `mcp-setup` | Config | Synchronize MCP configs |
| `login` | Auth | Authenticate with API key |
| `device-login` | Auth | Authenticate with device code |

## 📚 Examples

### Start Codex (interactive)
```powershell
.\run-codex.ps1
```

### Analyze code (auto-exec)
```powershell
.\run-codex.ps1 exec "analyze the ChemBL parser"
```

### Check setup
```powershell
.\run-codex.ps1 check
```

### Sync MCP before launch
```powershell
.\run-codex.ps1 mcp-setup
```

## 🔧 Scripts Breakdown

All scripts delegate to the **canonical WSL launcher** at `scripts/ai/codex/run-codex.sh`:

- **`run-codex.ps1`** → PowerShell transport to bash launcher
- **`run-codex.sh`** ⭐ → Main WSL/Bash entry point (loads env, checks setup, syncs MCP, launches Codex)
- **`headless.ps1`** → Launch Codex without MCP sync
- **`helper/setup-wsl-complete.sh`** → Full WSL setup (Node.js, Codex CLI, Docker check)
- **`helper/ensure-codex-cli.sh`** → Install/verify Codex binary
- **`helper/ensure-mcp.sh`** → Sync MCP configuration
- **`helper/run-codex-impl.sh`** → Final Codex executor

## 🔐 API Key

Currently configured in `scripts/ai/codex/.env.codex` with your OpenAI key.

To update:
```powershell
notepad .\scripts\ai\codex\.env.codex
```

Get a new key: https://platform.openai.com/api-keys

**Note**: Setup scripts do not create `.env.codex` by default. Create it manually from `.env.codex.example`, or set `BIOETL_CREATE_LOCAL_ENV_FILES=1` when running setup to generate a local template automatically.

## 🐛 Troubleshooting

### "WSL is not recognized"
WSL is working — you have Ubuntu running. This shouldn't happen, but run:
```powershell
wsl --list --verbose
```

### "Node.js not found"
Run setup:
```powershell
.\run-codex.ps1 setup
```

### "Codex CLI not found"
Run setup to install:
```powershell
.\run-codex.ps1 setup
```

### Setup hangs/freezes
Run diagnostics:
```powershell
.\scripts\ai\codex\helper\diagnose-hang.ps1
```

Or check logs in WSL:
```bash
wsl -e bash -c "bash scripts/ai/codex/helper/setup-wsl-complete.sh 2>&1 | tail -50"
```

### "API key not found"
Edit `.env.codex` and add your key:
```powershell
$env:OPENAI_API_KEY = "sk-your-key"
.\run-codex.ps1
```

Or set in PowerShell before running:
```powershell
$env:OPENAI_API_KEY = "sk-..."
.\run-codex.ps1 exec "your prompt"
```

## 📂 WSL Path Mapping

Your repository inside WSL:
```
Windows: E:\g-drive\05_AI\github\BioactivityDataAcquisition2
WSL:     /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2
```

All scripts automatically convert paths between Windows and WSL.

## 🎯 Next Steps

1. **Test interactive launch** (confirmations):
   ```powershell
   .\run-codex.ps1
   ```

2. **Test with a prompt** (auto-exec):
   ```powershell
   .\run-codex.ps1 exec "list the MCP servers in this repo"
   ```

3. **Check environment**:
   ```powershell
   .\run-codex.ps1 check
   ```

4. **Sync MCP if needed**:
   ```powershell
   .\run-codex.ps1 mcp-setup
   ```

## 📖 Full Documentation

- Main README: `scripts/ai/codex/README.md`
- Setup guide: `scripts/ai/codex/WSL_SETUP_INSTRUCTIONS.md`
- Troubleshooting: `CODEX_SETUP.txt`

---

**Status**: ✅ Ready to use. Run `.\run-codex.ps1` to start.
