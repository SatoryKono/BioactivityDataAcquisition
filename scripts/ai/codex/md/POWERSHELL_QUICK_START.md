# Codex CLI for WSL — PowerShell Quick Start

## For Windows PowerShell Users

You have all the tools you need. Here's how to use them:

### Step 1: Verify Setup (Recommended from PowerShell)

```powershell
.\scripts\ops\verify-setup.ps1
```

This runs better in PowerShell than cmd.exe because it has proper color output.

### Step 2: Initial Setup

```powershell
.\scripts\ai\codex\setup-codex-wsl.bat
```

This installs:

- Node.js & npm (if needed)
- Codex CLI
- WSL proxy configuration

### Step 3: Test It Works

```powershell
.\scripts\ops\codex.bat "what's in the src directory?"
```

______________________________________________________________________

## All PowerShell Commands

### Interactive Mode (review changes before applying)

```powershell
# Start interactive
.\scripts\ops\codex.bat

# With a prompt
.\scripts\ops\codex.bat "analyze the pipeline"

# Show help
.\scripts\ops\codex.bat --help
```

### Auto-Execution Mode (no confirmations)

```powershell
# Just do it
.\scripts\ops\codex-exec.bat "refactor the parser"

# Update and run
.\scripts\ops\codex-exec.bat --update "your prompt"
```

### Diagnostics

```powershell
# Quick check (PowerShell - recommended)
.\scripts\ops\verify-setup.ps1

# Detailed diagnostics
.\scripts\ai\codex\diagnose_wsl.ps1

# Using batch (basic)
.\scripts\ops\verify-setup.bat
```

### Setup & Configuration

```powershell
# Complete setup
.\scripts\ai\codex\setup-codex-wsl.bat

# Start proxy if needed
.\scripts\ops\start-wsl-proxy.bat
```

______________________________________________________________________

## Common Workflows

### Analyze Code

```powershell
.\scripts\ops\codex.bat "analyze the ChemBL parser for issues"
```

### Refactor Code (Auto)

```powershell
.\scripts\ops\codex-exec.bat "refactor for performance"
```

### Add Tests

```powershell
.\scripts\ops\codex.bat "write unit tests for the parser"
```

### Generate Documentation

```powershell
.\scripts\ops\codex.bat "generate docstrings for the BioETL module"
```

______________________________________________________________________

## Troubleshooting in PowerShell

### Issue: "command not found"

```powershell
# Make sure you're in the repo root
pwd
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2
```

### Issue: WSL not working

```powershell
# Check if WSL is installed
wsl --list --verbose

# If Ubuntu is not listed, install it
wsl --install -d Ubuntu
```

### Issue: Node.js errors in WSL

```powershell
# Run setup again
.\scripts\ai\codex\setup-codex-wsl.bat
```

### Issue: Docker Desktop not responding

```powershell
# Verify Docker is running
docker ps

# If it fails, start Docker Desktop app
# Wait for green icon in taskbar, then retry
```

### Issue: Network/proxy errors

```powershell
# Start proxy server
.\scripts\ops\start-wsl-proxy.bat

# Then try your command again
.\scripts\ops\codex.bat "your prompt"
```

______________________________________________________________________

## Documentation to Read

From PowerShell:

```powershell
# Main Codex guide
notepad .\scripts\ai\codex\README.md

# WSL setup guide
notepad .\docs\05-operations\tooling\scripts-ops\CODEX_WSL_SETUP.md

# Quick reference
notepad .\docs\05-operations\tooling\scripts-ops\CODEX_QUICK_REF.md

# Tooling index
notepad .\docs\05-operations\tooling\scripts-ops\INDEX.md

# Start here guide
notepad .\docs\05-operations\tooling\scripts-ops\00_START_HERE.md
```

______________________________________________________________________

## Tips for PowerShell

1. **Use `verify-setup.ps1` not the batch version** — better output and colors

1. **Tab completion works** — type `.\scripts\ops\co` and press Tab

1. **Use quotes for prompts with spaces**:

   ```powershell
   .\scripts\ops\codex.bat "your prompt here"
   ```

1. **View exit code** to see if command succeeded:

   ```powershell
   .\scripts\ops\codex.bat "something"
   echo "Exit code: $LASTEXITCODE"
   ```

1. **Run multiple commands**:

   ```powershell
   .\scripts\ops\codex.bat "task 1"; .\scripts\ops\codex.bat "task 2"
   ```

______________________________________________________________________

## If You Prefer WSL Bash

You can also open the WSL terminal directly and use:

```bash
./scripts/ops/codex.sh "your prompt"
./scripts/ops/codex-exec.sh "your prompt"
bash ./scripts/ai/codex/helper/setup-wsl-complete.sh
bash ./scripts/ai/codex/diagnose_wsl.sh
```

But PowerShell is easier for Windows users because path handling is simpler.

______________________________________________________________________

## Ready to Start?

1. Open PowerShell
1. `.\scripts\ops\verify-setup.ps1`
1. `.\scripts\ai\codex\setup-codex-wsl.bat`
1. `.\scripts\ops\codex.bat "hello"`

That's it! Enjoy using Codex! 🚀
