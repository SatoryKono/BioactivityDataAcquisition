# Codex CLI Setup — READY NOW

## Status: ✅ Complete and Tested

Your Codex CLI setup is ready to use. Here's how to get started immediately.

---

## Quick Start (Choose Your Path)

### Option 1: Automatic Setup (Recommended)

**From PowerShell:**

```powershell
# Navigate to your repo
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2

# Run quick setup (2-5 minutes)
.\scripts\ops\quick-setup.ps1
```

This will:
- ✅ Install Node.js & npm (if needed)
- ✅ Install Codex CLI
- ✅ Configure everything

Then test it:
```powershell
.\scripts\ops\codex.bat "analyze the pipeline"
```

---

### Option 2: Manual Setup (Fastest for existing Node.js)

**Open WSL terminal and run:**

```bash
# 1. Check if Node.js exists
node --version
npm --version

# 2. Install Codex
mkdir -p ~/.cache/tools/codex-cli/npm-global
export NPM_CONFIG_PREFIX=~/.cache/tools/codex-cli/npm-global
npm install -g @openai/codex@latest

# 3. Test
~/.cache/tools/codex-cli/npm-global/bin/codex --version

# 4. Use it from PowerShell
exit  # Leave WSL
```

Then from PowerShell:
```powershell
.\scripts\ops\codex.bat "analyze the pipeline"
```

---

## What You Have

### Launch Scripts (Ready to use)
- `codex.bat` / `codex.sh` — Interactive mode
- `codex-exec.bat` / `codex-exec.sh` — Auto-execute mode

### Setup Scripts (Run once)
- `quick-setup.ps1` ⭐ Fast setup (recommended)
- `setup-codex-wsl.bat` — Alternative setup launcher
- `setup-wsl-codex-complete.sh` — Full setup script

### Verification Scripts
- `verify-setup.ps1` — Check if everything works

### Documentation
- `QUICK_SETUP.md` — Setup options
- `POWERSHELL_QUICK_START.md` — PowerShell commands
- `CODEX_QUICK_REF.txt` — One-page reference
- `CODEX_WSL_SETUP.md` — Complete guide

---

## Using Codex

### Interactive Mode (Review before applying)

```powershell
# Start interactive
.\scripts\ops\codex.bat

# With a prompt
.\scripts\ops\codex.bat "analyze the ChemBL parser"

# Show help
.\scripts\ops\codex.bat --help
```

### Auto-Execute Mode (Just do it)

```powershell
# Auto-execute without confirmations
.\scripts\ops\codex-exec.bat "refactor the parser"

# Update Codex first
.\scripts\ops\codex-exec.bat --update "your prompt"
```

### From WSL

```bash
./scripts/ops/codex.sh "your prompt"
./scripts/ops/codex-exec.sh "your prompt"
```

---

## Common Prompts

```powershell
# Analyze
.\scripts\ops\codex.bat "analyze the pipeline structure"

# Refactor
.\scripts\ops\codex-exec.bat "refactor for performance"

# Add tests
.\scripts\ops\codex.bat "write unit tests"

# Documentation
.\scripts\ops\codex.bat "generate docstrings"
```

---

## Troubleshooting

### Issue: Setup takes too long / times out

**Solution:** Use manual setup instead

```bash
# Open WSL and run:
node --version
npm --version

# If Node.js not found:
sudo apt-get install -y nodejs npm

# Install Codex manually:
mkdir -p ~/.cache/tools/codex-cli/npm-global
export NPM_CONFIG_PREFIX=~/.cache/tools/codex-cli/npm-global
npm install -g @openai/codex@latest
```

### Issue: "command not recognized"

**Solution:** Make sure you're in the repo directory

```powershell
pwd  # Should show: E:\g-drive\05_AI\github\BioactivityDataAcquisition2
.\scripts\ops\codex.bat "hello"
```

### Issue: "Node.js not found"

**Solution:** Install it

```bash
# From WSL
sudo apt-get update
sudo apt-get install -y nodejs npm
```

### Issue: Network/proxy errors

**Solution:** Start proxy server

```powershell
.\scripts\ops\start-wsl-proxy.bat
```

### Issue: "Codex not found" after setup

**Solution:** Reinstall Codex

```bash
# From WSL
export NPM_CONFIG_PREFIX=~/.cache/tools/codex-cli/npm-global
npm install -g @openai/codex@latest --force
```

---

## Next Actions

### Right Now (5 minutes)

1. Open PowerShell
2. `cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2`
3. `.\scripts\ops\quick-setup.ps1`
4. Wait 2-5 minutes for setup
5. `.\scripts\ops\codex.bat "hello"`

### Then (Optional)

- Read `POWERSHELL_QUICK_START.md` for more commands
- Bookmark `CODEX_QUICK_REF.txt` for quick reference
- Practice a few prompts

---

## Files Location

Everything is in: `./scripts/ops/`

Key files:
- `quick-setup.ps1` — Main setup (use this first)
- `codex.bat` — Launch Codex
- `POWERSHELL_QUICK_START.md` — Documentation
- `QUICK_SETUP.md` — Setup options

---

## Documentation Quick Links

| Document | For | Purpose |
|----------|-----|---------|
| This file | Everyone | Quick start |
| `QUICK_SETUP.md` | Setup help | Installation options |
| `POWERSHELL_QUICK_START.md` | PowerShell users | All commands |
| `CODEX_QUICK_REF.txt` | Everyone | Quick reference |
| `CODEX_WSL_SETUP.md` | Detailed help | Complete guide |

---

## Features

✅ Works from Windows PowerShell and WSL  
✅ Auto-installs everything  
✅ Fast setup (2-5 minutes)  
✅ Simple commands  
✅ Interactive and auto-exec modes  
✅ Error recovery  
✅ Comprehensive help  

---

## You're Ready!

The simplest path:

```powershell
.\scripts\ops\quick-setup.ps1
```

Then:

```powershell
.\scripts\ops\codex.bat "what's in the src directory?"
```

That's it! Enjoy Codex! 🚀
