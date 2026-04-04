# scripts/docs — Documentation Maintenance

Documentation lint, build, drift checks, and maintenance tooling.

## Unified Entry Point

```bash
python -m scripts.docs --help
python -m scripts.docs <command> [args...]
```

## Commands

| Command                               | Script                                                       | Description                                                                           |
| ------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `check-links`                         | `scripts/docs/check_doc_links.py`                            | Check documentation links, specs, configs, and mkdocs nav classification              |
| `check-drift`                         | `scripts/docs/check_doc_drift.py`                            | Check documentation drift (ports, classes, runtime mirrors, freshness)                |
| `check-docstrings`                    | `scripts/docs/check_docstring_coverage.py`                   | Check docstring coverage                                                              |
| `check-kpi`                           | `scripts/docs/report_docs_kpi.py`                            | Report documentation KPI metrics                                                      |
| `export-matrix-structural-contract`   | `scripts/docs/export_chembl_matrix_structural_contract.py`   | Export the canonical runtime structural contract for ChEMBL workbook sync             |
| `build-matrix-dicts`                  | `scripts/docs/generate_chembl_matrix_dictionaries.py`        | Build inventory and dictionary artifacts for the canonical ChEMBL matrix workbook     |
| `enrich-matrix-normalization-details` | `scripts/docs/enrich_chembl_matrix_normalization_details.py` | Populate exact per-row normalization details in the canonical ChEMBL matrix workbook  |
| `filter-matrix-rows`                  | `scripts/docs/filter_chembl_matrix_rows.py`                  | Remove rows from the canonical ChEMBL matrix workbook by column value                 |
| `normalize-matrix-values`             | `scripts/docs/normalize_chembl_matrix_workbook.py`           | Normalize controlled vocabulary values in the canonical ChEMBL matrix workbook        |
| `sync-matrix-structural-policy`       | `scripts/docs/sync_chembl_matrix_structural_policy.py`       | Reconcile workbook policy columns with the current structural Silver policy semantics |
| `fix-links-auto`                      | `scripts/docs/fix_doc_links_auto.py`                         | Auto-fix broken documentation links                                                   |
| `fix-links-explicit`                  | `scripts/docs/fix_doc_links_explicit.py`                     | Fix documentation links with explicit rules                                           |
| `fix-link-warnings`                   | `scripts/docs/fix_link_warnings.py`                          | Fix link warnings in specified files                                                  |
| `audit-sentence`                      | `scripts/docs/sentence_doc_audit.py`                         | Sentence-level documentation audit                                                    |

## When to Use

| Command                               | When                                                                                                                                                                                                     | Trigger                                                                    |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `check-links`                         | After editing docs; validates internal links, spec files, contracts, legacy path guardrails, and ensures each local skill mirror page is explicitly classified in `mkdocs.yml` via `nav` or `not_in_nav` | CI gate (`docs.yml`, every PR)                                             |
| `check-drift`                         | After renaming classes, moving modules, changing ports, or updating active runtime docs; detects doc/code desync, runtime mirror drift, and freshness conflicts                                          | CI gate (`architecture.yml`)                                               |
| `check-docstrings`                    | After adding new modules/classes/functions; enforces coverage thresholds (modules 100%, classes 95%, functions 90%)                                                                                      | CI gate (`architecture.yml`)                                               |
| `check-kpi`                           | Weekly documentation health tracking; generates coverage, links, and drift metrics                                                                                                                       | Scheduled weekly (Monday 4:00 UTC)                                         |
| `export-matrix-structural-contract`   | After changing runtime structural policy, optionality precedence, explicit `field_policy` overlays, or schema-derived contract semantics; refreshes the canonical export consumed by workbook sync       | Manual, after structural contract changes; CI freshness gate via `--check` |
| `build-matrix-dicts`                  | After any workbook edit; refreshes inventory and dictionary artifacts for the canonical matrix                                                                                                           | Manual, after workbook changes                                             |
| `enrich-matrix-normalization-details` | After workbook edits that change normalization semantics; repopulates exact row-level normalization detail text for the canonical matrix                                                                 | Manual, after workbook changes                                             |
| `filter-matrix-rows`                  | When removing obsolete rows such as `not_mapped` fields from the canonical matrix                                                                                                                        | Manual, on-demand                                                          |
| `normalize-matrix-values`             | After any workbook edit that touches controlled vocabularies; normalizes values in-place for the canonical matrix                                                                                        | Manual, after workbook changes                                             |
| `sync-matrix-structural-policy`       | After changing runtime structural Silver policy semantics or workbook-relevant `field_policy` overlays; updates workbook policy columns from the canonical runtime contract export                       | Manual, after structural policy changes; CI freshness gate via `--check`   |
| `fix-links-auto`                      | After bulk renames or restructuring; auto-rewrites broken doc links                                                                                                                                      | Manual, after refactoring                                                  |
| `fix-links-explicit`                  | When specific broken links need targeted fixes with explicit rules                                                                                                                                       | Manual, on-demand                                                          |
| `fix-link-warnings`                   | After `check-links` reports warnings; fixes link format issues in specified files                                                                                                                        | Manual, on-demand                                                          |
| `audit-sentence`                      | Before release or documentation review; audits sentence structure and grammar                                                                                                                            | Manual, pre-release                                                        |

## Canonical Workbook

The single canonical ChEMBL workbook artifact is:

- [chembl_pipeline_silver_matrices_v12.xlsx](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/chembl_pipeline_silver_matrices_v12.xlsx)

Older `v2`-`v11` files are historical snapshots only and should not be edited.

## Canonical Workbook Update Workflow

1. Edit only [chembl_pipeline_silver_matrices_v12.xlsx](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/chembl_pipeline_silver_matrices_v12.xlsx).
1. Export the canonical runtime structural contract:

```bash
uv run python -m scripts.docs export-matrix-structural-contract
uv run python -m scripts.docs export-matrix-structural-contract --check
```

3. If runtime structural Silver policy changed, sync the workbook policy columns from that export:

```bash
uv run python -m scripts.docs sync-matrix-structural-policy
uv run python -m scripts.docs sync-matrix-structural-policy --check
```

4. Normalize controlled vocabularies in place:

```bash
uv run python -m scripts.docs normalize-matrix-values
```

5. Rebuild dictionary artifacts from the canonical workbook:

```bash
uv run python -m scripts.docs build-matrix-dicts
```

6. If the change intentionally removes obsolete rows, apply the row filter in place:

```bash
uv run python -m scripts.docs filter-matrix-rows
```

7. Review the runtime contract export and regenerated YAML artifacts:

- [docs/reports/generated/chembl_matrix_structural_contract_v1.json](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/chembl_matrix_structural_contract_v1.json)
- [docs/reports/dictionaries](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/dictionaries)

The exported contract now includes runtime-resolved `field_policy` overlays such as:

- `empty_as_missing`
- `coercion_policy`
- `boolean_true_values`
- `boolean_false_values`

## Other Files

| File                                                | Description                                                                              |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `scripts/docs/chembl_matrix_structural_contract.py` | Shared runtime export helper used by the ChEMBL matrix structural contract/sync workflow |
| `scripts/docs/build_docs_site.sh`                   | Build MkDocs documentation site                                                          |
