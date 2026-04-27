# ✅ Codex WSL Setup — Complete & Verified

## Status: READY TO USE ✓

Codex is fully installed and working in your WSL Ubuntu environment.

## How to Use Codex (Simplest Way)

### Step 1: Open PowerShell in Project Root

```powershell
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition
```

### Step 2: Launch WSL

```powershell
wsl
```

### Step 3: Start Codex

```bash
codex
```

### Step 4: Type Your Prompt

You'll see a Codex interactive terminal. Type your prompt:

```
analyze the data pipeline architecture
```

Press Enter and Codex will respond.

### Step 5: Continue or Exit

- Type more prompts (same session)
- Press `Ctrl+C` to exit

## Example Prompts to Try

```
what is this project about?
explain how the silver layer transformations work
show me the data flow from bronze to gold
find performance bottlenecks in the ETL pipeline
generate comprehensive unit tests for ChemBLExtractor
create Pydantic models for the bronze layer schema
refactor the compound transformer for vectorization
debug the gold_sink_disabled warning
add docstrings to all public methods
```

## Installation Confirmed

```
✓ Node.js v18.19.1
✓ npm 9.2.0
✓ Codex CLI v0.118.0
✓ WSL Ubuntu integration
✓ Codex accessible from any directory
```

## Navigation Shortcuts

In Codex interactive mode:

- `↑/↓` - Navigate command history
- `Tab` - Auto-complete
- `Ctrl+L` - Clear screen
- `Ctrl+C` - Exit

## If You Have Questions

- **Quick reference**: `docs/05-operations/tooling/scripts-ops/CODEX_WSL_QUICK_REF.md`
- **Detailed guide**: `docs/05-operations/tooling/scripts-ops/CODEX_WSL_SETUP.md`
- **How to run**: `docs/05-operations/tooling/scripts-ops/HOW_TO_RUN.md`

## Verification Commands

```powershell
# Check Codex version
wsl -- codex --version

# Check Codex help
wsl -- codex --help

# Test in interactive mode
wsl -- codex
```

## Important Notes

1. **First response takes 20-30 seconds** - This is normal (Codex connects to OpenAI)
1. **Use `wsl` to enter WSL** - Then run `codex` normally
1. **Stay in project directory** - For better context
1. **Press Ctrl+C to exit** - From Codex TUI
1. **Review output carefully** - Before applying auto-exec changes

## Common Tasks

### Analyze Code

```
explain the ChemBL extraction pipeline
```

### Generate Code

```
create comprehensive unit tests for this transformer
```

### Refactor

```
optimize these database queries for performance
```

### Debug

```
why does this health_check_degraded occur on startup?
```

### Document

```
generate docstrings for all methods in this module
```

______________________________________________________________________

**You're all set! Start with:** `wsl` then `codex`
