______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# VCR Test Tasks

> **Status:** Historical verification artifact (non-normative).
> Use this report as dated evidence only; current policy source of truth is
> `configs/quality/integration_vcr_policy.yaml`,
> `docs/03-guides/testing.md`, `configs/quality/test_matrix.yaml`, and active
> ADRs.

*Generated: 2026-02-17 | Sync workflow Prompt 5 (vcr-tests)*

## Summary

| Provider        | Cassettes | Integration Tests (VCR) | Integration Tests (respx/mock) | E2E Tests (VCR) | Pipeline Configs | Gaps                                          |
| --------------- | --------- | ----------------------- | ------------------------------ | --------------- | ---------------- | --------------------------------------------- |
| chembl          | 22        | 7                       | 0                              | 13+             | 15               | 8 entities missing pipeline integration tests |
| pubchem         | 4         | 0                       | 0                              | 3               | 1                | No VCR-backed integration tests               |
| pubmed          | 5         | 0 (respx only)          | 2                              | 5               | 1                | All cassettes used by E2E only                |
| crossref        | 5         | 0 (respx only)          | 9                              | 0               | 1                | No VCR-backed integration or E2E tests        |
| openalex        | 7         | 7                       | 0                              | 0               | 1                | No E2E pipeline tests                         |
| semanticscholar | 6         | 6                       | 0                              | 0               | 1                | No E2E pipeline tests                         |
| uniprot         | 10        | 4                       | 0                              | 3               | 2                | 0                                             |
| multi-provider  | 1         | 0                       | 0                              | 1               | --               | 0                                             |
| *root-level*    | 3         | 0                       | 0                              | 3               | --               | Potential orphan cassettes                    |

### Provider Totals

- **Total VCR cassettes:** 63
- **Total integration test files with VCR:** 12
- **Total E2E test files with VCR:** 14
- **Pipeline configs (non-composite):** 22

______________________________________________________________________

## Detailed Cassette Inventory

### chembl/ (22 cassettes)

| Cassette                                                                           | Used By                                       | Status |
| ---------------------------------------------------------------------------------- | --------------------------------------------- | ------ |
| `TestChEMBLIntegration.test-chembl-extract-transform-load.yaml`                    | E2E `test-full-pipeline.py`                   | OK     |
| `TestChEMBLPipelineE2E.test-chembl_activity-full-run.yaml`                         | E2E `test-chembl_activity-e2e.py`             | OK     |
| `TestChemblActivityPipeline.test-chembl_activity-error-handling.yaml`              | Integration `test-chembl_activity.py`         | OK     |
| `TestChemblAdapter.test-fetch-activities.yaml`                                     | Integration `test-chembl.py`                  | OK     |
| `TestChemblAdapter.test-get-entity-count.yaml`                                     | Integration `test-chembl.py`                  | OK     |
| `TestChemblAdapter.test-health_check.yaml`                                         | Integration `test-chembl.py`                  | OK     |
| `TestChemblCellLinePipeline.test-chembl_cell_line-happy-path.yaml`                 | Integration `test-chembl_cell_line.py`        | OK     |
| `TestChemblCellLinePipeline.test-chembl_cell_line-source-fields.yaml`              | Integration `test-chembl_cell_line.py`        | OK     |
| `TestChemblCompoundRecordPipeline.test-chembl_compound_record-error-handling.yaml` | Integration `test-chembl_compound_record.py`  | OK     |
| `TestChemblCompoundRecordPipeline.test-chembl_compound_record-happy-path.yaml`     | Integration `test-chembl_compound_record.py`  | OK     |
| `TestChemblTargetComponentPipeline.test-chembl_target_component-happy-path.yaml`   | Integration `test-chembl_target_component.py` | OK     |
| `test-chembl_assay-confidence-score.yaml`                                          | E2E `test-chembl_assay-e2e.py`                | OK     |
| `test-chembl_assay-full-cycle.yaml`                                                | E2E `test-chembl_assay-e2e.py`                | OK     |
| `test-chembl_assay-metadata-fields.yaml`                                           | E2E `test-chembl_assay-e2e.py`                | OK     |
| `test-chembl_molecule-full-cycle.yaml`                                             | E2E `test-chembl_molecule-e2e.py`             | OK     |
| `test-chembl_molecule-structural-fields.yaml`                                      | E2E `test-chembl_molecule-e2e.py`             | OK     |
| `test-chembl_publication-full-cycle.yaml`                                          | E2E `test-chembl_publication-e2e.py`          | OK     |
| `test-chembl_publication-metadata-fields.yaml`                                     | E2E `test-chembl_publication-e2e.py`          | OK     |
| `test-chembl_target-cross-references.yaml`                                         | E2E `test-chembl_target-e2e.py`               | OK     |
| `test-chembl_target-full-cycle.yaml`                                               | E2E `test-chembl_target-e2e.py`               | OK     |
| `test-parallel-independent-pipelines.yaml`                                         | E2E `test-advanced-scenarios-e2e.py`          | OK     |
| `test-pipeline-isolation.yaml`                                                     | E2E `test-advanced-scenarios-e2e.py`          | OK     |
| `test-rerun-same-pipeline-twice.yaml`                                              | E2E `test-advanced-scenarios-e2e.py`          | OK     |

### pubchem/ (4 cassettes)

| Cassette                                       | Used By                                             | Status                                |
| ---------------------------------------------- | --------------------------------------------------- | ------------------------------------- |
| `test-pubchem_compound-full-cycle.yaml`        | E2E `test-pubchem_compound-e2e.py`                  | OK                                    |
| `test-pubchem_compound-pipeline.yaml`          | E2E `test-pubchem_compound-e2e.py` / root-level dup | VERIFY - duplicate at root            |
| `test-pubchem_compound-query-filter.yaml`      | E2E `test-pubchem_compound-e2e.py`                  | OK                                    |
| `test-pubchem_compound-structural-fields.yaml` | E2E `test-pubchem_compound-e2e.py`                  | VERIFY - uses `cid` field in API body |

### pubmed/ (5 cassettes)

| Cassette                                             | Used By                                               | Status                     |
| ---------------------------------------------------- | ----------------------------------------------------- | -------------------------- |
| `test-fetch-publications.yaml`                       | E2E `test-pubmed_publication-e2e.py`                  | OK                         |
| `test-health_check.yaml`                             | E2E `test-pubmed_publication-e2e.py` / root-level dup | VERIFY - duplicate at root |
| `test-pubmed_publication-classification-fields.yaml` | E2E `test-pubmed_publication-e2e.py`                  | OK                         |
| `test-pubmed_publication-date-fields.yaml`           | E2E `test-pubmed_publication-e2e.py`                  | OK                         |
| `test-pubmed_publication-full-cycle.yaml`            | E2E `test-pubmed_publication-e2e.py`                  | OK                         |
| `test-pubmed_publication-identifier-fields.yaml`     | E2E `test-pubmed_publication-e2e.py`                  | OK                         |
| `test-pubmed_publication-journal-fields.yaml`        | E2E `test-pubmed_publication-e2e.py`                  | OK                         |

### crossref/ (5 cassettes)

| Cassette                             | Used By                              | Status |
| ------------------------------------ | ------------------------------------ | ------ |
| `test-crossref-batch-fetch.yaml`     | **ORPHAN** - no test references this | ORPHAN |
| `test-crossref-fetch-by-doi.yaml`    | **ORPHAN** - no test references this | ORPHAN |
| `test-crossref-health_check.yaml`    | **ORPHAN** - no test references this | ORPHAN |
| `test-crossref-search-by-title.yaml` | **ORPHAN** - no test references this | ORPHAN |
| `works-batch.yaml`                   | **ORPHAN** - no test references this | ORPHAN |

> **Note:** `test-crossref.py` uses `respx` mocking exclusively, not VCR cassettes. All 5 CrossRef cassettes appear to be orphaned.

### openalex/ (7 cassettes)

| Cassette                                                                | Used By                       | Status |
| ----------------------------------------------------------------------- | ----------------------------- | ------ |
| `TestOpenAlexAdapterIntegration.test-fetch-filtered-batch-dois.yaml`    | Integration `test-adapter.py` | OK     |
| `TestOpenAlexAdapterIntegration.test-fetch-filtered-by-doi.yaml`        | Integration `test-adapter.py` | OK     |
| `TestOpenAlexAdapterIntegration.test-fetch-filtered-with-fallback.yaml` | Integration `test-adapter.py` | OK     |
| `TestOpenAlexAdapterIntegration.test-fetch-with-query.yaml`             | Integration `test-adapter.py` | OK     |
| `TestOpenAlexAdapterIntegration.test-health_check.yaml`                 | Integration `test-adapter.py` | OK     |
| `TestOpenAlexAdapterIntegration.test-title-only-lookup.yaml`            | Integration `test-adapter.py` | OK     |
| `TestOpenAlexAdapterRateLimiting.test-rate-limiting-not-exceeded.yaml`  | Integration `test-adapter.py` | OK     |

### semanticscholar/ (6 cassettes)

| Cassette                                                                       | Used By                               | Status |
| ------------------------------------------------------------------------------ | ------------------------------------- | ------ |
| `TestSemanticScholarAdapterIntegration.test-fetch-batch-dois.yaml`             | Integration `test-semanticscholar.py` | OK     |
| `TestSemanticScholarAdapterIntegration.test-fetch-by-doi.yaml`                 | Integration `test-semanticscholar.py` | OK     |
| `TestSemanticScholarAdapterIntegration.test-fetch-filtered-with-fallback.yaml` | Integration `test-semanticscholar.py` | OK     |
| `TestSemanticScholarAdapterIntegration.test-fetch-with-query.yaml`             | Integration `test-semanticscholar.py` | OK     |
| `TestSemanticScholarAdapterIntegration.test-health_check.yaml`                 | Integration `test-semanticscholar.py` | OK     |
| `TestSemanticScholarAdapterIntegration.test-title-only-lookup.yaml`            | Integration `test-semanticscholar.py` | OK     |

### uniprot/ (10 cassettes)

| Cassette                                                      | Used By                                 | Status |
| ------------------------------------------------------------- | --------------------------------------- | ------ |
| `TestUniProtAdapterIntegration.test-fetch-proteins.yaml`      | Integration `test-uniprot.py`           | OK     |
| `TestUniProtAdapterIntegration.test-health_check.yaml`        | Integration `test-uniprot.py`           | OK     |
| `TestUniProtClientIntegration.test-fetch-proteins.yaml`       | **ORPHAN** - no matching test class     | ORPHAN |
| `TestUniProtClientIntegration.test-health_check.yaml`         | **ORPHAN** - no matching test class     | ORPHAN |
| `TestUniProtIDMappingIntegration.test-health_check.yaml`      | Integration `test-uniprot_idmapping.py` | OK     |
| `TestUniProtIDMappingIntegration.test-map-mixed-results.yaml` | Integration `test-uniprot_idmapping.py` | OK     |
| `TestUniProtIDMappingIntegration.test-map-multiple-ids.yaml`  | Integration `test-uniprot_idmapping.py` | OK     |
| `TestUniProtIDMappingIntegration.test-map-not-found-id.yaml`  | Integration `test-uniprot_idmapping.py` | OK     |
| `TestUniProtIDMappingIntegration.test-map-single-id.yaml`     | Integration `test-uniprot_idmapping.py` | OK     |
| `test-uniprot_protein-full-cycle.yaml`                        | E2E `test-uniprot_protein-e2e.py`       | OK     |
| `test-uniprot_protein-metadata-fields.yaml`                   | E2E `test-uniprot_protein-e2e.py`       | OK     |
| `test-uniprot_protein-sequence-fields.yaml`                   | E2E `test-uniprot_protein-e2e.py`       | OK     |

> **Observed-value coverage note:** offline non-ChEMBL vocabulary governance
> now also depends on the curated Bronze fixtures under
> `tests/fixtures/bronze/openalex/publication/`,
> `tests/fixtures/bronze/crossref/publication/`,
> `tests/fixtures/bronze/pubmed/publication/`,
> `tests/fixtures/bronze/semanticscholar/publication/`,
> `tests/fixtures/bronze/uniprot/protein/`, and
> `tests/fixtures/bronze/uniprot/idmapping/`. In particular,
> `sample_edge_nested_vocab_2026-05-05.jsonl`,
> `sample_edge_structured_payloads_2026-05-12.jsonl`,
> `sample_edge_publication_types_mesh_2026-05-05.jsonl`,
> `sample_edge_publication_types_citations_2026-05-05.jsonl`,
> `sample_edge_semantic_payloads_2026-05-12.jsonl`, and
> `sample_edge_statuses_2026-05-05.jsonl` are the authoritative offline inputs
> for non-ChEMBL observed-value inventory checks.

### multi-provider/ (1 cassette)

| Cassette                                      | Used By                              | Status |
| --------------------------------------------- | ------------------------------------ | ------ |
| `test-chembl-and-uniprot-sequential-run.yaml` | E2E `test-advanced-scenarios-e2e.py` | OK     |

### Root-level (3 cassettes)

| Cassette                                      | Used By                                    | Status           |
| --------------------------------------------- | ------------------------------------------ | ---------------- |
| `test-chembl-and-uniprot-sequential-run.yaml` | **DUPLICATE** of `multi-provider/` version | ORPHAN/DUPLICATE |
| `test-health_check.yaml`                      | **DUPLICATE** of `pubmed/` version         | ORPHAN/DUPLICATE |
| `test-pubchem_compound-pipeline.yaml`         | **DUPLICATE** of `pubchem/` version        | ORPHAN/DUPLICATE |

______________________________________________________________________

## Tasks

### [RECORD] New cassettes needed

#### ChEMBL - Missing entity integration tests

Pipeline configs exist for 15 ChEMBL entities but only 4 have dedicated integration pipeline tests (activity, cell-line, compound-record, target-component). The following entities lack VCR-backed integration/E2E pipeline tests:

- [ ] `chembl/assay-parameters` -- has pipeline config `configs/entities/chembl/assay_parameters.yaml` and transformer `assay-parameters-transformer.py`, but no integration test or VCR cassette
- [ ] `chembl/protein-class` -- has pipeline config and transformer, no integration test
- [ ] `chembl/publication-similarity` -- has pipeline config and transformer, no integration test
- [ ] `chembl/subcellular-fraction` -- has pipeline config and transformer, no integration test
- [ ] `chembl/tissue` -- has pipeline config and transformer, no integration test

#### ChEMBL - Skipped VCR tests needing cassettes

- [ ] `chembl/chembl_activity-filtered.yaml` -- `test-activity-extraction-params.py::test-filtered-api-request` is `@pytest.mark.skip` pending cassette recording
- [ ] `chembl/chembl_assay-filtered.yaml` -- `test-assay-extraction-params.py::test-assay-filtered-api-request` is `@pytest.mark.skip` pending cassette recording

#### CrossRef - No VCR-backed tests at all

- [ ] `crossref/publication-pipeline` -- CrossRef publication pipeline (`configs/entities/crossref/publication.yaml`) has no E2E VCR test; adapter tests use `respx` only
- [ ] `crossref/adapter-integration` -- Consider migrating respx tests to VCR for consistency with other providers

#### OpenAlex - Missing E2E pipeline test

- [ ] `openalex/publication-pipeline` -- OpenAlex publication pipeline (`configs/entities/openalex/publication.yaml`) has adapter-level VCR tests but no E2E full-pipeline test

#### Semantic Scholar - Missing E2E pipeline test

- [ ] `semanticscholar/publication-pipeline` -- Semantic Scholar publication pipeline (`configs/entities/semanticscholar/publication.yaml`) has adapter-level VCR tests but no E2E full-pipeline test

#### UniProt - ID Mapping pipeline test

- [ ] `uniprot/idmapping-pipeline` -- UniProt ID mapping pipeline (`configs/entities/uniprot/idmapping.yaml`) has adapter-level VCR tests but no E2E full-pipeline test

______________________________________________________________________

### [UPDATE] Cassettes to refresh

#### PubChem: `cid` to `molecule-id` field rename

The PubChem transformer (`pubchem/transformer.py`) now uses `molecule-id` as the canonical field name, falling back to `cid` for backward compatibility (line 166-168):

```python
cid = record.get("cid")
if cid is None:
    cid = record.get("molecule-id")
```

The `entity-mapper.py` emits both `"molecule-id"` and `"cid"` fields in the output dict. Existing cassettes use raw PubChem API responses which return `cid` at the REST API level. **No cassette update is needed** for the rename itself because the adapter handles the mapping internally. However:

- [ ] `pubchem/test-pubchem_compound-pipeline.yaml` -- Verify cassette still works with current entity-mapper that produces `molecule-id` as primary key. Consider re-recording if test assertions reference `cid` instead of `molecule-id`.
- [ ] `pubchem/test-pubchem_compound-structural-fields.yaml` -- Same verification needed for `molecule-id` field mapping.

#### PubChem: Extended physicochemical properties

The PubChem transformer now extracts 30+ additional fields (computed descriptors, stereochemistry counts, 3D properties) that were not in earlier versions. Cassettes may not have response data for all these fields.

- [ ] `pubchem/test-pubchem_compound-full-cycle.yaml` -- Verify cassette responses include data for new physicochemical property fields (xlogp, tpsa, complexity, stereo counts, 3D properties). Re-record if extended coverage is desired.

#### UniProt: Extended extraction fields

The UniProt transformer now extracts taxonomy lineage, GO annotations, PTM features, isoform data, and reaction data (visible in `test-uniprot-pipeline.py::test-transform-extracts-new-fields`). E2E cassettes may need updating.

- [ ] `uniprot/test-uniprot_protein-full-cycle.yaml` -- Verify cassette contains records with GO terms, PTM features, isoforms, and reactions. Re-record with a protein that has rich annotation (e.g., P00533/EGFR).
- [ ] `uniprot/test-uniprot_protein-metadata-fields.yaml` -- Verify new taxonomy fields (superkingdom, phylum, genus) are present in cassette response.
- [ ] `uniprot/test-uniprot_protein-sequence-fields.yaml` -- Check if structural feature fields (topology, transmembrane, signal-peptide) are in cassette response.

#### CrossRef: Author ORCID field name anomaly

A search through the CrossRef extractors reveals `authenticated-ormolecule-id` in `author-extractors.py` (line 73), which appears to be a corrupted field name (should be `authenticated-orcid`). If cassettes are re-recorded, this should be investigated.

- [ ] `crossref/` -- Investigate `authenticated-ormolecule-id` vs `authenticated-orcid` field name in `author-extractors.py` (possible artifact of a global rename). Affects cassette response field matching.

#### OpenAlex/Semantic Scholar: `pmmolecule-id` field anomaly

Similar corruption found in `openalex/extractors.py` (line 431-439) and `semanticscholar/extractors.py` (line 53) where `pmmolecule-id` appears instead of `pmcid`.

- [ ] `openalex/` -- Investigate `pmmolecule-id` vs `pmcid` field name in extractors. Ensure cassettes and test assertions use the correct field name.
- [ ] `semanticscholar/` -- Same investigation for `pmmolecule-id` in extractors.

______________________________________________________________________

### [VERIFY] Cassettes to validate

- [ ] `pubchem/test-pubchem_compound-pipeline.yaml` -- Duplicate exists at root level (`tests/fixtures/vcr/test-pubchem_compound-pipeline.yaml`). Verify which one is actually loaded and remove the unused duplicate.
- [ ] `pubmed/test-health_check.yaml` -- Duplicate exists at root level. Verify which is used.
- [ ] `multi-provider/test-chembl-and-uniprot-sequential-run.yaml` -- Duplicate exists at root level. E2E conftest maps to `multi-provider/` dir.
- [ ] `uniprot/TestUniProtClientIntegration.test-fetch-proteins.yaml` -- Orphan cassette. No test class named `TestUniProtClientIntegration` found in current tests (class was likely renamed to `TestUniProtAdapterIntegration`).
- [ ] `uniprot/TestUniProtClientIntegration.test-health_check.yaml` -- Same orphan issue as above.
- [ ] `crossref/test-crossref-batch-fetch.yaml` -- Orphan cassette. All CrossRef tests use `respx`, not VCR.
- [ ] `crossref/test-crossref-fetch-by-doi.yaml` -- Orphan cassette.
- [ ] `crossref/test-crossref-health_check.yaml` -- Orphan cassette.
- [ ] `crossref/test-crossref-search-by-title.yaml` -- Orphan cassette.
- [ ] `crossref/works-batch.yaml` -- Orphan cassette.

______________________________________________________________________

### Missing Integration Tests

| Provider        | Entity                 | Pipeline Config                      | Transformer                             | Integration Test | E2E Test   | Reason                           |
| --------------- | ---------------------- | ------------------------------------ | --------------------------------------- | ---------------- | ---------- | -------------------------------- |
| chembl          | assay-parameters       | `chembl/assay-parameters.yaml`       | `assay-parameters-transformer.py`       | MISSING          | MISSING    | No test coverage for this entity |
| chembl          | protein-class          | `chembl/protein-class.yaml`          | `protein-class-transformer.py`          | MISSING          | MISSING    | No test coverage for this entity |
| chembl          | publication-similarity | `chembl/publication-similarity.yaml` | `publication-similarity-transformer.py` | MISSING          | MISSING    | No test coverage for this entity |
| chembl          | subcellular-fraction   | `chembl/subcellular-fraction.yaml`   | `subcellular-fraction-transformer.py`   | MISSING          | MISSING    | No test coverage for this entity |
| chembl          | tissue                 | `chembl/tissue.yaml`                 | `tissue-transformer.py`                 | MISSING          | MISSING    | No test coverage for this entity |
| chembl          | publication-term       | `chembl/publication-term.yaml`       | `publication-term-transformer.py`       | MISSING          | E2E exists | Integration-level test missing   |
| crossref        | publication            | `crossref/publication.yaml`          | `crossref/transformer.py`               | respx only       | MISSING    | No VCR-backed tests; no E2E test |
| openalex        | publication            | `openalex/publication.yaml`          | `openalex/transformer.py`               | VCR adapter only | MISSING    | E2E full-pipeline test missing   |
| semanticscholar | publication            | `semanticscholar/publication.yaml`   | `semanticscholar/transformer.py`        | VCR adapter only | MISSING    | E2E full-pipeline test missing   |
| uniprot         | idmapping              | `uniprot/idmapping.yaml`             | `uniprot/idmapping-transformer.py`      | VCR adapter only | MISSING    | E2E full-pipeline test missing   |

______________________________________________________________________

### Orphan Cassettes (Cleanup Candidates)

| Provider | Cassette                                                | Reason                                         |
| -------- | ------------------------------------------------------- | ---------------------------------------------- |
| crossref | `test-crossref-batch-fetch.yaml`                        | No VCR-using test references this cassette     |
| crossref | `test-crossref-fetch-by-doi.yaml`                       | No VCR-using test references this cassette     |
| crossref | `test-crossref-health_check.yaml`                       | No VCR-using test references this cassette     |
| crossref | `test-crossref-search-by-title.yaml`                    | No VCR-using test references this cassette     |
| crossref | `works-batch.yaml`                                      | No VCR-using test references this cassette     |
| uniprot  | `TestUniProtClientIntegration.test-fetch-proteins.yaml` | Class renamed to TestUniProtAdapterIntegration |
| uniprot  | `TestUniProtClientIntegration.test-health_check.yaml`   | Class renamed to TestUniProtAdapterIntegration |
| root     | `test-chembl-and-uniprot-sequential-run.yaml`           | Duplicate of `multi-provider/` version         |
| root     | `test-health_check.yaml`                                | Duplicate of `pubmed/` version                 |
| root     | `test-pubchem_compound-pipeline.yaml`                   | Duplicate of `pubchem/` version                |

______________________________________________________________________

### Field Name Anomalies Detected

During analysis, the following suspicious field names were found that appear to be artifacts of an incorrect global rename (`cid` -> `molecule-id` applied too broadly):

| File                                                  | Line    | Found                         | Expected              |
| ----------------------------------------------------- | ------- | ----------------------------- | --------------------- |
| `application/pipelines/crossref/author-extractors.py` | 73      | `authenticated-ormolecule-id` | `authenticated-orcid` |
| `application/pipelines/crossref/author-extractors.py` | 81      | `ormolecule-id`               | `orcid`               |
| `application/pipelines/openalex/extractors.py`        | 195     | `ormolecule-id`               | `orcid`               |
| `application/pipelines/openalex/extractors.py`        | 431-439 | `pmmolecule-id`               | `pmcid`               |
| `application/pipelines/semanticscholar/extractors.py` | 53      | `pmmolecule-id`               | `pmcid`               |

These corrupted field names will cause data to be written with wrong column names, which means **any VCR cassettes that test these fields will need to be re-recorded** after the field names are corrected. This is a **CRITICAL** issue that should be resolved before recording new cassettes.

______________________________________________________________________

## Priority Ordering

### P0 -- Critical (data correctness)

1. Fix corrupted field names (`ormolecule-id`, `pmmolecule-id`) across CrossRef, OpenAlex, and Semantic Scholar extractors
1. Re-record affected cassettes after field name fixes

### P1 -- High (test coverage gaps)

3. Record cassettes for the 2 skipped ChEMBL extraction-params tests
1. Create integration tests for the 5 ChEMBL entities with no test coverage
1. Create E2E tests for CrossRef, OpenAlex, Semantic Scholar, and UniProt ID Mapping pipelines

### P2 -- Medium (cassette maintenance)

6. Verify and update PubChem cassettes for `cid`/`molecule-id` compatibility
1. Verify UniProt cassettes include data for extended taxonomy/GO/PTM fields
1. Clean up 10 orphan cassettes

### P3 -- Low (housekeeping)

9. Remove 3 root-level duplicate cassettes
1. Consider migrating CrossRef respx tests to VCR for consistency
