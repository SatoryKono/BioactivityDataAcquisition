# Codex Setup Guide

## Overview

Codex is an AI-powered code assistant that helps analyze, refactor, and improve your codebase. This guide explains how to use it in the BioactivityDataAcquisition project.

## Prerequisites

✅ Installed:

- WSL2 with Debian distro
- wsl-vpnkit (for API connectivity)
- Codex CLI (v0.118.0+)

## Quick Start

### 1. Setup WSL VPN (one-time)

Run from PowerShell in the project root:

```powershell
cd e:\g-drive\05_AI\github\BioactivityDataAcquisition
.\scripts\engineering\dev\.setup_wsl_codex.sh
```

### 2. Interactive Mode

Start Codex for interactive analysis:

```bash
.\scripts\ops\codex.bat
```

Then type your prompt directly in the TUI.

### 3. Prompt Mode

Pass a prompt directly:

```bash
.\scripts\ops\codex.bat "analyze the ChemBL data extraction pipeline"
.\scripts\ops\codex.bat "refactor main.py for better performance"
.\scripts\ops\codex.bat "add comprehensive error handling to bioetl/data_loader.py"
```

### 4. Auto-Execution Mode

Run with auto-approval (full-auto):

```bash
.\scripts\ops\codex-exec.bat "fix all TODO comments in the codebase"
```

## Usage Examples

### Code Analysis

```bash
.\scripts\ops\codex.bat "explain the data transformation pipeline in silver layer"
.\scripts\ops\codex.bat "identify performance bottlenecks in the ETL pipeline"
```

### Code Generation

```bash
.\scripts\ops\codex.bat "add comprehensive unit tests for ChemBLExtractor class"
.\scripts\ops\codex.bat "generate Pydantic models for the bronze layer schema"
```

### Refactoring

```bash
.\scripts\ops\codex.bat "refactor the compound transformer to use vectorized operations"
.\scripts\ops\codex.bat "optimize database query performance in bioetl/database.py"
```

### Debugging

```bash
.\scripts\ops\codex.bat "debug the 'gold_sink_disabled' warning in the pipeline"
.\scripts\ops\codex.bat "fix the health_check_degraded issue during pipeline startup"
```

## Advanced Options

### Config Overrides

```bash
.\scripts\ops\codex.bat -c model="o3" "analyze pipeline performance"
```

### Sandbox Modes

```bash
.\scripts\ops\codex.bat -s read-only "review security of data access patterns"
.\scripts\ops\codex.bat -s workspace-write "refactor and apply changes automatically"
```

### Web Search

```bash
.\scripts\ops\codex.bat --search "research best practices for ETL frameworks"
```

### Multiple Directories

```bash
.\scripts\ops\codex.bat --add-dir data "analyze both code and data structure"
```

## Troubleshooting

### "Codex not found"

Install with: `npm install -g @openai/codex`

### "Unable to resolve repo path"

- Ensure you're in the project directory
- Check WSL2 is running: `wsl -l -v`

### "OpenAI API unreachable"

- Verify wsl-vpnkit is running: `wsl -d wsl-vpnkit -- /app/wsl-vpnkit &`
- Re-run VPN setup: `.\scripts\engineering\dev\.setup_wsl_codex.sh`

### "Connection timeout"

- Check: `.\scripts\engineering\dev\.setup_wsl_codex.sh` for connectivity status

## Files Modified

- `scripts/ops/launchers/codex/codex.bat` - Main launcher (interactive & prompt modes)
- `scripts/ops/launchers/codex/codex-exec.bat` - Auto-execution launcher
- `scripts/engineering/dev/.setup_wsl_codex.sh` - VPN setup (unchanged)

## Best Practices

1. **Start with analysis**: Use interactive mode first to understand the code
1. **Use read-only sandbox**: When exploring unfamiliar code
1. **Iterative refinement**: Ask follow-up questions in same session
1. **Version control**: Always review changes before applying
1. **Test thoroughly**: Codex output should be reviewed before production

## Environment

- **Working Directory**: Automatically set to project root
- **API Model**: Uses default from ~/.codex/config.toml (typically GPT-4 or o3)
- **Sandbox Policy**: Default is read-only for safety
- **VPN Gateway**: 172.26.16.1 (wsl-vpnkit)

## Notes

- Codex preserves terminal scrollback (no alternate screen by default)
- All commands run in the BioactivityDataAcquisition root directory context
- WSL2 VPN configuration is required for OpenAI API access
