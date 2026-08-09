______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Script Documentation Standards

## Purpose

This document defines the documentation standards for all scripts in the BioETL project to ensure consistency, discoverability, and maintainability across the codebase.

## Scope

This policy applies to all script files in the `scripts/**` directory, including:
- Python scripts (`.py`)
- Shell scripts (`.sh`)
- PowerShell scripts (`.ps1`)
- Batch files (`.bat`)

## Current State Analysis

### Python Scripts
- **Total:** 406 scripts
- **With docstrings:** 360 scripts (88.7%)
- **Without docstrings:** 46 scripts (11.3%)

### Shell Scripts
- **Total:** 111 scripts
- **With header comments:** 106 scripts (95.5%)
- **Without header comments:** 5 scripts (4.5%)

**Overall compliance:** 90% (466 compliant out of 517 total scripts)

## Python Script Documentation Standards

### Docstring Format

**Convention:** Google-style docstrings

**Pattern:**
```python
#!/usr/bin/env python3
"""Brief one-line description of the script.

Extended description of the script's purpose and functionality.
Include important context, dependencies, and usage patterns.

Usage:
    python -m scripts.module.name <command> [args...]
    python scripts/module/name.py <command> [args...]

Commands:
    command1    Description of command1
    command2    Description of command2

Examples:
    # Example usage
    python -m scripts.module.name command1 --option value

Args:
    argv: Command line arguments (optional, defaults to sys.argv)

Returns:
    int: Exit code (0 for success, non-zero for failure)

Raises:
    ValueError: When invalid arguments are provided
    RuntimeError: When required dependencies are missing
"""

from __future__ import annotations
```

### Required Elements

1. **Brief one-line description** - First line should be a concise summary
2. **Extended description** - Paragraph explaining purpose and context
3. **Usage section** - How to invoke the script
4. **Commands/Arguments section** - Available commands or required arguments
5. **Examples section** - Concrete usage examples
6. **Returns/Raises sections** - For functions with return values or exceptions

### Optional Elements

- **Dependencies section** - Required external packages
- **Environment variables** - Required environment variables
- **See Also section** - Related scripts or documentation
- **Notes section** - Important implementation notes

## Shell Script Documentation Standards

### Header Format

**Convention:** Shell script header with purpose and usage

**Pattern:**
```bash
#!/usr/bin/env bash
# Brief one-line description of the script.
#
# Extended description of the script's purpose and functionality.
# Include important context, dependencies, and usage patterns.
#
# Usage:
#   bash scripts/module/name.sh <command> [args...]
#   ./scripts/module/name.sh <command> [args...]
#
# Commands:
#   command1    Description of command1
#   command2    Description of command2
#
# Examples:
#   # Example usage
#   bash scripts/module/name.sh command1 --option value
#
# Environment Variables:
#   VAR_NAME    Description of required environment variable
#
# Dependencies:
#   - Required command/tool
#   - Required package
#
# See Also:
#   - Related documentation
#   - Related scripts

set -euo pipefail
```

### Required Elements

1. **Shebang line** - `#!/usr/bin/env bash` or appropriate interpreter
2. **Brief one-line description** - First comment line
3. **Extended description** - Paragraph explaining purpose and context
4. **Usage section** - How to invoke the script
5. **Commands/Arguments section** - Available commands or required arguments
6. **Examples section** - Concrete usage examples

### Optional Elements

- **Environment Variables section** - Required environment variables
- **Dependencies section** - Required external tools or packages
- **See Also section** - Related scripts or documentation
- **Notes section** - Important implementation notes

## PowerShell Script Documentation Standards

### Header Format

**Convention:** PowerShell script header with purpose and usage

**Pattern:**
```powershell
# Brief one-line description of the script.
#
# Extended description of the script's purpose and functionality.
# Include important context, dependencies, and usage patterns.
#
# Usage:
#   .\scripts\module\name.ps1 <command> [args...]
#
# Parameters:
#   -Parameter1: Description of parameter1
#   -Parameter2: Description of parameter2
#
# Examples:
#   # Example usage
#   .\scripts\module\name.ps1 -Parameter1 value -Parameter2 value
#
# Environment Variables:
#   - VAR_NAME: Description of required environment variable
#
# Dependencies:
#   - Required module
#   - Required command/tool
#
# See Also:
#   - Related documentation
#   - Related scripts

param(
    [string]$Parameter1,
    [string]$Parameter2
)
```

## Batch File Documentation Standards

### Header Format

**Convention:** Batch file header with purpose and usage

**Pattern:**
```batch
@echo off
REM Brief one-line description of the script.
REM
REM Extended description of the script's purpose and functionality.
REM Include important context, dependencies, and usage patterns.
REM
REM Usage:
REM   scripts\module\name.bat <command> [args...]
REM
REM Parameters:
REM   %1: Description of first parameter
REM   %2: Description of second parameter
REM
REM Examples:
REM   # Example usage
REM   scripts\module\name.bat value1 value2
REM
REM Environment Variables:
REM   - VAR_NAME: Description of required environment variable
REM
REM Dependencies:
REM   - Required command/tool
REM
REM See Also:
REM   - Related documentation
REM   - Related scripts
```

## Special Cases

### Helper Scripts

Helper scripts in subdirectories should follow the same standards but can have simplified documentation:

```python
#!/usr/bin/env python3
"""Helper function for X operation.

Used by: parent_script.py
Internal: Do not invoke directly
"""
```

### Entry Point Scripts

Entry point scripts (`__main__.py`) should include command documentation:

```python
#!/usr/bin/env python3
"""Unified entry point for scripts/module/ commands.

Usage:
    python -m scripts.module <command> [args...]
    python -m scripts.module --help

Commands:
    command1    Description of command1
    command2    Description of command2
"""
```

### MCP Wrapper Scripts

MCP wrapper scripts should include MCP-specific documentation:

```bash
#!/usr/bin/env bash
# MCP wrapper for server-name.
#
# This script provides a standardized interface to the server-name MCP server.
# It handles environment setup, token management, and error handling.
#
# Usage:
#   bash scripts/ai/mcp/mcp_server_name_wrapper.sh <mcp-args...>
#
# Environment Variables:
#   SERVER_API_KEY: Required API key for server-name
#   SERVER_ENDPOINT: Optional custom endpoint
#
# See Also:
#   - MCP configuration: scripts/ops/runtime/mcp/shared-servers.json
```

## Enforcement

### Pre-commit Hooks

Add pre-commit hooks to enforce documentation standards:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-python-docstrings
      name: Check Python script docstrings
      entry: scripts/engineering/repo/check_python_docstrings.py
      language: script
      files: \.py$
      types: [python]

    - id: check-shell-headers
      name: Check shell script headers
      entry: scripts/engineering/repo/check_shell_headers.py
      language: script
      files: \.(sh|ps1|bat)$
```

### CI Validation

Add CI validation to prevent undocumented scripts from being merged:

```yaml
# .github/workflows/script-documentation.yml
name: Script Documentation Standards
on: [pull_request]
jobs:
  check-documentation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check script documentation
        run: python scripts/engineering/repo/validate_script_documentation.py
```

## Migration Strategy

### Phase 1: High-Impact Scripts (Priority: HIGH)
- Scripts in `scripts/ai/codex/` - core AI runtime
- Scripts in `scripts/ai/mcp/` - MCP integration
- Scripts in `scripts/engineering/dev/` - development tools
- Scripts in `scripts/ops/` - operational scripts

### Phase 2: Medium-Impact Scripts (Priority: MEDIUM)
- Scripts in `scripts/docs/` - documentation tools
- Scripts in `scripts/diagrams/` - diagram tools
- Scripts in `scripts/data_quality/` - data quality tools

### Phase 3: Low-Impact Scripts (Priority: LOW)
- Helper scripts in subdirectories
- Legacy/deprecated scripts
- One-off maintenance scripts

## Documentation Quality Checklist

### Python Scripts
- [ ] Has Google-style docstring
- [ ] Includes brief one-line description
- [ ] Includes extended description
- [ ] Includes usage section
- [ ] Includes commands/arguments section
- [ ] Includes examples section
- [ ] Includes returns/raises sections (if applicable)

### Shell Scripts
- [ ] Has shebang line
- [ ] Has header comment with purpose
- [ ] Includes extended description
- [ ] Includes usage section
- [ ] Includes commands/arguments section
- [ ] Includes examples section
- [ ] Includes environment variables (if applicable)

## Related Documents

- [Script Naming Conventions](script-naming-conventions.md) - Naming standards for scripts
- [Script Inventory Audit](../../reports/scripts_inventory_audit_report.md) - Overall script inventory
- [PEP 257 - Docstring Conventions](https://peps.org/pep-0257/)
- [Google Style Python Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)

## Revision History

- **2026-08-09:** Initial documentation standards definition based on script audit
