# scripts/docs — Documentation Maintenance

Documentation lint, build, drift checks, and maintenance tooling.

## Unified Entry Point

```bash
python -m scripts.docs --help
python -m scripts.docs <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `check-links` | `check_doc_links.py` | Check documentation links, specs, and configs |
| `check-drift` | `check_doc_drift.py` | Check documentation drift (ports, classes, runtime mirrors, freshness) |
| `check-docstrings` | `check_docstring_coverage.py` | Check docstring coverage |
| `check-kpi` | `report_docs_kpi.py` | Report documentation KPI metrics |
| `build-matrix-dicts` | `generate_chembl_matrix_dictionaries.py` | Build inventory and dictionary artifacts for the canonical ChEMBL matrix workbook |
| `filter-matrix-rows` | `filter_chembl_matrix_rows.py` | Remove rows from the canonical ChEMBL matrix workbook by column value |
| `normalize-matrix-values` | `normalize_chembl_matrix_workbook.py` | Normalize controlled vocabulary values in the canonical ChEMBL matrix workbook |
| `sync-matrix-structural-policy` | `sync_chembl_matrix_structural_policy.py` | Reconcile workbook policy columns with the current structural Silver policy semantics |
| `fix-links-auto` | `fix_doc_links_auto.py` | Auto-fix broken documentation links |
| `fix-links-explicit` | `fix_doc_links_explicit.py` | Fix documentation links with explicit rules |
| `fix-link-warnings` | `fix_link_warnings.py` | Fix link warnings in specified files |
| `audit-sentence` | `sentence_doc_audit.py` | Sentence-level documentation audit |

## When to Use

| Command | When | Trigger |
|---------|------|---------|
| `check-links` | After editing docs; validates internal links, spec files, contracts, legacy path guardrails | CI gate (`docs.yml`, every PR) |
| `check-drift` | After renaming classes, moving modules, changing ports, or updating active runtime docs; detects doc/code desync, runtime mirror drift, and freshness conflicts | CI gate (`architecture.yml`) |
| `check-docstrings` | After adding new modules/classes/functions; enforces coverage thresholds (modules 100%, classes 95%, functions 90%) | CI gate (`architecture.yml`) |
| `check-kpi` | Weekly documentation health tracking; generates coverage, links, and drift metrics | Scheduled weekly (Monday 4:00 UTC) |
| `build-matrix-dicts` | After any workbook edit; refreshes inventory and dictionary artifacts for the canonical matrix | Manual, after workbook changes |
| `filter-matrix-rows` | When removing obsolete rows such as `not_mapped` fields from the canonical matrix | Manual, on-demand |
| `normalize-matrix-values` | After any workbook edit that touches controlled vocabularies; normalizes values in-place for the canonical matrix | Manual, after workbook changes |
| `sync-matrix-structural-policy` | After changing runtime structural Silver policy semantics; updates workbook policy columns from current `Type`/`Nullable`/`Required` contracts | Manual, after structural policy changes |
| `fix-links-auto` | After bulk renames or restructuring; auto-rewrites broken doc links | Manual, after refactoring |
| `fix-links-explicit` | When specific broken links need targeted fixes with explicit rules | Manual, on-demand |
| `fix-link-warnings` | After `check-links` reports warnings; fixes link format issues in specified files | Manual, on-demand |
| `audit-sentence` | Before release or documentation review; audits sentence structure and grammar | Manual, pre-release |

## Canonical Workbook

The single canonical ChEMBL workbook artifact is:

- [chembl_pipeline_silver_matrices_v12.xlsx](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/chembl_pipeline_silver_matrices_v12.xlsx)

Older `v2`-`v11` files are historical snapshots only and should not be edited.

## Canonical Workbook Update Workflow

1. Edit only [chembl_pipeline_silver_matrices_v12.xlsx](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/chembl_pipeline_silver_matrices_v12.xlsx).
2. If runtime structural Silver policy changed, sync the workbook policy columns first:

```bash
uv run python -m scripts.docs sync-matrix-structural-policy
```

3. Normalize controlled vocabularies in place:

```bash
uv run python -m scripts.docs normalize-matrix-values
```

4. Rebuild dictionary artifacts from the canonical workbook:

```bash
uv run python -m scripts.docs build-matrix-dicts
```

5. If the change intentionally removes obsolete rows, apply the row filter in place:

```bash
uv run python -m scripts.docs filter-matrix-rows
```

6. Review the regenerated YAML artifacts in [docs/reports/dictionaries](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/dictionaries).

## Other Files

| File | Description |
|------|-------------|
| `build_docs_site.sh` | Build MkDocs documentation site |
