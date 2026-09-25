______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-09-24'

______________________________________________________________________

# Bounded Pipeline Smoke (`--limit 100`)

## Trigger

- Use this procedure to launch every registered entity pipeline, then every
  composite pack, with a bounded record cap.
- Use it after a runtime/schema/config change that can break extract, transform,
  Gold write, DQ, or run-report persistence.
- Do **not** use this as a full rebuild, backfill, or exact-replay drill.

## Impact

- Priority: P2.
- Concurrent `bioetl run` against the same data root will fail lock acquisition
  (exit `84`). These smokes **must** be sequential.
- `--limit 100` is a fetch cap, not a Gold-row guarantee. Derived pipelines
  (subcellular fraction, publication terms, target protein classification)
  may scan more upstream records than they emit.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010). Do **not** start
  `docker-compose.monitoring.yml` unless an operator explicitly requested
  dashboard work.
- Mixed Windows + WSL checkout: use
  `.\.venv-win\Scripts\python.exe` on Windows, or
  `"${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python"` on WSL.
- `.env` is present and readable. Do not create, edit, rename, move, or delete
  any `.env` file as part of this runbook.
- Confirm the catalog matches the live registry:

  ```powershell
  .\.venv-win\Scripts\python.exe -m bioetl config list-pipelines
  ```

- Required input CSVs exist under `data/input/` for pipelines whose
  `filters.input_filter.enabled` is `true`. Live checkout files:

  | File | Used by |
  | --- | --- |
  | `data/input/cell.csv` | `chembl_cell_line` |
  | `data/input/molecule.csv` | `chembl_compound_record` |
  | `data/input/pubchem_smiles.csv` | `pubchem_compound` |
  | `data/input/target_component.csv` | `chembl_target_component` |
  | `data/input/publication.csv` | `chembl_publication_term` |
  | `data/input/pubmed.csv` | `pubmed_publication` |
  | `data/input/dois.csv` | `crossref_publication`, `openalex_publication`, `semanticscholar_publication` |
  | `data/input/protein.csv` | `uniprot_protein` |
  | `data/input/target.csv` | `uniprot_idmapping` |

- No stale lock. If lock acquisition fails, follow
  [Stale Lock](stale-lock.md) before retrying.

## Procedure

Follow the canonical smoke flags, then execute one pipeline or composite at a
time in the wave order below. Stop on the first non-zero exit, classify it,
fix, and resume from the failed name.

## Canonical smoke flags

Entity pipeline:

```powershell
.\.venv-win\Scripts\python.exe -m bioetl run `
  --pipeline <NAME> `
  --limit 100 `
  --required-persistence-profile degraded_observable `
  --no-health-server `
  --no-ensure-observability-backend
```

Composite pack (`--limit` is **not** a composite flag; use `--seed-limit`):

```powershell
.\.venv-win\Scripts\python.exe -m bioetl run-composite `
  --composite <ENTITY> `
  --seed-limit 100 `
  --required-persistence-profile degraded_observable `
  --no-health-server `
  --no-ensure-observability-backend
```

Why these flags:

- `--limit 100` / `--seed-limit 100` — bounded live smoke, not a full ingest.
- `--required-persistence-profile degraded_observable` — local diagnostic
  opt-down that stays observable without claiming the `replay_ready` evidence
  floor. Required for both `bioetl run` and `bioetl run-composite`: default
  settings stay `replay_ready`, and composite execution is outside the
  strict exact-replay boundary (`replay_ready` / `forensic_grade` fail-close).
  Do **not** combine with `--exact-replay`.
- `--no-health-server` — sequential smokes must not fight over `:8000`.
- `--no-ensure-observability-backend` — keep the default-off Ops HTTP backend
  off unless Grafana ID panels are in scope.
- `composite publication` without `BIOETL_SEMANTICSCHOLAR_API_KEY`: skip the
  optional Semantic Scholar enricher (`--enrich-only crossref,openalex,pubmed`).
  Unauthenticated title-fallback search hits HTTP 429 with multi-minute backoff
  per missing DOI and can exceed the 7200s enricher timeout. Config already
  marks this enricher `required: false` (high rate limits, ok to skip).

Equivalent bash:

```bash
python -m bioetl run --pipeline <NAME> --limit 100 \
  --required-persistence-profile degraded_observable \
  --no-health-server --no-ensure-observability-backend

python -m bioetl run-composite --composite <ENTITY> --seed-limit 100 \
  --required-persistence-profile degraded_observable \
  --no-health-server --no-ensure-observability-backend
```

Provider-family shortcut (ChEMBL only; still sequential):

```powershell
.\.venv-win\Scripts\python.exe -m bioetl run-all --source chembl --limit 100 --list-only
.\.venv-win\Scripts\python.exe -m bioetl run-all --source chembl --limit 100 --no-health-server
```

`run-all` does not cover CrossRef, OpenAlex, PubMed, PubChem, Semantic Scholar,
or UniProt in one invocation. Use the per-pipeline table below for a full
catalog smoke.

## Execution order

Run **one** command at a time. Stop on the first non-zero exit, classify, fix,
then resume from the failed name (do not restart already-green pipelines unless
the fix invalidates their Gold).

### Wave A — small / independent ChEMBL

| # | Pipeline | Notes |
| --- | --- | --- |
| 1 | `chembl_protein_class` | Hierarchy; no input CSV. Prerequisite for wave C TPC. |
| 2 | `chembl_tissue` | API scan. |
| 3 | `chembl_cell_line` | Input filter: `data/input/cell.csv`. |
| 4 | `chembl_target` | Prerequisite for TPC and UniProt mapping. |
| 5 | `chembl_molecule` | Prerequisite for compound_record / PubChem. |
| 6 | `chembl_publication` | Seed for composite publication and term/similarity. |

### Wave B — core ChEMBL entities

| # | Pipeline | Notes |
| --- | --- | --- |
| 7 | `chembl_assay` | API scan. |
| 8 | `chembl_activity` | Curated `extraction_params` (IC50/Ki, nM). |
| 9 | `chembl_assay_parameters` | Nested on assays; `--limit` scales upstream. |
| 10 | `chembl_compound_record` | Input filter: `data/input/molecule.csv`. |
| 11 | `chembl_target_component` | Input filter: `data/input/target_component.csv`. Prerequisite for TPC. |

### Wave C — derived ChEMBL

| # | Pipeline | Notes |
| --- | --- | --- |
| 12 | `chembl_publication_similarity` | API scan from documents. |
| 13 | `chembl_publication_term` | Input filter: `data/input/publication.csv`. `/document_term` is retired; terms come from publication records. `--limit N` caps the CSV ID window to N publications (not `N * 50`) so the 180s derived-scan I/O budget is not exhausted when MeSH/keywords are absent. |
| 14 | `chembl_subcellular_fraction` | Derived from assays; sparse. Upstream scan uses `ASSAY_LIMIT_MULTIPLIER=200`, capped at 50_000 source rows. A `--limit` window that hits that cap returns the unique fractions found and does not raise `derived_scan_budget_exceeded`. Hang timeout is per upstream `anext`, not a 180s sum across pages. |
| 15 | `chembl_target_protein_classification` | Local Gold snapshots of `chembl_target`, `chembl_target_component`, `chembl_protein_class`. Fail-closed if those snapshots are missing. |

### Wave D — enrichers (standalone CSV, not composite)

| # | Pipeline | Notes |
| --- | --- | --- |
| 16 | `pubmed_publication` | `data/input/pubmed.csv` (`pubmed_id` → `pmid`). |
| 17 | `crossref_publication` | `data/input/dois.csv`. |
| 18 | `openalex_publication` | `data/input/dois.csv`. |
| 19 | `semanticscholar_publication` | `data/input/dois.csv`. Tight provider QPS; expect longer wall time. |
| 20 | `pubchem_compound` | `data/input/pubchem_smiles.csv` (`canonical_smiles` → `smiles`). |
| 21 | `uniprot_protein` | `data/input/protein.csv`. |
| 22 | `uniprot_idmapping` | Input filter: `data/input/target.csv` (`target_chembl_id` → `target_id`). `--limit 100` caps mapped IDs. Prefer after `chembl_target`. |

### Wave E — composite packs

CLI `--composite` takes the **entity** token, not the `composite_` registry name.

| # | `--composite` | Seed | Optional enrichers / dependencies |
| --- | --- | --- | --- |
| 23 | `publication` | `chembl_publication` | CrossRef, OpenAlex, PubMed, Semantic Scholar |
| 24 | `activity` | `chembl_activity` | compound_record and related optional enrichers |
| 25 | `assay` | `chembl_assay` | cell_line, tissue (optional) |
| 26 | `molecule` | `chembl_molecule` | PubChem (optional) |
| 27 | `target` | `chembl_target` | target_component, protein_class, UniProt (optional) |

Do not pass `--pipeline composite_publication` to `bioetl run`. Composite
entity YAML under `configs/entities/composite/` is the merge contract, not a
standalone `bioetl run` target.

## Per-pipeline commands

Replace `$py` with `.\.venv-win\Scripts\python.exe` on Windows.

```powershell
$py = ".\.venv-win\Scripts\python.exe"
$common = @(
  "--limit", "100",
  "--required-persistence-profile", "degraded_observable",
  "--no-health-server",
  "--no-ensure-observability-backend"
)

# Wave A
& $py -m bioetl run --pipeline chembl_protein_class @common
& $py -m bioetl run --pipeline chembl_tissue @common
& $py -m bioetl run --pipeline chembl_cell_line @common
& $py -m bioetl run --pipeline chembl_target @common
& $py -m bioetl run --pipeline chembl_molecule @common
& $py -m bioetl run --pipeline chembl_publication @common

# Wave B
& $py -m bioetl run --pipeline chembl_assay @common
& $py -m bioetl run --pipeline chembl_activity @common
& $py -m bioetl run --pipeline chembl_assay_parameters @common
& $py -m bioetl run --pipeline chembl_compound_record @common
& $py -m bioetl run --pipeline chembl_target_component @common

# Wave C
& $py -m bioetl run --pipeline chembl_publication_similarity @common
& $py -m bioetl run --pipeline chembl_publication_term @common
& $py -m bioetl run --pipeline chembl_subcellular_fraction @common
& $py -m bioetl run --pipeline chembl_target_protein_classification @common

# Wave D
& $py -m bioetl run --pipeline pubmed_publication @common
& $py -m bioetl run --pipeline crossref_publication @common
& $py -m bioetl run --pipeline openalex_publication @common
& $py -m bioetl run --pipeline semanticscholar_publication @common
& $py -m bioetl run --pipeline pubchem_compound @common
& $py -m bioetl run --pipeline uniprot_protein @common
& $py -m bioetl run --pipeline uniprot_idmapping @common

# Wave E
$ccommon = @(
  "--seed-limit", "100",
  "--required-persistence-profile", "degraded_observable",
  "--no-health-server",
  "--no-ensure-observability-backend"
)
& $py -m bioetl run-composite --composite publication @ccommon --enrich-only "crossref,openalex,pubmed"
& $py -m bioetl run-composite --composite activity @ccommon
& $py -m bioetl run-composite --composite assay @ccommon
& $py -m bioetl run-composite --composite molecule @ccommon
& $py -m bioetl run-composite --composite target @ccommon
```

## Failure classification

| Exit | Meaning | Next |
| ---: | --- | --- |
| 0 | Success | Verify report + manifest, continue to the next name. |
| 82 | Pipeline execution error | Capture `run_id`, logs, then [Pipeline Failure Recovery](pipeline-failure-recovery.md). |
| 83 | DQ threshold | [Pipeline Failure - DQ](pipeline-failure-dq.md). |
| 84 | Lock | [Stale Lock](stale-lock.md). Do not `--resume` until the owner is gone. |
| 86 | Network | Retry the same command after provider health recovers. Do not widen `--limit`. |
| 130 | Interrupted | Re-run the same name without `--resume` for a fresh bounded smoke, or `--resume` only when continuing the same incomplete occurrence. |

Capture before changing code:

```powershell
Get-Content -Path reports\logs\bioetl.log -Tail 80
.\.venv-win\Scripts\python.exe -m bioetl report list --pipeline <NAME> --limit 5
.\.venv-win\Scripts\python.exe -m bioetl run-manifest show <RUN-ID>
```

Canonical application logs are JSON lines at `reports/logs/bioetl.log`.

After a product fix, re-run **only** the failed pipeline (and any later wave
that consumed its Gold) with the same flags. Do not raise tech-debt budgets to
make a smoke pass.

## Verification

For each successful entity run:

1. Exit code `0`.
1. `pipeline-run-report.json` exists under
   `reports/run-reports/pipeline/<NAME>/<run_id>/`.
1. `bioetl report list --pipeline <NAME> --limit 5` does not show
   `REPORT MISSING` for that `run_id`.
1. `bioetl run-manifest show <run_id>` returns the same occurrence.

For each successful composite run:

1. Seed report exists for the seed pipeline `run_id`.
1. Optional enricher reports exist when those enrichers ran (nested
   `PipelineRunner.run()` must persist the same report files as standalone
   `bioetl run`).
1. Parent composite report exists under
   `reports/run-reports/pipeline/composite_<entity>/<run_id>/`.

## Rollback

- Bounded smokes write Silver/Gold for the processed IDs. There is no
  `bioetl rollback`. If a smoke corrupted a table, follow
  [Data Recovery](data-recovery.md) or rebuild that pipeline with an explicit
  `--run-type rebuild --yes` **after** isolating the data root.
- Do not delete `data/**` or `reports/**` without
  [Retention-Sensitive Cleanup](retention-sensitive-cleanup.md).

## Post-incident

- Record pipeline name, `run_id`, exit code, wall time, and whether the
  run-report was `AVAILABLE`.
- If Grafana Run Explorer still shows `REPORT MISSING` after exit `0`, treat it
  as a persistence-path defect, not as a missing ingest.

## Compliance

- This runbook MUST be executed within the priority and runtime profile
  declared in the YAML header (ADR-010 local-only).
- Operators MUST NOT create, edit, rename, move, or delete any `.env` file as
  part of this procedure.
- Operators MUST NOT start `docker-compose.monitoring.yml` unless an operator
  explicitly requested dashboard work.
- Operators SHOULD preserve pipeline name, `run_id`, exit code, and report
  availability in the Verification and Post-incident sections.
- Do not raise tech-debt budgets to make a bounded smoke pass.

## See also

- [Pipeline Catalog](../../04-reference/pipeline-catalog.md)
- [Running Pipelines](../../03-guides/running-pipelines.md)
- [CLI Reference](../../04-reference/cli.md)
- [Run reports](../../04-reference/reports/run-reports.md)
- [Run Manifest Inspection](run-manifest-inspection.md)
