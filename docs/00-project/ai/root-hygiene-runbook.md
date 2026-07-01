# Root Hygiene Runbook

## Overview

This runbook provides operator guidance for managing local-only runtime, cache, and vendor root surfaces in the BioETL repository.

## Root Surface Classification

### Curated Shared Roots
These are tracked roots that contain project artifacts and are part of the committed repository:

- `artifacts/` - Debug export evidence and governed diagnostics
- `docs/` - Project documentation
- `reports/` - Quality reports and governance artifacts
- `scripts/` - Operator scripts and tooling
- `src/` - Source code
- `tests/` - Test suite
- `configs/` - Configuration files

### Local-Only Runtime/Cache Roots
These are transient regenerable artifacts that should remain untracked:

- `.venv/`, `.venv-win/`, `.venv-wsl/` - Python virtual environments
- `.pytest_cache/` - Pytest cache
- `.ruff_cache/` - Ruff linting cache
- `.mypy_cache/` - MyPy type checking cache
- `.import_linter_cache/` - Import linter cache
- `.coverage-sharded-current-main/` - Coverage sharding cache
- `.hypothesis/` - Hypothesis test cache
- `.benchmarks/` - Benchmark results
- `.cache/` - General cache directory
- `node_modules/` - Node.js dependencies
- `.npm-cache/` - NPM cache

### Local-Only Vendor/Editor Roots
These are AI/editor runtime surfaces that are machine-local:

- `.agents/` - AI agent runtime
- `.cache/` - General cache
- `.claude/` - Claude AI editor
- `.cursor/` - Cursor AI editor
- `.windsurf/` - Windsurf AI editor
- `.junie/` - Junie AI editor
- `.qodo/` - Qodo AI editor
- `.sonarlint/` - SonarLint editor
- `.devin/` - Devin AI editor
- `.ai/` - Generic AI runtime
- `.gemini/` - Gemini AI runtime
- `.jules/` - Jules AI editor

### Transitional Local-Only Aliases
These are temporary local-only aliases for transitional tooling:

- `script-codex` - Transitional alias for Codex launcher (canonical: `scripts/ai/codex/`)
- `script-gemini` - Transitional alias for Gemini launcher (canonical: `scripts/ai/gemini/`)
- `script-mistrall` - Transitional alias for Mistral launcher (canonical: `scripts/ai/vibe/`)
- `script-mistrallvibe` - Transitional alias for Mistral Vibe launcher (canonical: `scripts/ai/vibe/`)

## Pruning / Rebuild Guidance

### Python Virtual Environments
```bash
# Remove and rebuild virtual environment
rm -rf .venv/
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

### Cache Directories
```bash
# Clear all Python caches
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/ .import_linter_cache/ .hypothesis/ .benchmarks/ .cache/
```

### Node Dependencies
```bash
# Remove and reinstall Node modules
rm -rf node_modules/ .npm-cache/
npm install
```

### Vendor/Editor Roots
These should remain untracked. If they appear in git status:
```bash
# Verify they are in .gitignore
grep -E "\.(agents|claude|cursor|windsurf|junie|qodo|sonarlint|devin|ai|gemini|jules)/" .gitignore

# If not, add them to .gitignore
echo ".agents/" >> .gitignore
echo ".claude/" >> .gitignore
# ... etc
```

### Transitional Aliases
These should be removed and replaced with canonical paths:
```bash
# Remove transitional aliases
rm -f script-codex script-gemini script-mistrall script-mistrallvibe

# Use canonical paths instead
python -m scripts.ai.codex vibe
python -m scripts.ai.gemini ...
python -m scripts.ai.vibe ...
```

## Governance Checks

### Root Hygiene Audit
```bash
# Run root cleanliness audit
python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
```

### Scripts Inventory
```bash
# Check scripts inventory
python scripts/engineering/repo/check_scripts_inventory.py
```

## CI Enforcement

The following CI checks enforce no-growth governance:

1. **Root Hygiene Tests** - `tests/architecture/test_root_hygiene_review_registry.py`
   - Fails on unreviewed root surfaces
   - Validates classification against `configs/quality/root_hygiene_review_registry.yaml`

2. **Scripts Inventory Tests** - `tests/architecture/test_scripts_inventory.py`
   - Fails on unreviewed script growth
   - Validates against `configs/quality/scripts_inventory_manifest.json`

## Convergence Path for Transitional Aliases

### script-codex
- **Current status**: Local-only transitional alias
- **Canonical replacement**: `python -m scripts.ai.codex vibe` or `scripts/ops/launchers/codex/codex.sh`
- **Retirement condition**: After operator migration to canonical paths (target: 2026-08-01)
- **Action**: Remove alias, update documentation to use canonical paths

### script-gemini
- **Current status**: Local-only transitional alias
- **Canonical replacement**: `python -m scripts.ai.gemini ...`
- **Retirement condition**: After Gemini runtime activation (target: 2026-09-01)
- **Action**: Remove alias, update documentation to use canonical paths

### script-mistrall / script-mistrallvibe
- **Current status**: Local-only transitional alias
- **Canonical replacement**: `python -m scripts.ai.vibe ...`
- **Retirement condition**: After operator migration to canonical paths (target: 2026-08-01)
- **Action**: Remove alias, update documentation to use canonical paths

## Related Governance

- `configs/quality/root_hygiene_review_registry.yaml` - Root surface classification
- `configs/quality/scripts_inventory_manifest.json` - Scripts inventory
- `tests/architecture/test_root_hygiene_review_registry.py` - Root hygiene tests
- `tests/architecture/test_scripts_inventory.py` - Scripts inventory tests
