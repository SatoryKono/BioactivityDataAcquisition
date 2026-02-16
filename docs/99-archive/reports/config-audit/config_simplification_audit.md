# Config Simplification Audit

**Date**: 2026-02-16
**Scope**: All config files (configs/, .github/workflows/, root configs, pyproject.toml, Makefile)
**Focus**: Maintainability, readability, duplication reduction
**Previous audit**: 2026-02-03 (ADR compliance - PASS, 0 critical issues)

---

## Executive Summary

The project has **295+ config files** totaling **~10,000+ lines** of YAML/TOML/JSON. While functionally correct (confirmed by previous audit), the configs suffer from **structural duplication** that hinders maintainability.

Key metrics:

| Area | Files | Lines | Duplication Est. |
|------|-------|-------|------------------|
| configs/ (ETL) | 125 | 6,400+ | ~35-40% |
| .github/workflows/ | 17 | 1,782 | ~25-30% |
| Root configs | 7 | ~1,200 | ~15% |
| **Total** | **149** | **~9,400** | **~30%** |

**Top 3 problems:**
1. Composite pipeline configs are 2,417 lines for 5 files (avg 483 LOC) with massive column_groups and cross-validation duplication
2. CI workflows repeat identical Python setup, cache, and artifact patterns across 13+ files
3. pyproject.toml has duplicate dependency declarations between `[project.optional-dependencies]` and `[dependency-groups]`

---

## 1. ETL Configs (`configs/`)

### 1.1 Composite Pipelines: Main Pain Point

**5 composite pipeline configs = 2,417 lines (68% of all pipeline config lines).**

| File | Lines | Issue |
|------|-------|-------|
| composite/publication.yaml | 781 | 60 exclude_fields + 100 field_priorities + 160 column_groups |
| composite/target.yaml | 495 | Similar pattern |
| composite/molecule.yaml | 411 | Similar pattern |
| composite/activity.yaml | 383 | Similar pattern |
| composite/assay.yaml | 347 | Similar pattern |

**Specific duplication patterns:**

**A) `column_groups` repeated across composites:**
Each composite defines a `system` group with identical fields (`entity_id`, `content_hash`, `_run_id`, `_run_type`, `_source_batch_id`, `_source`, `_ingestion_ts`, `_index`). This exact block appears in all 5 composites. The `date` group, `doc_type` group, and `citations` group are also near-identical across composites.

**B) `cross_validation.enricher_pairings` repeated fields:**
Publication composite defines 34 paired fields across 4 enrichers. Most fields use the same validation method. The pattern `{ field: doi, method: exact }`, `{ field: title, method: fuzzy, threshold: 0.8 }`, `{ field: volume, method: exact }`, etc. is repeated for each enricher with minimal variation.

**C) `exclude_fields` lists are long and manually maintained:**
Publication composite lists 60 exclude_fields. These could be computed from the `preserve_all_sources` flag and a "common fields" definition.

### 1.2 DQ/Filter Hierarchical Config: 4-Level Merge

DQ rules resolve through 4 levels:
```
_defaults.yaml -> providers/{provider}.yaml -> entities/{provider}/{entity}.yaml -> pipeline dq_overrides
```

While the merge is correct, the intermediate `providers/{provider}.yaml` level is very thin:

| File | Lines | Unique Content |
|------|-------|----------------|
| quality/providers/chembl.yaml | 42 | 3 regex patterns + stricter threshold |
| quality/providers/pubchem.yaml | 24 | 1 threshold override |
| quality/providers/uniprot.yaml | 24 | 1 threshold override |
| quality/providers/crossref.yaml | 32 | 1 threshold override |
| quality/providers/openalex.yaml | 39 | 1 threshold + 1 field validation |
| quality/providers/pubmed.yaml | 47 | 1 threshold + 2 field validations |
| quality/providers/semanticscholar.yaml | 47 | 1 threshold + 2 field validations |

**7 files x ~35 avg lines = 245 lines for content that could be inlined into entity configs.**

Same pattern exists for filter providers (168 lines across 7 files with even less unique content).

### 1.3 Regular Pipeline Config Verbosity

The 22 regular pipeline configs contain:
- **Boilerplate comments** about DQ hierarchy (lines 17-23 in each) -- repeated ~15 times
- **`primary_keys`, `silver_table`, `gold_table`** that follow predictable conventions (`{provider}_{entity}`) -- 22 files x 3 fields = 66 redundant declarations
- **`partition_by: []`** (empty) in most configs -- inherited from _base.yaml but re-declared

### 1.4 Schema Configs: Bimodal Distribution

| Type | Files | Lines | Note |
|------|-------|-------|------|
| Empty/minimal (`column_groups: []`) | 14 | 14 | 1 line each |
| Publication schemas | 7 | 1,200+ | Detailed column definitions |
| Composite schemas | 3 | 864 | Column ordering |
| Other | 1 | 86 | Example file |

**14 files with `column_groups: []` could be eliminated if the loader defaults to empty.**

### 1.5 `_base.yaml`: Good but Has Dead Placeholders

The 113-line `_base.yaml` contains `<provider>`, `<version>`, `<entity>`, `<pipeline>` placeholders in metadata that are never substituted at runtime. These are documentation artifacts, not functional config.

---

## 2. CI Workflows (`.github/workflows/`)

### 2.1 Duplicated Setup Patterns

**Python setup (checkout + setup-python + install)** appears in 13 out of 17 workflows with minimal variation:

```yaml
# This 6-line block is copied 13 times:
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"
- run: pip install ... # varies
```

**Dependency installation uses 3 different approaches:**
1. `uv sync` (tests.yml, contract-tests.yml, port-contracts.yml, vacuum.yml)
2. `pip install .[dev]` (type-checking.yml, import-linter.yml)
3. `pip install build twine` (release.yml)

### 2.2 Duplicate Mermaid Validation

Both `docs.yml` (lines 16-56) and `validate-mermaid.yml` (lines 8-30) validate Mermaid diagrams with identical logic. One should be removed.

### 2.3 Architecture Testing Fragmentation

Architecture tests are spread across 4 workflows:
- `tests.yml` -- runs `tests/architecture/` in matrix
- `architecture.yml` -- dedicated metrics (only on `main`)
- `import-linter.yml` -- import boundary + architecture
- `port-contracts.yml` -- port protocol validation

### 2.4 Inconsistent Branch Triggers

| Workflow | Branches |
|----------|----------|
| tests.yml | main, master, develop |
| architecture.yml | main |
| type-checking.yml | main, master |
| import-linter.yml | main, master |
| port-contracts.yml | main, master, develop |

No documented rationale for why some workflows skip `develop`.

### 2.5 Cache Key Inconsistencies

At least 4 different cache key patterns for pytest:
- `pytest-fast-${{ runner.os }}-${{ hashFiles('tests/**/*.py') }}`
- `pytest-contracts-${{ runner.os }}-${{ hashFiles('tests/architecture/...') }}`
- `pytest-${{ runner.os }}-${{ hashFiles('**/pyproject.toml') }}`
- Various ad-hoc patterns

---

## 3. Root Config Files

### 3.1 pyproject.toml: Dependency Duplication

`[project.optional-dependencies]tests` (lines 61-85) and `[dependency-groups]dev` (lines 503-538) share ~60% of packages (pytest, pytest-cov, pytest-asyncio, hypothesis, vcrpy, etc.). Updating a version in one place without the other causes silent drift.

### 3.2 pyproject.toml: Redundant isort Config

Both `[tool.isort]` and `[tool.ruff.lint.isort]` are configured. The pre-commit hook runs both isort and ruff. Ruff's isort is sufficient.

### 3.3 pyproject.toml: 100 Lines of mypy Overrides

Lines 255-353 contain ~100 lines of mypy `[[tool.mypy.overrides]]` with overlapping module patterns. Some modules appear in multiple blocks.

### 3.4 Makefile: 16 Test Targets

| Target | Description | Overlap |
|--------|-------------|---------|
| test | Full suite | Base |
| test-serial | No parallel | Same as `test` minus `-n auto` |
| test-fast | Skip slow | Subset |
| test-quick | Quick check | Similar to test-fast |
| test-unit | Unit only | Subset |
| test-unit-fast | Fast unit | Subset of subset |
| test-smoke | Smoke tests | Subset |
| test-ci-local | CI locally | Nearly identical to `test` |
| ... | ... | ... |

`test-fast` vs `test-quick` and `test` vs `test-ci-local` create confusion.

### 3.5 .pre-commit-config.yaml: Redundant Scanners

Both `detect-secrets` and `gitleaks` run as pre-commit hooks for secret scanning. Both `isort` and `ruff` run for import sorting.

---

## 4. Simplification Strategy

### Phase 1: Low-Risk, High-Impact (no behavior change)

#### S1.1: Extract Shared Composite Column Groups

**Current**: Each composite duplicates `system`, `date`, `citations` column groups.
**Proposed**: Create `configs/schemas/composite/_shared_column_groups.yaml` with common groups. Reference from composite configs.

**Savings**: ~200 lines across 5 composites.

**Implementation**: Add support for `!include` or `$ref` in config_loader, OR move column_groups to a shared schema file referenced by the composite data_schema_file mechanism that already exists.

#### S1.2: Eliminate Empty Schema Files

**Current**: 14 files containing only `column_groups: []`.
**Proposed**: Make `column_groups: []` the default in config_loader when no schema file exists.

**Savings**: 14 files deleted.

**Implementation**: One-line change in `config_loader.py` -- check file existence before loading.

#### ~~S1.3: Remove Duplicate Mermaid Workflow~~ (RETRACTED)

After review: `docs.yml` validates Mermaid **diagram syntax** (renders `.mermaid` files), while `validate-mermaid.yml` checks for **vendored JS assets** (file existence). These are different tasks -- no duplication.

#### S1.4: Remove Redundant Pre-commit Hooks

**Current**: isort + ruff (both sort imports), detect-secrets + gitleaks (both scan secrets).
**Proposed**: Remove isort hook (ruff handles it), remove detect-secrets (gitleaks handles it).

**Savings**: ~15 lines, faster pre-commit runs.

#### S1.5: Remove `[tool.isort]` from pyproject.toml

**Current**: Both `[tool.isort]` and `[tool.ruff.lint.isort]` configured.
**Proposed**: Delete `[tool.isort]` section.

**Savings**: ~5 lines, eliminates config drift risk.

---

### Phase 2: Medium-Risk, High-Impact (config structure changes)

#### S2.1: Flatten DQ/Filter Provider Level

**Current**: 4-level DQ hierarchy (defaults -> provider -> entity -> pipeline overrides).
**Proposed**: 3-level hierarchy (defaults -> entity -> pipeline overrides). Inline the ~2-3 provider-specific values into entity configs.

**Savings**: 14 files deleted (7 quality + 7 filter provider files), ~400 lines.

**Risk**: Requires updating `_merge_dq_config()` and `_merge_filter_config()` in config_loader.

#### S2.2: Create Composite Action for CI Python Setup

**Current**: 13 workflows copy-paste checkout + python setup + install.
**Proposed**: Create `.github/actions/setup-python-env/action.yml` composite action.

**Savings**: ~150 lines across workflows, single source of truth for Python version.

#### S2.3: Consolidate CI Type-Checking Workflows

**Current**: `type-checking.yml` and `import-linter.yml` both run mypy.
**Proposed**: Merge into single `code-quality.yml` workflow.

**Savings**: ~100 lines, eliminates duplicate mypy runs.

#### S2.4: Standardize Pipeline Configs to Convention Style

**Current**: Mixed explicit/convention styles across ChEMBL configs.
**Proposed**: Migrate all to convention-minimal style (ADR-029).

**Savings**: ~200 lines across 14 ChEMBL configs (remove redundant path declarations, silver_table, gold_table).

#### S2.5: Deduplicate pyproject.toml Dependencies

**Current**: Test deps in both `[project.optional-dependencies]` and `[dependency-groups]`.
**Proposed**: Keep `[project.optional-dependencies]tests` as source of truth. Have `[dependency-groups]dev` include it via `{include-group = "tests"}`.

**Savings**: ~30 lines, eliminates version drift.

---

### Phase 3: Higher-Risk, Structural (requires code changes)

#### S3.1: Compute `exclude_fields` from Metadata

**Current**: Manually maintained lists of 60+ exclude_fields in composite configs.
**Proposed**: Auto-compute from `preserve_all_sources` flag + "common fields" definition. Only list explicit additions/removals.

**Savings**: ~200 lines across composite configs.

#### S3.2: Extract Cross-Validation Field Patterns

**Current**: Each enricher pairing repeats similar field lists.
**Proposed**: Define "standard CV fields" (`doi`, `title`, `volume`, `issue`, `page_first`, `page_last`, `publication_year`) as a template. Enrichers only declare additions/overrides.

**Savings**: ~100 lines in publication composite, proportional in others.

#### S3.3: Consolidate Makefile Test Targets

**Current**: 16 test targets with overlapping functionality.
**Proposed**: 5 curated targets: `test` (default), `test-ci` (strict), `test-serial` (debug), `test-smoke` (quick), `test-arch` (architecture). Use env vars for variants.

**Savings**: ~50 lines, clearer developer experience.

#### S3.4: Consolidate mypy Overrides

**Current**: ~100 lines of mypy overrides with overlapping modules.
**Proposed**: Merge blocks that share settings, remove duplicates.

**Savings**: ~40 lines.

---

## 5. Impact Summary

| Phase | Files Affected | Lines Saved | Risk | Effort |
|-------|----------------|-------------|------|--------|
| Phase 1 | ~20 | ~280 | Low | Small |
| Phase 2 | ~40 | ~880 | Medium | Medium |
| Phase 3 | ~15 | ~390 | Higher | Large |
| **Total** | **~75** | **~1,550** | - | - |

**Estimated overall reduction: ~16% of total config lines.**

---

## 6. Recommended Priority Order

1. **S1.4 + S1.5**: Remove redundant pre-commit hooks and isort config (5 min, zero risk)
2. **S1.3**: Remove duplicate Mermaid validation (5 min, zero risk)
3. **S1.2**: Eliminate empty schema files (small code change in loader)
4. **S2.5**: Deduplicate pyproject.toml dependencies (10 min)
5. **S2.4**: Standardize pipeline configs to convention style (systematic, low risk)
6. **S2.2**: Create CI composite action (medium effort, high payoff)
7. **S1.1**: Extract shared composite column groups (requires loader support)
8. **S2.1**: Flatten DQ/filter provider level (requires merge logic update)
9. **S2.3**: Consolidate CI workflows (medium effort)
10. **S3.1-S3.4**: Structural improvements (larger scope, plan separately)

---

## 7. What NOT to Change

- **`_base.yaml` structure**: The hierarchical inheritance model is sound
- **ADR-029 convention system**: Working correctly, should be extended not replaced
- **Composite pipeline semantics**: The merge/enricher/cross-validation logic is domain-specific and necessarily explicit
- **Source configs**: 7 files, each unique, no meaningful duplication
- **VCR cassettes**: Test fixtures, not configs -- leave as-is
- **Gold contracts**: Schema documentation, not operational config

---

## Appendix A: File Count by Directory

```
configs/
  pipelines/       27 files   3,566 lines
  schemas/         25 files   1,714 lines
  quality/          8 files     255 lines (providers only; entity files not in wc glob)
  filters/          8 files     168 lines (providers only; entity files not in wc glob)
  sources/          7 files     662 lines (includes _defaults)
  _schema/          2 files     ~500 lines (JSON)
  naming_exceptions  1 file     ~100 lines
  _base.yaml        1 file     113 lines

.github/workflows/ 17 files   1,782 lines

Root configs:       7 files   ~1,200 lines
```

## Appendix B: Largest Files (Top 10)

| File | Lines | Notes |
|------|-------|-------|
| configs/pipelines/composite/publication.yaml | 781 | Largest config file in project |
| configs/pipelines/composite/target.yaml | 495 | |
| configs/pipelines/composite/molecule.yaml | 411 | |
| configs/pipelines/composite/activity.yaml | 383 | |
| configs/schemas/composite/publication.yaml | 354 | Column ordering |
| configs/pipelines/composite/assay.yaml | 347 | |
| configs/schemas/composite/molecule.yaml | 259 | |
| configs/schemas/composite/assay.yaml | 251 | |
| .github/workflows/duplication-complexity.yml | 210 | |
| .github/workflows/tests.yml | 204 | |
