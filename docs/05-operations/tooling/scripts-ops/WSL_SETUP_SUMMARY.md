# Codex WSL Setup — Complete Summary

## What Was Analyzed

Your project has existing Codex scripts for Windows:

- `scripts/ops/launchers/codex/codex.bat` - WSL2-based interactive launcher
- `scripts/ops/launchers/codex/codex-exec.bat` - WSL2-based auto-execution launcher
- `scripts/ops/launchers/codex/start-codex.bat` - Quick start wrapper
- `scripts/ops/runtime/wsl/wsl_proxy.py` - HTTP proxy bridge for VPN access
- `scripts/ai/mcp/support/load_repo_env.ps1` - PowerShell environment loader
- `.wsl_proxy_env.sh` - WSL proxy environment setup
- Documentation: `CODEX_SETUP.md`, `CODEX_QUICK_REF.md`

## What Was Created

### New Shell Scripts (for WSL direct use)

1. **`scripts/ops/launchers/codex/codex.sh`**

   - WSL bash launcher for interactive & prompt-based Codex usage
   - Auto-detects repository path
   - Verifies Node.js and Codex CLI availability
   - No path conversion needed (runs natively in WSL)

1. **`scripts/ops/launchers/codex/codex-exec.sh`**

   - WSL auto-execution launcher (full-auto mode)
   - Runs without user confirmations
   - Requires a prompt argument
   - Direct WSL context for performance

1. **`scripts/ai/codex/helper/setup-wsl.sh`**

   - Comprehensive WSL setup script
   - Installs Node.js, npm, and Codex CLI
   - Configures WSL proxy for VPN access
   - Verifies all dependencies and connectivity
   - Provides helpful diagnostic output

### New Windows Wrapper

4. **`scripts/ops/launchers/codex/codex-wsl.bat`**
   - Modern PowerShell batch wrapper
   - Bridges Windows → WSL Debian
   - Cleaner alternative to existing `codex.bat`
   - Calls the bash scripts directly

### Documentation

5. **`docs/05-operations/tooling/scripts-ops/CODEX_WSL_SETUP.md`** (detailed guide)

   - Complete setup instructions
   - Prerequisites and verification steps
   - Proxy configuration for VPN access
   - Common usage examples
   - Comprehensive troubleshooting guide
   - Advanced configuration options
   - Best practices

1. **`docs/05-operations/tooling/scripts-ops/CODEX_WSL_QUICK_REF.md`** (quick reference)

   - One-page quick start
   - Command cheat sheet
   - Common prompts and tasks
   - Troubleshooting checklist
   - Keyboard shortcuts

## Quick Start Guide

### Step 1: Install Dependencies (One-Time)

From PowerShell in project root:

```powershell
wsl -d Debian -- bash ./scripts/ai/codex/helper/setup-wsl.sh
```

Or from WSL directly:

```bash
bash ./scripts/ai/codex/helper/setup-wsl.sh
```

### Step 2: Verify Installation

```bash
# In WSL
codex --version
curl -I https://api.openai.com  # Should return 200 OK
```

### Step 3: Start Using Codex

From PowerShell:

```powershell
# Interactive
.\scripts\ops\codex-wsl.bat

# With prompt
.\scripts\ops\codex-wsl.bat "analyze the ChemBL parser"

# Or existing launchers still work
.\scripts\ops\codex.bat
.\scripts\ops\codex-exec.bat "refactor the transformer"
```

From WSL:

```bash
# Interactive
./scripts/ops/launchers/codex/codex.sh

# With prompt
./scripts/ops/launchers/codex/codex.sh "explain the data pipeline"

# Auto-execute
./scripts/ops/launchers/codex/codex-exec.sh "add type hints everywhere"
```

## Architecture

```
Windows (PowerShell)
    ↓
.bat files (codex.bat, codex-wsl.bat, codex-exec.bat)
    ↓
WSL2 Debian (wsl -d Debian -- bash)
    ↓
Bash scripts (.sh files)
    ↓
npm/Node.js
    ↓
Codex CLI
    ↓
OpenAI API (via proxy if behind VPN)
```

## Key Features

✅ **Native WSL Support**

- Run Codex directly in WSL bash
- No path conversion needed
- Better performance than WSL2 interop

✅ **VPN/Proxy Support**

- Auto-configurable Windows proxy bridge
- Works behind corporate firewalls
- Proxy detection in setup script

✅ **Flexible Execution**

- Interactive mode (TUI)
- Prompt mode (one-shot analysis)
- Auto-execution mode (full-auto)
- Multiple model support (GPT-4, o3, etc.)

✅ **Comprehensive Setup**

- Single command setup: `scripts/ai/codex/helper/setup-wsl.sh`
- Dependency verification
- Connectivity testing
- Clear diagnostic output

✅ **Well Documented**

- Detailed setup guide (`CODEX_WSL_SETUP.md`)
- Quick reference card (`CODEX_WSL_QUICK_REF.md`)
- Troubleshooting sections
- Example commands and best practices

## Files Reference

| File                               | Purpose                            | Platform         |
| ---------------------------------- | ---------------------------------- | ---------------- |
| `codex.sh`                         | **NEW** WSL launcher (interactive) | WSL bash         |
| `codex-exec.sh`                    | **NEW** WSL auto-exec launcher     | WSL bash         |
| `scripts/ai/codex/helper/setup-wsl.sh` | **NEW** Installation & setup       | WSL bash         |
| `codex-wsl.bat`                    | **NEW** Windows wrapper for WSL    | PowerShell       |
| `codex.bat`                        | Original Windows launcher          | PowerShell       |
| `codex-exec.bat`                   | Original Windows auto-exec         | PowerShell       |
| `start-codex.bat`                  | Existing quick launcher            | PowerShell       |
| `wsl_proxy.py`                     | HTTP proxy bridge                  | Python (Windows) |
| `start-wsl-proxy.bat`              | Existing proxy launcher            | PowerShell       |
| `.wsl_proxy_env.sh`                | Proxy environment vars             | WSL bash         |
| `CODEX_WSL_SETUP.md`               | **NEW** Detailed guide             | Markdown         |
| `CODEX_WSL_QUICK_REF.md`           | **NEW** Quick reference            | Markdown         |
| `CODEX_SETUP.md`                   | Existing setup guide               | Markdown         |
| `CODEX_QUICK_REF.md`               | Existing quick ref                 | Markdown         |

## Common Usage Scenarios

### Scenario 1: Quick Analysis from PowerShell

```powershell
.\scripts\ops\codex-wsl.bat "identify performance issues in the ETL pipeline"
```

### Scenario 2: Deep Interactive Session from WSL

```bash
./scripts/ops/launchers/codex/codex.sh
# Then type prompts interactively in the TUI
```

### Scenario 3: Auto-Apply Refactoring

```bash
./scripts/ops/launchers/codex/codex-exec.sh "add comprehensive error handling to all data loaders"
```

### Scenario 4: Code Generation

```bash
./scripts/ops/launchers/codex/codex.sh "generate Pydantic models for the bronze layer schema"
```

### Scenario 5: Read-Only Code Review

```bash
./scripts/ops/launchers/codex/codex.sh -s read-only "review security of credential handling"
```

## Troubleshooting Quick Links

- **Codex not found**: Run `scripts/ai/codex/helper/setup-wsl.sh`
- **API unreachable**: Run `wsl -d Debian -- source .wsl_proxy_env.sh`
- **WSL not installed**: `wsl --install -d Debian` (requires Windows Admin)
- **Permission issues**: Add `-d Debian --` after `wsl` in batch files
- **Path issues**: Scripts auto-convert paths; ensure running from project root

See `CODEX_WSL_SETUP.md` for comprehensive troubleshooting.

## Next Steps

1. ✅ Run setup: `bash ./scripts/ai/codex/helper/setup-wsl.sh`
1. ✅ Test: `./scripts/ops/launchers/codex/codex.sh --version`
1. ✅ Try: `./scripts/ops/launchers/codex/codex.sh "explain the pipeline"`
1. ✅ Explore: Review `CODEX_WSL_QUICK_REF.md` for examples
1. ✅ Integrate: Add Codex to your development workflow

## Notes

- All existing `.bat` files continue to work unchanged
- Bash scripts are executable from WSL directly
- Setup script is idempotent (safe to run multiple times)
- Proxy auto-detection works for most Windows configurations
- Codex preserves terminal history for analysis reference
- Sessions can be resumed with `codex resume --last`

______________________________________________________________________

**Questions or issues?** See `CODEX_WSL_SETUP.md` for detailed help.
