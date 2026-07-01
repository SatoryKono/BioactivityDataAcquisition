# Supporting Scripts Governance

## Overview

This document provides governance for the 88 supporting scripts tracked in `configs/quality/scripts_inventory_manifest.json`.

## Current State

Based on the scripts inventory:
- Total scripts: 448
- Active scripts: 360
- Supporting scripts: 88

## Supporting Script Classification

### Canonical Operator Entrypoints
These are the primary operator-facing scripts that should be preserved:

- `scripts/ai/__main__.py` - AI runtime entrypoint
- `scripts/ops/__main__.py` - Operations entrypoint
- `scripts/engineering/__main__.py` - Engineering entrypoint
- `scripts/ai/vibe/` - Mistral Vibe AI runtime
- `scripts/ai/codex/` - Codex AI runtime
- `scripts/ai/gemini/` - Gemini AI runtime
- `scripts/ops/launchers/codex/` - Codex launchers

### Reviewed Local/Setup Wrappers
These are setup and local development helpers that are reviewed and maintained:

- `scripts/ai/codex/helper/` - Codex setup helpers
- `scripts/ai/codex/diagnose_wsl.*` - WSL diagnostics
- `scripts/ai/codex/headless.*` - Headless Codex launchers
- `scripts/ops/support/` - Operations support scripts

### Temporary Compatibility Wrappers
These are temporary compatibility shims that should be removed when no longer needed:

- `scripts/ai/codex/fix-nodejs.sh` - Node.js version fix (supporting, 0 references)
- `scripts/ai/codex/cursor-launch.ps1` - Cursor launcher (supporting, 0 references)

### Internal Launcher Variants
These are internal launcher variants for specific use cases:

- `scripts/ops/launchers/codex/` - Multiple Codex launcher variants
- `scripts/ai/codex/` - Multiple Codex launcher variants

## Consolidation Plan

### Windows Wrappers
Current: 22 `windows_compatibility_wrapper` entries
Target: ≤10

Strategy:
1. Audit which wrappers are actively used
2. Consolidate duplicate wrappers
3. Document Windows/WSL compatibility strategy
4. Remove obsolete wrappers

### Legacy Utilities
Current: 32 `legacy_manual_utility` entries
Target: ≤10

Strategy:
1. Identify utilities with no active callers
2. Deprecate with warnings (2 weeks)
3. Remove deprecated utilities
4. Update documentation

### Compatibility Shims
Current: 5 `compatibility_wrapper` entries
Target: 0

Strategy:
1. Audit callers for each shim
2. Migrate callers to canonical paths
3. Remove shims
4. Update governance tests

### Shared Helpers
Current: 22 `shared_helper_module` entries
Target: Consolidated

Strategy:
1. Consolidate duplicate helpers
2. Promote to active inventory where appropriate
3. Document shared helper API
4. Update imports

## Retention Policy

### Keep
- Canonical operator entrypoints
- Reviewed local/setup wrappers with active usage
- Internal launcher variants with documented use cases

### Remove
- Temporary compatibility wrappers with 0 references
- Legacy utilities with no active callers
- Duplicate wrappers where canonical flow exists

### Freeze
- Supporting wrappers with overlapping operator value
- Internal launcher variants without clear use case

## Governance Checks

### Scripts Inventory
```bash
# Check scripts inventory
python scripts/engineering/repo/check_scripts_inventory.py
```

### Lifecycle Registry
```bash
# Check lifecycle registry
python scripts/engineering/qa/audit_scripts_lifecycle.py
```

## CI Enforcement

The following CI checks enforce no-growth governance:

1. **Scripts Inventory Tests** - `tests/architecture/test_scripts_inventory.py`
   - Fails on unreviewed script growth
   - Validates against `configs/quality/scripts_inventory_manifest.json`

2. **Scripts Lifecycle Tests** - `tests/architecture/test_scripts_lifecycle.py`
   - Fails on unreviewed lifecycle changes
   - Validates against `configs/quality/scripts_lifecycle_registry.json`

## Next Steps

1. Complete audit of all 88 supporting scripts
2. Create detailed removal plan for each category
3. Execute consolidation plan
4. Update lifecycle registry
5. Update architecture tests

## Related Governance

- `configs/quality/scripts_inventory_manifest.json` - Scripts inventory
- `configs/quality/scripts_lifecycle_registry.json` - Lifecycle registry
- `tests/architecture/test_scripts_inventory.py` - Scripts inventory tests
- `tests/architecture/test_scripts_lifecycle.py` - Lifecycle tests
