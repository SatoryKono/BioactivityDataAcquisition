# Codex Helper Scripts - Internal Documentation

## Overview

This directory contains **INTERNAL helper scripts** for Codex AI runtime support. These scripts are **not intended for direct invocation** by users or external processes. They are sourced or called by other scripts in the Codex runtime ecosystem.

## INTERNAL Scripts

All scripts in this directory are **INTERNAL** and should not be invoked directly. They are designed to be:

- **Sourced** by other scripts (library functions)
- **Called** by parent scripts (implementation helpers)
- **Used** by the Codex runtime bootstrap process

## Script Inventory

### Library Scripts (Source Only)

| Script | Purpose | Called By |
|--------|---------|-----------|
| `codex-auth-lib.sh` | Shared Codex auth probes for WSL launchers | `run-codex-impl.sh`, other WSL launchers |

### Implementation Helpers (Called by Parent Scripts)

| Script | Purpose | Called By |
|--------|---------|-----------|
| `run-codex-impl.sh` | Launch Codex implementation | `run-codex.sh`, `run-codex.ps1` |
| `check-env.sh` | Check and setup Codex environment (WSL) | `run-codex.sh` |
| `ensure-codex-cli.sh` | Ensure writable Codex CLI installation | Multiple parent scripts |
| `ensure-mcp.sh` | Keep Codex MCP config synchronized | `run-codex-impl.sh` |
| `setup-env.sh` | Setup missing components without apt-get | `run-codex.sh` |
| `run-codex-wsl-noninteractive.sh` | WSL non-interactive launch | WSL launchers |
| `wsl_proxy_env.sh` | Shared WSL proxy environment | Multiple parent scripts |

### Setup and Verification Scripts

| Script | Purpose | Called By |
|--------|---------|-----------|
| `setup-wsl.sh` | WSL setup | `setup-wsl-complete.sh` |
| `setup-wsl-complete.sh` | Complete WSL setup | Manual invocation or parent scripts |
| `test-basic.sh` | Basic tests | Verification scripts |
| `verify-setup.sh` | Verify setup | Manual invocation or parent scripts |

### PowerShell Helpers

| Script | Purpose | Called By |
|--------|---------|-----------|
| `diagnose-hang.ps1` | Diagnose Codex hang issues | Manual invocation |
| `check-env.ps1` | Check environment (PowerShell) | `run-codex.ps1` |
| `wsl-support.ps1` | WSL support utilities | PowerShell launchers |

## Usage Guidelines

### For Developers

- **DO NOT** invoke these scripts directly
- **DO** source library scripts: `source scripts/ai/codex/helper/codex-auth-lib.sh`
- **DO** call implementation helpers through parent scripts
- **DO** use public entry points: `scripts/ai/codex/run-codex.sh`

### For Maintenance

- Changes to helper scripts should be tested through parent scripts
- Library scripts should maintain backward compatibility
- Document any breaking changes in parent scripts
- Update this inventory when adding/removing scripts

## Ownership Markers

All scripts in this directory are marked as **INTERNAL** in their headers:

```bash
#!/usr/bin/env bash
# INTERNAL: Helper script for Codex runtime
# Called by: [parent script]
# DO NOT invoke directly
```

## Public Entry Points

For public-facing Codex operations, use:

- `scripts/ai/codex/run-codex.sh` - Main Codex launcher (bash)
- `scripts/ai/codex/run-codex.ps1` - Main Codex launcher (PowerShell)
- `scripts/ai/codex/run-codex-wsl-noninteractive.sh` - WSL non-interactive launcher

## Related Documentation

- `scripts/ai/codex/README.md` - Codex runtime documentation
- `scripts/ai/mcp/README.md` - MCP configuration documentation
- `docs/00-project/ai/` - AI runtime documentation

## Maintenance Notes

- These scripts are part of the **Codex runtime bootstrap chain**
- Changes should preserve the bootstrap sequence
- Test changes through the full Codex launch process
- Consider impact on both bash and PowerShell environments