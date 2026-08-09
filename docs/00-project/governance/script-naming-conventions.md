______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Script Naming Conventions Policy

## Purpose

This document defines the naming conventions for all scripts in the BioETL project to ensure consistency, discoverability, and maintainability across the codebase.

## Scope

This policy applies to all script files in the `scripts/**` directory, including:
- Python scripts (`.py`)
- Shell scripts (`.sh`)
- PowerShell scripts (`.ps1`)
- Batch files (`.bat`)

## Naming Conventions

### Python Scripts

**Convention:** `snake_case`

**Pattern:** `lowercase_with_underscores.py`

**Examples:**
- ✅ `run_tests.py`
- ✅ `check_env.py`
- ✅ `setup_mcp.py`
- ❌ `run-tests.py`
- ❌ `checkEnv.py`
- ❌ `setup-mcp.py`

**Rationale:** Python PEP 8 recommends snake_case for module names and most Python projects follow this convention.

### Shell Scripts

**Convention:** `kebab-case`

**Pattern:** `lowercase-with-hyphens.sh`

**Examples:**
- ✅ `run-tests.sh`
- ✅ `check-env.sh`
- ✅ `setup-mcp.sh`
- ❌ `run_tests.sh`
- ❌ `checkEnv.sh`
- ❌ `setup_mcp.sh`

**Rationale:** Kebab-case is the standard for shell scripts and command-line tools, making them more readable and consistent with Unix conventions.

### PowerShell Scripts

**Convention:** `kebab-case`

**Pattern:** `lowercase-with-hyphens.ps1`

**Examples:**
- ✅ `run-tests.ps1`
- ✅ `check-env.ps1`
- ✅ `setup-mcp.ps1`
- ❌ `run_tests.ps1`
- ❌ `checkEnv.ps1`
- ❌ `setup_mcp.ps1`

**Rationale:** PowerShell community standards recommend kebab-case for cmdlets and scripts.

### Batch Files

**Convention:** `kebab-case`

**Pattern:** `lowercase-with-hyphens.bat`

**Examples:**
- ✅ `run-tests.bat`
- ✅ `check-env.bat`
- ✅ `setup-mcp.bat`
- ❌ `run_tests.bat`
- ❌ `checkEnv.bat`
- ❌ `setup_mcp.bat`

**Rationale:** Consistency with shell scripts and Windows batch file conventions.

## Special Cases

### Helper Scripts

Helper scripts in subdirectories should follow the same naming conventions:

- ✅ `helper/check-env.sh`
- ✅ `helper/setup-env.sh`
- ❌ `helper/check_env.sh`
- ❌ `helper/setup_env.sh`

### MCP Wrapper Scripts

MCP wrapper scripts should use kebab-case with `mcp-` prefix:

- ✅ `mcp-code-analyzer-wrapper.sh`
- ✅ `mcp-brave-search-wrapper.sh`
- ❌ `mcp_code_analyzer_wrapper.sh`
- ❌ `mcpBraveSearchWrapper.sh`

### AI Runtime Scripts

AI runtime scripts should follow their respective conventions:

- Python: `check_junie_mirror.py`
- Shell: `check-junie-mirror.sh`

## Current State Analysis

### Python Scripts
- **Total:** 406 scripts
- **Compliant:** 405 scripts (99.8%)
- **Non-compliant:** 1 script (0.2%)
  - `scripts/ops/runtime/mcp/apply-shared-to-devin.py`

### Shell Scripts
- **Total:** 111 scripts
- **Compliant:** 42 scripts (38%)
- **Non-compliant:** 69 scripts (62%)

**Most common non-compliant patterns:**
- Underscores instead of hyphens: `check_skills_layout.sh`
- Mixed naming: `diagnose_wsl.sh`
- Wrapper scripts: `mcp_code_analyzer_wrapper.sh`

## Migration Strategy

### Phase 1: High-Impact Scripts (Priority: HIGH)
- Scripts in `scripts/ai/mcp/` - heavily used MCP wrappers
- Scripts in `scripts/ai/codex/` - core AI runtime
- Scripts in `scripts/ops/` - operational scripts

### Phase 2: Medium-Impact Scripts (Priority: MEDIUM)
- Scripts in `scripts/engineering/` - development tools
- Scripts in `scripts/docs/` - documentation tools
- Scripts in `scripts/diagrams/` - diagram tools

### Phase 3: Low-Impact Scripts (Priority: LOW)
- Helper scripts in subdirectories
- Legacy/deprecated scripts
- One-off maintenance scripts

## Enforcement

### Pre-commit Hooks

Add pre-commit hooks to enforce naming conventions:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-python-naming
      name: Check Python script naming (snake_case)
      entry: scripts/engineering/repo/check_python_script_naming.sh
      language: script
      files: \.py$
      types: [python]

    - id: check-shell-naming
      name: Check shell script naming (kebab-case)
      entry: scripts/engineering/repo/check_shell_script_naming.sh
      language: script
      files: \.(sh|ps1|bat)$
```

### CI Validation

Add CI validation to prevent non-compliant scripts from being merged:

```yaml
# .github/workflows/script-naming.yml
name: Script Naming Conventions
on: [pull_request]
jobs:
  check-naming:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check script naming
        run: python scripts/engineering/repo/validate_script_naming.py
```

## Rollout Plan

1. **Policy Definition** (Current)
   - Document naming conventions
   - Define migration strategy
   - Create validation tools

2. **Tooling Setup** (Week 1)
   - Implement pre-commit hooks
   - Add CI validation
   - Create migration scripts

3. **Phase 1 Migration** (Week 2-3)
   - Rename high-impact scripts
   - Update all references
   - Update documentation

4. **Phase 2 Migration** (Week 4-5)
   - Rename medium-impact scripts
   - Update all references
   - Update documentation

5. **Phase 3 Migration** (Week 6-7)
   - Rename low-impact scripts
   - Update all references
   - Update documentation

6. **Cleanup** (Week 8)
   - Remove deprecated aliases
   - Final validation
   - Documentation update

## Exceptions

Exceptions to this policy require explicit approval from the BioETL Team and must be documented in the script's header comment:

```bash
#!/usr/bin/env bash
# EXCEPTION: Non-standard naming for backward compatibility
# Approved by: BioETL Team
# Reason: External tooling dependency requires this name
# Sunset date: 2026-12-31
```

## Related Documents

- [Makefile and Temporary Scripts Management](makefile-and-temporary-scripts-management.md) - Script lifecycle and cleanup policy
- [Scripts Inventory Manifest](../../../configs/quality/scripts_inventory_manifest.json) - Governed script inventory
- [PEP 8 Style Guide](https://peps.org/pep-0008/)
- [PowerShell Naming Conventions](https://learn.microsoft.com/en-us/powershell/scripting/dev-cross-plat/guidelines/using-correct-casing)
- [Shell Script Best Practices](https://github.com/koalaman/shellcheck)

## Revision History

- **2026-08-09:** Initial policy definition based on script inventory audit
