# Branch Consolidation Report

**Date**: 2026-03-14
**Branch**: `claude/review-branch-consolidation-ACHbr`
**Analyzed**: 29 non-main remote branches

---

## Summary

| Action | Count | Details |
|--------|-------|---------|
| Cherry-picked successfully | **3** | walrus opt, lint fix, REPO_ROOT fix |
| Skipped (already in main) | **1** | batch_size config fix |
| Stale (conflicts, deleted files) | **18** | codex/*, DI, mixin, FSM branches |
| Kept (best of duplicates) | **4** | ClockPort, DQ, reviews, scripts |
| Kept (user request) | **1** | claude/add-interactive-debugger |
| Needs manual re-impl | **1** | async metrics server |
| Needs manual review | **1** | main_20250312 backup |
| **Total for deletion** | **25** | See cleanup script |

---

## Cherry-picked Commits

### 1. Walrus optimization in serialization.py
- **Source**: `bolt-opt-flatten-arrow-1596384014476340969` (a555e06)
- **Change**: Eliminates redundant `v.as_py()` call in `flatten_arrow_table_for_export`
- **Impact**: ~1.8x speedup in Arrow→JSON serialization
- **Files**: `src/bioetl/domain/serialization.py`

### 2. Lint fix in tests
- **Source**: `perf-arrow-as-py-13400775707547248079` (65646e5)
- **Change**: Remove unused `tempfile` import, unnecessary `# noqa: A001`
- **Files**: `tests/unit/infrastructure/export/test_csv_exporter.py`, `tests/unit/infrastructure/storage/test_retention_dedup.py`

### 3. Setup script REPO_ROOT fix
- **Source**: `claude/configure-setup-script-ei3rR` (1c4f9b8)
- **Change**: Fix `REPO_ROOT` path (`../..` instead of `..`) + add root `setup.sh` entry point
- **Files**: `scripts/ops/setup_plugins.sh`, `setup.sh`

---

## Stale Branches Analysis

### Why so many branches are stale

All `codex/*` branches are based on an **ancient commit** (7730+ commits divergence from main).
This means they contain the entire main history plus 1 meaningful commit on top. Key structural
changes in main since these branches were created:

1. **`services_factory.py` deleted** — breaks all DI refactoring branches
2. **Composite runner mixins deleted** (`runner_stage_mixin.py`, `runner_merge_stage_mixin.py`, `runner_support_mixin.py`) — breaks getattr, FSM helper branches
3. **ChEMBL fetch mixins significantly refactored** — breaks type-safety branch (22 conflicts)
4. **Metrics service restructured** — breaks async metrics branch (5 conflicts)

### Duplicate Branch Groups

| Group | Branches | Best candidate |
|-------|----------|----------------|
| ClockPort (3) | add-clockport-*, implement-clockport-* | `implement-clockport-with-systemclock-and-fixedclock` |
| Review Reports (3) | generate-review-reports-*, jules/py-review-* | `feat/generate-review-reports-1938004674597881868` |
| SilverDQAnalyzer (2) | refactor-silverdqanalyzer-* | `refactor-silverdqanalyzer-into-components-bpi4lc` |
| Consolidate Scripts (2) | consolidate-project-scripts-* | `consolidate-project-scripts-IyUir` |

---

## Recommendations

### Immediate (run cleanup script)
```bash
./scripts/ops/cleanup_stale_branches.sh          # Dry-run
./scripts/ops/cleanup_stale_branches.sh --execute # Delete 25 branches
```

### Follow-up tasks
1. **Re-implement async metrics server** from `perf-async-metrics-server` branch idea
   - Convert `ensure_metrics_server_started()` sync→async
   - Convert `metrics_server_context()` to async context manager
   - Update CLI commands (run, run_all, run_composite)

2. **Re-implement ClockPort** from `codex/implement-clockport-with-systemclock-and-fixedclock`
   - Introduce `ClockPort` protocol in `domain/ports/`
   - Create `SystemClock` and `FixedClock` implementations
   - Inject into orchestration services

3. **Re-implement SilverDQAnalyzer decomposition** from `codex/refactor-silverdqanalyzer-into-components-bpi4lc`
   - Break monolithic analyzer into composable DQ components

4. **Evaluate review reports generator** from `feat/generate-review-reports-1938004674597881868`
   - AST-based AI review reports generator script

---

## Branches After Cleanup

After running the cleanup script, only these branches will remain:

| Branch | Status | Action needed |
|--------|--------|---------------|
| `claude/add-interactive-debugger` | Active | User decision |
| `codex/implement-clockport-with-systemclock-and-fixedclock` | Stale but valuable | Re-implement on fresh base |
| `feat/generate-review-reports-1938004674597881868` | Stale but valuable | Evaluate utility |
| `codex/refactor-silverdqanalyzer-into-components-bpi4lc` | Stale but valuable | Re-implement on fresh base |
| `claude/consolidate-project-scripts-IyUir` | Active | Review and merge |
| `perf-async-metrics-server-1814537927827611323` | Stale but valuable | Re-implement on fresh base |
| `main_20250312` | Backup | Manual review |
| `dependabot/*` (4 branches) | Automated | Merge or dismiss |
