# Plan: Consolidation of Project Scripts

**Date:** 2026-03-11
**Status:** PROPOSAL
**Scope:** `scripts/` directory restructuring

---

## 1. Current State Analysis

### 1.1 Metrics

| Location | Count | Role |
|----------|-------|------|
| `scripts/*.py` | 39 | Root-level (38 wrappers + `run.py`) |
| `scripts/*.sh` | 14 | Root-level shell wrappers |
| `scripts/*.bat` | 3 | Root-level batch wrappers |
| Canonical subdirectories | 102 | Actual implementations |
| `scripts/archive/` | ~20 | Archived/deprecated |
| **Total** | ~178 | |

### 1.2 Canonical Groups (current)

| Group | Scripts | Purpose |
|-------|---------|---------|
| `qa/` | 8 | Quality checks, complexity, naming |
| `docs/` | 9 | Doc build, drift, links, coverage |
| `schema/` | 8 | Config validation, contract generation |
| `data/` | 9 | Delta integrity, VCR, checksums |
| `repo/` | 5 | Inventory, cleanliness, version |
| `ops/` | 12 | Deploy, PRs, skills, salt |
| `diagnostics/` | 7 | Debug, AST, cleanup |
| `ci/` | 7 | Pytest resilient, quality gate, e2e |
| `dev/` | 13 | Setup, test runners, MCP config |
| `diagrams/` | 22 | Lint, render, quality gates |
| `migrations/` | 2 | One-off data migrations |

### 1.3 Key Problems

1. **56 root wrappers** exist solely for backward compatibility, adding noise
2. **CI workflows reference root wrappers** (not canonical paths) — migration needed
3. **No unified entry point per domain** — e.g., 8 separate QA scripts require 8 separate invocations
4. **diagrams/** has 22 scripts without a single orchestrator (aside from `run_diagram_checks.sh`)
5. **Functional overlap** — scripts like `check_quality_exemptions.py`, `check_c901_baseline.py`, `check_naming_package_consistency.py`, `lint_terminology.py` all validate code quality but lack a unified runner

---

## 2. Consolidation Strategy

### Principle: One Domain = One Entry Point + Subcommands

Each canonical group gets a **CLI entry point** (`__main__.py` or `cli.py`) using `click` or `argparse` subcommands, while individual scripts remain as importable modules.

```
scripts/<group>/
    __init__.py          # package marker
    cli.py               # unified entry point with subcommands
    <module_1>.py        # individual logic (importable)
    <module_2>.py        # individual logic (importable)
```

**Invocation:**
```bash
# Before (8 separate calls):
python scripts/qa/check_c901_baseline.py
python scripts/qa/check_naming_package_consistency.py
python scripts/qa/check_quality_exemptions.py
...

# After (single entry point):
python -m scripts.qa all                    # run all QA checks
python -m scripts.qa c901                   # run specific check
python -m scripts.qa naming                 # run specific check
python scripts/run.py exec qa cli -- all    # via launcher
```

---

## 3. Group-by-Group Consolidation Plan

### 3.1 `scripts/qa/` → Code Quality Validation

**Entry point:** `scripts/qa/cli.py`

| Subcommand | Source Script | What It Does |
|------------|---------------|--------------|
| `c901` | `check_c901_baseline.py` | Cognitive complexity baseline |
| `naming` | `check_naming_package_consistency.py` | NAME-001 rules |
| `exemptions` | `check_quality_exemptions.py` | Exemption metadata |
| `terminology` | `lint_terminology.py` | Glossary enforcement |
| `hotspots` | `calibrate_hotspot_budgets.py` | Complexity budgets |
| `arch-map` | `generate_architecture_dependency_map.py` | Dependency visualization |
| `degradation` | `generate_hotspot_degradation_report.py` | Complexity trends |
| `naming-audit` | `naming_audit.py` | Full naming audit |
| `all` | — | Run all checks, aggregate exit codes |

**Impact:** 8 scripts → 1 entry point + 8 modules

---

### 3.2 `scripts/docs/` → Documentation Validation

**Entry point:** `scripts/docs/cli.py`

| Subcommand | Source Script | What It Does |
|------------|---------------|--------------|
| `drift` | `check_doc_drift.py` | Code ↔ docs drift |
| `links` | `check_doc_links.py` | Hyperlink validation |
| `coverage` | `check_docstring_coverage.py` | Docstring completeness |
| `kpi` | `report_docs_kpi.py` | Documentation KPIs |
| `fix-links` | `fix_doc_links_auto.py` | Auto-fix broken links |
| `build` | `build_docs_site.sh` | Build docs site |
| `audit` | `sentence_doc_audit.py` | Grammar/style audit |
| `all-checks` | — | drift + links + coverage |

**Impact:** 9 scripts → 1 entry point + 9 modules

---

### 3.3 `scripts/schema/` → Schema & Config Governance

**Entry point:** `scripts/schema/cli.py`

| Subcommand | Source Script | What It Does |
|------------|---------------|--------------|
| `validate` | `validate_pipeline_configs.py` | Pipeline config validation |
| `invariants` | `check_config_invariants.py` | Config integrity |
| `gaps` | `config_gap_analysis.py` | Missing config sections |
| `lint-paths` | `lint_config_paths.py` | Config path validation |
| `contracts` | `generate_contracts.py` | Gold layer contracts |
| `pipeline-schema` | `generate_pipeline_schema.py` | Pipeline schema artifacts |
| `schema-artifacts` | `generate_schema_artifacts.py` | General schema generation |
| `pub-types` | `generate_publication_type_classification_artifacts.py` | Publication type schemas |
| `all-checks` | — | validate + invariants + gaps + lint-paths |
| `all-generate` | — | contracts + pipeline-schema + schema-artifacts |

**Impact:** 8 scripts → 1 entry point + 8 modules

---

### 3.4 `scripts/data/` → Data Integrity

**Entry point:** `scripts/data/cli.py`

| Subcommand | Source Script | What It Does |
|------------|---------------|--------------|
| `delta` | `check_delta_integrity.py` | Delta Lake integrity |
| `vcr-root` | `check_root_vcr_cassettes.py` | VCR cassette location |
| `vcr-naming` | `check_vcr_filename_policy.py` | VCR naming conventions |
| `checksums` | `verify_checksums.py` | Checksum verification |
| `validate-dir` | `validate_data_dir.py` | Directory structure |
| `dq-baseline` | `dq_baseline_update.py` | DQ metric baselines |
| `vacuum` | `vacuum_delta.py` | Delta Lake maintenance |
| `all-checks` | — | delta + vcr-root + vcr-naming + checksums + validate-dir |

**Impact:** 9 scripts → 1 entry point + 9 modules

---

### 3.5 `scripts/repo/` → Repository Hygiene

**Entry point:** `scripts/repo/cli.py`

| Subcommand | Source Script | What It Does |
|------------|---------------|--------------|
| `cleanliness` | `audit_root_cleanliness.py` | Root dir hygiene |
| `inventory` | `check_scripts_inventory.py` | Script inventory drift |
| `catalog` | `check_scripts_catalog.py` | Catalog governance |
| `versions` | `check_version_consistency.py` | Version string consistency |
| `preflight` | `preflight_cleanup.sh` | Pre-commit cleanup |
| `all-checks` | — | cleanliness + inventory + catalog + versions |

**Impact:** 5 scripts → 1 entry point + 5 modules

---

### 3.6 `scripts/diagrams/` → Diagram Pipeline

**Entry point:** `scripts/diagrams/cli.py`

This is the highest-value consolidation — 22 scripts with no unified orchestration.

| Subcommand Group | Scripts | What They Do |
|------------------|---------|--------------|
| `lint` | `lint_diagrams.py`, `summarize_diagram_lint.py` | Lint + reporting |
| `check` | `check_diagram_quality_gates.py`, `check_diagram_artifacts.py`, `check_diagram_visual_smoke.py`, `check_svg_text_visibility.py`, `check_pdf_image_bounds.py`, `check_class_method_render_integrity.py` | Quality validation |
| `fix` | `fix_mermaid_operators.py`, `prune_orphan_nodes.py`, `strip_svg_foreign_object.py`, `inject_svg_styles.py`, `add_svg_text_fallback.py` | Auto-fixes |
| `generate` | `generate_with_descriptions_pdf.py`, `generate_with_descriptions_docx.py` | Output generation |
| `report` | `report_diagram_padding.py`, `enforce_diagram_quality_budget.py` | Metrics & budgets |
| `all-checks` | — | lint + all check subcommands |
| `nightly` | `run_diagram_nightly_suite.py` | Nightly orchestration |

**Impact:** 22 scripts → 1 entry point + 22 modules (6 logical groups)

---

### 3.7 `scripts/ops/` → Operations

**Entry point:** `scripts/ops/cli.py`

| Subcommand | Source Script |
|------------|---------------|
| `deploy` | `deploy-bioetl.sh` |
| `skills-layout` | `check_ai_skills_layout.sh` |
| `skills-mirror` | `check_skills_mirror.sh` |
| `skills-setup` | `setup_skills.sh` |
| `plugins` | `setup_plugins.sh` |
| `mcp` | `check_mcp.sh` |
| `salt-rotate` | `salt_rotate.py` |
| `grafana-fix` | `fix_grafana_dashboards.py` |
| `close-prs` | `close_superseded_prs.sh` (merge wave2/wave3) |
| `stale-branches` | `delete-stale-branches.sh` |

**Impact:** 12 scripts → 1 entry point + 10 modules (merge PR closers)

---

### 3.8 `scripts/ci/` → CI Orchestration

**Entry point:** `scripts/ci/cli.py`

| Subcommand | Source Script |
|------------|---------------|
| `test` | `run_pytest_resilient.py` |
| `gate` | `quality_integral_gate.py` |
| `e2e-skip` | `check_e2e_matrix_skip_rate.py` |
| `e2e-stability` | `check_e2e_rerun_stability.py` |
| `debt-report` | `report_quality_debt_weekly.py` |

**Impact:** 7 scripts → 1 entry point + 5 modules (exclude PS1 duplicates)

---

## 4. Root Wrapper Elimination Plan

### Phase 1: Migrate CI References (LOW RISK)

Update `.github/workflows/*.yml` and `Makefile` to use canonical paths instead of root wrappers.

**Before:**
```yaml
run: python scripts/check_c901_baseline.py
```

**After:**
```yaml
run: python scripts/qa/check_c901_baseline.py
# or:
run: python -m scripts.qa c901
```

**Scope:** ~30 references in workflows + ~25 in Makefile

### Phase 2: Deprecation Notices

Add `warnings.warn("Use scripts/qa/cli.py instead", DeprecationWarning)` to root wrappers.

### Phase 3: Remove Root Wrappers

After confirming no external consumers, delete 51 root wrapper files.

**Timeline:**
- Phase 1: immediate (no user impact)
- Phase 2: 1 release cycle
- Phase 3: next major version

---

## 5. Enhanced `run.py` Launcher

Extend `run.py` to support the new CLI entry points:

```bash
# Current (still works):
python scripts/run.py exec qa check_c901_baseline

# New (unified):
python scripts/run.py exec qa -- c901
python scripts/run.py exec qa -- all
python scripts/run.py exec docs -- all-checks
python scripts/run.py exec diagrams -- lint
```

---

## 6. Cross-Domain Composite Commands

Create top-level composite commands in `run.py` for common workflows:

```bash
python scripts/run.py preflight     # qa/all + docs/all-checks + schema/all-checks + repo/all-checks
python scripts/run.py validate      # schema/validate + data/all-checks + config invariants
python scripts/run.py full-audit    # all groups, all checks
```

This replaces the need to remember which groups contain which checks.

---

## 7. Implementation Priority

| Priority | Group | Reason | Effort |
|----------|-------|--------|--------|
| **P0** | `qa/` | Most fragmented quality checks, highest CI usage | M |
| **P0** | `diagrams/` | 22 scripts, no unified orchestration | L |
| **P1** | `docs/` | Frequent manual invocation | M |
| **P1** | `schema/` | Check + generate duality | M |
| **P2** | `data/` | Already well-organized | S |
| **P2** | `repo/` | Small group, low churn | S |
| **P3** | `ops/` | Mixed bash/python, operational | M |
| **P3** | `ci/` | Already called directly by workflows | S |

**Effort:** S = 1-2h, M = 2-4h, L = 4-8h

---

## 8. Migration Safety

### 8.1 Backward Compatibility

- Root wrappers remain functional until Phase 3
- `run.py exec <group> <script>` continues to work (individual scripts preserved)
- New `cli.py` entry points are additive

### 8.2 CI Impact

All workflow references to root wrappers must be updated in Phase 1 **before** Phase 3. Tracked via:
- `scripts/check_scripts_inventory.py` (existing inventory tool)
- `scripts/check_scripts_catalog.py` (existing catalog validation)

### 8.3 Testing

Each `cli.py` entry point gets a smoke test in `tests/scripts/`:
```python
def test_qa_cli_all(subprocess_run):
    result = subprocess_run(["python", "-m", "scripts.qa", "all", "--dry-run"])
    assert result.returncode == 0
```

---

## 9. Target Directory Structure

```
scripts/
    run.py                          # Enhanced launcher with composite commands
    catalog.yaml                    # Updated catalog
    baselines/                      # Baseline data files
    qa/
        __init__.py
        cli.py                      # `python -m scripts.qa [subcommand]`
        check_c901_baseline.py
        check_naming_package_consistency.py
        check_quality_exemptions.py
        calibrate_hotspot_budgets.py
        generate_architecture_dependency_map.py
        generate_hotspot_degradation_report.py
        lint_terminology.py
        naming_audit.py
    docs/
        __init__.py
        cli.py                      # `python -m scripts.docs [subcommand]`
        build_docs_site.sh
        check_doc_drift.py
        check_doc_links.py
        check_docstring_coverage.py
        fix_doc_links_auto.py
        report_docs_kpi.py
        ...
    schema/
        __init__.py
        cli.py
        ...
    data/
        __init__.py
        cli.py
        ...
    diagrams/
        __init__.py
        cli.py                      # Biggest win: 22 scripts → 6 subcommand groups
        lint_diagrams.py
        ...
    repo/
        __init__.py
        cli.py
        ...
    ops/
        __init__.py
        cli.py
        ...
    ci/
        __init__.py
        cli.py
        ...
    dev/
        ...
    diagnostics/
        ...
    migrations/
        active/
        oneoff/
    archive/                        # Unchanged
    compat/                         # Deprecated root wrappers (Phase 2 → Phase 3 delete)
```

---

## 10. Summary

| Metric | Before | After |
|--------|--------|-------|
| Root wrapper scripts | 51 | 0 (Phase 3) |
| Entry points per domain | 8-22 scripts | 1 CLI per domain |
| Command to run all QA checks | 8 invocations | `python -m scripts.qa all` |
| Command for full preflight | manual assembly | `python scripts/run.py preflight` |
| Total script files | ~178 | ~110 (modules preserved, wrappers removed) |
| Discoverability | `run.py list` | `run.py list` + `<group> --help` |
