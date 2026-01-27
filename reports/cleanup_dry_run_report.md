# BioETL Repository Cleanup - Dry-Run Report

**Generated:** 2026-01-27
**Status:** Dry-run (no changes applied)

---

## Executive Summary

| Category | Items Found | Action |
|----------|-------------|--------|
| Compiled files (.pyc, __pycache__) | 0 | None needed |
| Temporary scripts (sandbox, notebooks) | 0 | None needed |
| Legacy CLI scripts | 0 | None needed |
| Unused YAML configs | 0 | None needed |
| Duplicate report files | 7 pairs | Remove older versions |
| Duplicate utility functions | 0 critical | None needed |
| Typer dependency consolidation | 1 file | Convert to Click |
| Temporary root files | 1 | Remove |

**Total cleanup candidates:** 8 hyphen-named report files + 1 temp file + 1 script conversion

---

## 1. Compiled Files and Cache Directories

**Status:** Clean

No `.pyc` files or `__pycache__` directories were found in the repository. The `.gitignore` correctly excludes these patterns.

---

## 2. Temporary Scripts (Sandbox, Notebooks)

**Status:** Clean

No sandbox directories or Jupyter notebooks were found. The repository does not contain temporary experimental code.

---

## 3. Legacy CLI Scripts

**Status:** Clean

All CLI scripts in `src/bioetl/interfaces/cli/` use the standard Click framework. No deprecated or legacy CLI runners were found.

**CLI Commands Found (all using Click):**
- `main.py` - Entry point
- `commands/run.py` - Pipeline run command
- `commands/run_all.py` - Run all pipelines
- `commands/run_composite.py` - Composite pipeline
- `commands/cleanup.py` - Cleanup command
- `commands/health.py` - Health check
- `commands/config.py` - Configuration
- `commands/vacuum.py` - Delta vacuum
- `commands/checkpoint.py` - Checkpoint management
- `commands/quarantine.py` - Quarantine management
- `commands/export.py` - Export functionality
- `commands/archive.py` - Archive command
- `commands/lock.py` - Lock management
- `commands/maintenance.py` - Maintenance tasks

---

## 4. Unused YAML Configurations

**Status:** Clean

All YAML configurations in `configs/` are referenced in the codebase:
- `configs/pipelines/` - 21 pipeline configurations (all 7 providers)
- `configs/filter/` - Filter configurations per entity
- `configs/dq/` - Data quality configurations
- `configs/sources/` - Source configurations
- `configs/composite/` - Composite pipeline configurations

---

## 5. Duplicate Report Files (CLEANUP NEEDED)

**Status:** 7 pairs of duplicate files with inconsistent naming

The `reports/` directory contains duplicate merged files with different naming conventions:
- Hyphen-separated (`-merged.md`) - older versions from Jan 27 19:06
- Underscore-separated (`_merged.md`) - newer versions from Jan 27 22:18

### Files to Remove (older hyphen-named versions):

| File | Size | Recommendation |
|------|------|----------------|
| `reports/application-merged.md` | 916K | REMOVE (superseded by `application_merged.md`) |
| `reports/composition-merged.md` | 350K | REMOVE (superseded by `composition_merged.md`) |
| `reports/configs-merged.md` | 194K | REMOVE (superseded by `configs_merged.md`) |
| `reports/documentation-merged.md` | 2.5M | REMOVE (superseded by `documentation_merged.md`) |
| `reports/domain-merged.md` | 1.1M | REMOVE (superseded by `domain_merged.md`) |
| `reports/infrastructure-merged.md` | 983K | REMOVE (superseded by `infrastructure_merged.md`) |
| `reports/interfaces-merged.md` | 98K | REMOVE (identical to `interfaces_merged.md`) |
| `reports/project-structure.md` | 648K | REMOVE (superseded by `project_structure.md`) |

**Total space to be freed:** ~6.8 MB

---

## 6. Duplicate Utility Functions

**Status:** Clean

Analysis of utility modules found no critical duplicates:

### Utility Modules Analyzed:
| Module | Location | Functions | Status |
|--------|----------|-----------|--------|
| `transform_utils.py` | `application/core/` | 8 | Clean (delegates to domain) |
| `xml_utils.py` | `pipelines/pubmed/` | 2 | Clean |
| `utils.py` | `pipelines/uniprot/extractors/` | Class-based | Clean |
| `logging_utils.py` | `infrastructure/adapters/` | 1 | Clean |
| `utils.py` | `application/services/dq/` | 2 | Clean |
| `runner_helpers.py` | `application/composite/` | 4 | Clean |
| `span_helpers.py` | `application/observability/` | 2 | Clean |
| `helpers.py` | `infrastructure/quarantine/` | 2 | Clean |
| `run_helpers.py` | `interfaces/cli/commands/` | 4 | Clean |

### Provider-Specific Functions (Intentionally Different):
- `extract_authors()` - Different implementations per provider (CrossRef, SemanticScholar, OpenAlex)
- `extract_journal_info()` - Different API formats require different parsing
- `extract_affiliations()` - Provider-specific data structures

These are **NOT** duplicates - they handle different API response formats.

---

## 7. Typer Dependency Consolidation

**Status:** Single file uses Typer instead of Click

The project standard is **Click** (per CLAUDE.md), but `scripts/cleanup_consolidate.py` uses **Typer**.

### Current State:
- **Click usage:** 17 files in `src/bioetl/interfaces/cli/`
- **Typer usage:** 1 file in `scripts/cleanup_consolidate.py`

### Recommendation:
Convert `scripts/cleanup_consolidate.py` to Click for consistency. Alternatively, remove Typer from dependencies if not needed elsewhere.

**Note:** Typer depends on Click internally, so using both adds unnecessary complexity.

---

## 8. Temporary Root Files

**Status:** 1 file found

| File | Size | Recommendation |
|------|------|----------------|
| `test_output.txt` | 3.6K (66 lines) | REMOVE (test artifact) |

---

## 9. Unused Imports and Dependencies

### Unused Dependencies in pyproject.toml:
Based on analysis, all core dependencies are used. However:

| Dependency | Used In | Notes |
|------------|---------|-------|
| `typer>=0.12` | `scripts/cleanup_consolidate.py` only | Could be removed if script converted to Click |

### Import Analysis:
The existing `scripts/cleanup_consolidate.py` script provides comprehensive import analysis. No critical unused imports were detected in the main codebase.

---

## 10. Planned Changes Summary

### Files to Delete:
```
reports/application-merged.md
reports/composition-merged.md
reports/configs-merged.md
reports/documentation-merged.md
reports/domain-merged.md
reports/infrastructure-merged.md
reports/interfaces-merged.md
reports/project-structure.md
test_output.txt
```

### Scripts to Refactor:
```
scripts/cleanup_consolidate.py  # Convert from Typer to Click
```

### Dependencies to Review:
```
typer>=0.12  # Consider removal after Click conversion
```

---

## 11. Verification Commands

```bash
# Verify no .pyc files
find . -name "*.pyc" -type f 2>/dev/null | wc -l

# Verify no __pycache__
find . -name "__pycache__" -type d 2>/dev/null | wc -l

# Check duplicate reports
ls -la reports/*-merged.md reports/*_merged.md

# Verify Click vs Typer usage
grep -r "import typer\|from typer" --include="*.py" .
grep -r "import click\|from click" --include="*.py" src/

# Run existing cleanup script (dry-run)
python scripts/cleanup_consolidate.py
```

---

## Appendix: Module Statistics

### By Layer:
| Layer | Python Files | Utility Modules |
|-------|-------------|-----------------|
| domain | ~90 | 0 |
| application | ~120 | 6 |
| infrastructure | ~80 | 2 |
| interfaces | ~30 | 1 |
| composition | ~20 | 0 |

### Code Quality:
- Total Python files: ~516
- Total lines of code: ~110,300
- Test files: ~7,770
- Utility modules: ~1,200 LOC across 10 files

---

*Report generated by BioETL cleanup analysis*
