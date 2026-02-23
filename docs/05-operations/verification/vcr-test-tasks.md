# VCR Test Tasks

*Generated: 2026-02-17 | Sync workflow Prompt 5 (vcr-tests)*

## Summary

| Provider | Cassettes | Integration Tests (VCR) | Integration Tests (respx/mock) | E2E Tests (VCR) | Pipeline Configs | Gaps |
|----------|-----------|------------------------|-------------------------------|-----------------|------------------|------|
| chembl | 22 | 7 | 0 | 13+ | 15 | 8 entities missing pipeline integration tests |
| pubchem | 4 | 0 | 0 | 3 | 1 | No VCR-backed integration tests |
| pubmed | 5 | 0 (respx only) | 2 | 5 | 1 | All cassettes used by E2E only |
| crossref | 5 | 0 (respx only) | 9 | 0 | 1 | No VCR-backed integration or E2E tests |
| openalex | 7 | 7 | 0 | 0 | 1 | No E2E pipeline tests |
| semanticscholar | 6 | 6 | 0 | 0 | 1 | No E2E pipeline tests |
| uniprot | 10 | 4 | 0 | 3 | 2 | 0 |
| multi-provider | 1 | 0 | 0 | 1 | -- | 0 |
| *root-level* | 3 | 0 | 0 | 3 | -- | Potential orphan cassettes |

### Provider Totals

- **Total VCR cassettes:** 63
- **Total integration test files with VCR:** 12
- **Total E2E test files with VCR:** 14
- **Pipeline configs (non-composite):** 22

---

## Detailed Cassette Inventory

### chembl/ (22 cassettes)

| Cassette | Used By | Status |
|----------|---------|--------|
| `TestChEMBLIntegration.test_chembl_extract_transform_load.yaml` | E2E `test_full_pipeline.py` | OK |
| `TestChEMBLPipelineE2E.test_chembl_activity_full_run.yaml` | E2E `test_chembl_activity_e2e.py` | OK |
| `TestChemblActivityPipeline.test_chembl_activity_error_handling.yaml` | Integration `test_chembl_activity.py` | OK |
| `TestChemblAdapter.test_fetch_activities.yaml` | Integration `test_chembl.py` | OK |
| `TestChemblAdapter.test_get_entity_count.yaml` | Integration `test_chembl.py` | OK |
| `TestChemblAdapter.test_health_check.yaml` | Integration `test_chembl.py` | OK |
| `TestChemblCellLinePipeline.test_chembl_cell_line_happy_path.yaml` | Integration `test_chembl_cell_line.py` | OK |
| `TestChemblCellLinePipeline.test_chembl_cell_line_source_fields.yaml` | Integration `test_chembl_cell_line.py` | OK |
| `TestChemblCompoundRecordPipeline.test_chembl_compound_record_error_handling.yaml` | Integration `test_chembl_compound_record.py` | OK |
| `TestChemblCompoundRecordPipeline.test_chembl_compound_record_happy_path.yaml` | Integration `test_chembl_compound_record.py` | OK |
| `TestChemblTargetComponentPipeline.test_chembl_target_component_happy_path.yaml` | Integration `test_chembl_target_component.py` | OK |
| `test_chembl_assay_confidence_score.yaml` | E2E `test_chembl_assay_e2e.py` | OK |
| `test_chembl_assay_full_cycle.yaml` | E2E `test_chembl_assay_e2e.py` | OK |
| `test_chembl_assay_metadata_fields.yaml` | E2E `test_chembl_assay_e2e.py` | OK |
| `test_chembl_molecule_full_cycle.yaml` | E2E `test_chembl_molecule_e2e.py` | OK |
| `test_chembl_molecule_structural_fields.yaml` | E2E `test_chembl_molecule_e2e.py` | OK |
| `test_chembl_publication_full_cycle.yaml` | E2E `test_chembl_publication_e2e.py` | OK |
| `test_chembl_publication_metadata_fields.yaml` | E2E `test_chembl_publication_e2e.py` | OK |
| `test_chembl_target_cross_references.yaml` | E2E `test_chembl_target_e2e.py` | OK |
| `test_chembl_target_full_cycle.yaml` | E2E `test_chembl_target_e2e.py` | OK |
| `test_parallel_independent_pipelines.yaml` | E2E `test_advanced_scenarios_e2e.py` | OK |
| `test_pipeline_isolation.yaml` | E2E `test_advanced_scenarios_e2e.py` | OK |
| `test_rerun_same_pipeline_twice.yaml` | E2E `test_advanced_scenarios_e2e.py` | OK |

### pubchem/ (4 cassettes)

| Cassette | Used By | Status |
|----------|---------|--------|
| `test_pubchem_compound_full_cycle.yaml` | E2E `test_pubchem_compound_e2e.py` | OK |
| `test_pubchem_compound_pipeline.yaml` | E2E `test_pubchem_compound_e2e.py` / root-level dup | VERIFY - duplicate at root |
| `test_pubchem_compound_query_filter.yaml` | E2E `test_pubchem_compound_e2e.py` | OK |
| `test_pubchem_compound_structural_fields.yaml` | E2E `test_pubchem_compound_e2e.py` | VERIFY - uses `cid` field in API body |

### pubmed/ (5 cassettes)

| Cassette | Used By | Status |
|----------|---------|--------|
| `test_fetch_publications.yaml` | E2E `test_pubmed_publication_e2e.py` | OK |
| `test_health_check.yaml` | E2E `test_pubmed_publication_e2e.py` / root-level dup | VERIFY - duplicate at root |
| `test_pubmed_publication_classification_fields.yaml` | E2E `test_pubmed_publication_e2e.py` | OK |
| `test_pubmed_publication_date_fields.yaml` | E2E `test_pubmed_publication_e2e.py` | OK |
| `test_pubmed_publication_full_cycle.yaml` | E2E `test_pubmed_publication_e2e.py` | OK |
| `test_pubmed_publication_identifier_fields.yaml` | E2E `test_pubmed_publication_e2e.py` | OK |
| `test_pubmed_publication_journal_fields.yaml` | E2E `test_pubmed_publication_e2e.py` | OK |

### crossref/ (5 cassettes)

| Cassette | Used By | Status |
|----------|---------|--------|
| `test_crossref_batch_fetch.yaml` | **ORPHAN** - no test references this | ORPHAN |
| `test_crossref_fetch_by_doi.yaml` | **ORPHAN** - no test references this | ORPHAN |
| `test_crossref_health_check.yaml` | **ORPHAN** - no test references this | ORPHAN |
| `test_crossref_search_by_title.yaml` | **ORPHAN** - no test references this | ORPHAN |
| `works_batch.yaml` | **ORPHAN** - no test references this | ORPHAN |

> **Note:** `test_crossref.py` uses `respx` mocking exclusively, not VCR cassettes. All 5 CrossRef cassettes appear to be orphaned.

### openalex/ (7 cassettes)

| Cassette | Used By | Status |
|----------|---------|--------|
| `TestOpenAlexAdapterIntegration.test_fetch_filtered_batch_dois.yaml` | Integration `test_adapter.py` | OK |
| `TestOpenAlexAdapterIntegration.test_fetch_filtered_by_doi.yaml` | Integration `test_adapter.py` | OK |
| `TestOpenAlexAdapterIntegration.test_fetch_filtered_with_fallback.yaml` | Integration `test_adapter.py` | OK |
| `TestOpenAlexAdapterIntegration.test_fetch_with_query.yaml` | Integration `test_adapter.py` | OK |
| `TestOpenAlexAdapterIntegration.test_health_check.yaml` | Integration `test_adapter.py` | OK |
| `TestOpenAlexAdapterIntegration.test_title_only_lookup.yaml` | Integration `test_adapter.py` | OK |
| `TestOpenAlexAdapterRateLimiting.test_rate_limiting_not_exceeded.yaml` | Integration `test_adapter.py` | OK |

### semanticscholar/ (6 cassettes)

| Cassette | Used By | Status |
|----------|---------|--------|
| `TestSemanticScholarAdapterIntegration.test_fetch_batch_dois.yaml` | Integration `test_semanticscholar.py` | OK |
| `TestSemanticScholarAdapterIntegration.test_fetch_by_doi.yaml` | Integration `test_semanticscholar.py` | OK |
| `TestSemanticScholarAdapterIntegration.test_fetch_filtered_with_fallback.yaml` | Integration `test_semanticscholar.py` | OK |
| `TestSemanticScholarAdapterIntegration.test_fetch_with_query.yaml` | Integration `test_semanticscholar.py` | OK |
| `TestSemanticScholarAdapterIntegration.test_health_check.yaml` | Integration `test_semanticscholar.py` | OK |
| `TestSemanticScholarAdapterIntegration.test_title_only_lookup.yaml` | Integration `test_semanticscholar.py` | OK |

### uniprot/ (10 cassettes)

| Cassette | Used By | Status |
|----------|---------|--------|
| `TestUniProtAdapterIntegration.test_fetch_proteins.yaml` | Integration `test_uniprot.py` | OK |
| `TestUniProtAdapterIntegration.test_health_check.yaml` | Integration `test_uniprot.py` | OK |
| `TestUniProtClientIntegration.test_fetch_proteins.yaml` | **ORPHAN** - no matching test class | ORPHAN |
| `TestUniProtClientIntegration.test_health_check.yaml` | **ORPHAN** - no matching test class | ORPHAN |
| `TestUniProtIDMappingIntegration.test_health_check.yaml` | Integration `test_uniprot_idmapping.py` | OK |
| `TestUniProtIDMappingIntegration.test_map_mixed_results.yaml` | Integration `test_uniprot_idmapping.py` | OK |
| `TestUniProtIDMappingIntegration.test_map_multiple_ids.yaml` | Integration `test_uniprot_idmapping.py` | OK |
| `TestUniProtIDMappingIntegration.test_map_not_found_id.yaml` | Integration `test_uniprot_idmapping.py` | OK |
| `TestUniProtIDMappingIntegration.test_map_single_id.yaml` | Integration `test_uniprot_idmapping.py` | OK |
| `test_uniprot_protein_full_cycle.yaml` | E2E `test_uniprot_protein_e2e.py` | OK |
| `test_uniprot_protein_metadata_fields.yaml` | E2E `test_uniprot_protein_e2e.py` | OK |
| `test_uniprot_protein_sequence_fields.yaml` | E2E `test_uniprot_protein_e2e.py` | OK |

### multi-provider/ (1 cassette)

| Cassette | Used By | Status |
|----------|---------|--------|
| `test_chembl_and_uniprot_sequential_run.yaml` | E2E `test_advanced_scenarios_e2e.py` | OK |

### Root-level (3 cassettes)

| Cassette | Used By | Status |
|----------|---------|--------|
| `test_chembl_and_uniprot_sequential_run.yaml` | **DUPLICATE** of `multi_provider/` version | ORPHAN/DUPLICATE |
| `test_health_check.yaml` | **DUPLICATE** of `pubmed/` version | ORPHAN/DUPLICATE |
| `test_pubchem_compound_pipeline.yaml` | **DUPLICATE** of `pubchem/` version | ORPHAN/DUPLICATE |

---

## Tasks

### [RECORD] New cassettes needed

#### ChEMBL - Missing entity integration tests

Pipeline configs exist for 15 ChEMBL entities but only 4 have dedicated integration pipeline tests (activity, cell-line, compound-record, target-component). The following entities lack VCR-backed integration/E2E pipeline tests:

- [ ] `chembl/assay_parameters` -- has pipeline config `configs/pipelines/chembl/assay_parameters.yaml` and transformer `assay_parameters_transformer.py`, but no integration test or VCR cassette
- [ ] `chembl/protein_class` -- has pipeline config and transformer, no integration test
- [ ] `chembl/publication_similarity` -- has pipeline config and transformer, no integration test
- [ ] `chembl/subcellular_fraction` -- has pipeline config and transformer, no integration test
- [ ] `chembl/tissue` -- has pipeline config and transformer, no integration test

#### ChEMBL - Skipped VCR tests needing cassettes

- [ ] `chembl/chembl_activity_filtered.yaml` -- `test_activity_extraction_params.py::test_filtered_api_request` is `@pytest.mark.skip` pending cassette recording
- [ ] `chembl/chembl_assay_filtered.yaml` -- `test_assay_extraction_params.py::test_assay_filtered_api_request` is `@pytest.mark.skip` pending cassette recording

#### CrossRef - No VCR-backed tests at all

- [ ] `crossref/publication-pipeline` -- CrossRef publication pipeline (`configs/pipelines/crossref/publication.yaml`) has no E2E VCR test; adapter tests use `respx` only
- [ ] `crossref/adapter-integration` -- Consider migrating respx tests to VCR for consistency with other providers

#### OpenAlex - Missing E2E pipeline test

- [ ] `openalex/publication-pipeline` -- OpenAlex publication pipeline (`configs/pipelines/openalex/publication.yaml`) has adapter-level VCR tests but no E2E full-pipeline test

#### Semantic Scholar - Missing E2E pipeline test

- [ ] `semanticscholar/publication-pipeline` -- Semantic Scholar publication pipeline (`configs/pipelines/semanticscholar/publication.yaml`) has adapter-level VCR tests but no E2E full-pipeline test

#### UniProt - ID Mapping pipeline test

- [ ] `uniprot/idmapping_pipeline` -- UniProt ID mapping pipeline (`configs/pipelines/uniprot/idmapping.yaml`) has adapter-level VCR tests but no E2E full-pipeline test

---

### [UPDATE] Cassettes to refresh

#### PubChem: `cid` to `molecule-id` field rename

The PubChem transformer (`pubchem/transformer.py`) now uses `molecule-id` as the canonical field name, falling back to `cid` for backward compatibility (line 166-168):
```python
cid = record.get("cid")
if cid is None:
    cid = record.get("molecule-id")
```

The `entity_mapper.py` emits both `"molecule-id"` and `"cid"` fields in the output dict. Existing cassettes use raw PubChem API responses which return `cid` at the REST API level. **No cassette update is needed** for the rename itself because the adapter handles the mapping internally. However:

- [ ] `pubchem/test_pubchem_compound_pipeline.yaml` -- Verify cassette still works with current entity-mapper that produces `molecule-id` as primary key. Consider re-recording if test assertions reference `cid` instead of `molecule-id`.
- [ ] `pubchem/test_pubchem_compound_structural_fields.yaml` -- Same verification needed for `molecule-id` field mapping.

#### PubChem: Extended physicochemical properties

The PubChem transformer now extracts 30+ additional fields (computed descriptors, stereochemistry counts, 3D properties) that were not in earlier versions. Cassettes may not have response data for all these fields.

- [ ] `pubchem/test_pubchem_compound_full_cycle.yaml` -- Verify cassette responses include data for new physicochemical property fields (xlogp, tpsa, complexity, stereo counts, 3D properties). Re-record if extended coverage is desired.

#### UniProt: Extended extraction fields

The UniProt transformer now extracts taxonomy lineage, GO annotations, PTM features, isoform data, and reaction data (visible in `test_uniprot_pipeline.py::test_transform_extracts_new_fields`). E2E cassettes may need updating.

- [ ] `uniprot/test_uniprot_protein_full_cycle.yaml` -- Verify cassette contains records with GO terms, PTM features, isoforms, and reactions. Re-record with a protein that has rich annotation (e.g., P00533/EGFR).
- [ ] `uniprot/test_uniprot_protein_metadata_fields.yaml` -- Verify new taxonomy fields (superkingdom, phylum, genus) are present in cassette response.
- [ ] `uniprot/test_uniprot_protein_sequence_fields.yaml` -- Check if structural feature fields (topology, transmembrane, signal-peptide) are in cassette response.

#### CrossRef: Author ORCID field name anomaly

A search through the CrossRef extractors reveals `authenticated-ormolecule-id` in `author_extractors.py` (line 73), which appears to be a corrupted field name (should be `authenticated-orcid`). If cassettes are re-recorded, this should be investigated.

- [ ] `crossref/` -- Investigate `authenticated-ormolecule-id` vs `authenticated-orcid` field name in `author_extractors.py` (possible artifact of a global rename). Affects cassette response field matching.

#### OpenAlex/Semantic Scholar: `pmmolecule-id` field anomaly

Similar corruption found in `openalex/extractors.py` (line 431-439) and `semanticscholar/extractors.py` (line 53) where `pmmolecule-id` appears instead of `pmcid`.

- [ ] `openalex/` -- Investigate `pmmolecule-id` vs `pmcid` field name in extractors. Ensure cassettes and test assertions use the correct field name.
- [ ] `semanticscholar/` -- Same investigation for `pmmolecule-id` in extractors.

---

### [VERIFY] Cassettes to validate

- [ ] `pubchem/test_pubchem_compound_pipeline.yaml` -- Duplicate exists at root level (`tests/fixtures/vcr/test_pubchem_compound_pipeline.yaml`). Verify which one is actually loaded and remove the unused duplicate.
- [ ] `pubmed/test_health_check.yaml` -- Duplicate exists at root level. Verify which is used.
- [ ] `multi_provider/test_chembl_and_uniprot_sequential_run.yaml` -- Duplicate exists at root level. E2E conftest maps to `multi_provider/` dir.
- [ ] `uniprot/TestUniProtClientIntegration.test_fetch_proteins.yaml` -- Orphan cassette. No test class named `TestUniProtClientIntegration` found in current tests (class was likely renamed to `TestUniProtAdapterIntegration`).
- [ ] `uniprot/TestUniProtClientIntegration.test_health_check.yaml` -- Same orphan issue as above.
- [ ] `crossref/test_crossref_batch_fetch.yaml` -- Orphan cassette. All CrossRef tests use `respx`, not VCR.
- [ ] `crossref/test_crossref_fetch_by_doi.yaml` -- Orphan cassette.
- [ ] `crossref/test_crossref_health_check.yaml` -- Orphan cassette.
- [ ] `crossref/test_crossref_search_by_title.yaml` -- Orphan cassette.
- [ ] `crossref/works_batch.yaml` -- Orphan cassette.

---

### Missing Integration Tests

| Provider | Entity | Pipeline Config | Transformer | Integration Test | E2E Test | Reason |
|----------|--------|----------------|-------------|------------------|----------|--------|
| chembl | assay-parameters | `chembl/assay_parameters.yaml` | `assay_parameters_transformer.py` | MISSING | MISSING | No test coverage for this entity |
| chembl | protein-class | `chembl/protein_class.yaml` | `protein_class_transformer.py` | MISSING | MISSING | No test coverage for this entity |
| chembl | publication-similarity | `chembl/publication_similarity.yaml` | `publication_similarity_transformer.py` | MISSING | MISSING | No test coverage for this entity |
| chembl | subcellular-fraction | `chembl/subcellular_fraction.yaml` | `subcellular_fraction_transformer.py` | MISSING | MISSING | No test coverage for this entity |
| chembl | tissue | `chembl/tissue.yaml` | `tissue_transformer.py` | MISSING | MISSING | No test coverage for this entity |
| chembl | publication-term | `chembl/publication_term.yaml` | `publication_term_transformer.py` | MISSING | E2E exists | Integration-level test missing |
| crossref | publication | `crossref/publication.yaml` | `crossref/transformer.py` | respx only | MISSING | No VCR-backed tests; no E2E test |
| openalex | publication | `openalex/publication.yaml` | `openalex/transformer.py` | VCR adapter only | MISSING | E2E full-pipeline test missing |
| semanticscholar | publication | `semanticscholar/publication.yaml` | `semanticscholar/transformer.py` | VCR adapter only | MISSING | E2E full-pipeline test missing |
| uniprot | idmapping | `uniprot/idmapping.yaml` | `uniprot/idmapping_transformer.py` | VCR adapter only | MISSING | E2E full-pipeline test missing |

---

### Orphan Cassettes (Cleanup Candidates)

| Provider | Cassette | Reason |
|----------|----------|--------|
| crossref | `test_crossref_batch_fetch.yaml` | No VCR-using test references this cassette |
| crossref | `test_crossref_fetch_by_doi.yaml` | No VCR-using test references this cassette |
| crossref | `test_crossref_health_check.yaml` | No VCR-using test references this cassette |
| crossref | `test_crossref_search_by_title.yaml` | No VCR-using test references this cassette |
| crossref | `works_batch.yaml` | No VCR-using test references this cassette |
| uniprot | `TestUniProtClientIntegration.test_fetch_proteins.yaml` | Class renamed to TestUniProtAdapterIntegration |
| uniprot | `TestUniProtClientIntegration.test_health_check.yaml` | Class renamed to TestUniProtAdapterIntegration |
| root | `test_chembl_and_uniprot_sequential_run.yaml` | Duplicate of `multi_provider/` version |
| root | `test_health_check.yaml` | Duplicate of `pubmed/` version |
| root | `test_pubchem_compound_pipeline.yaml` | Duplicate of `pubchem/` version |

---

### Field Name Anomalies Detected

During analysis, the following suspicious field names were found that appear to be artifacts of an incorrect global rename (`cid` -> `molecule-id` applied too broadly):

| File | Line | Found | Expected |
|------|------|-------|----------|
| `application/pipelines/crossref/author_extractors.py` | 73 | `authenticated-ormolecule-id` | `authenticated-orcid` |
| `application/pipelines/crossref/author_extractors.py` | 81 | `ormolecule-id` | `orcid` |
| `application/pipelines/openalex/extractors.py` | 195 | `ormolecule-id` | `orcid` |
| `application/pipelines/openalex/extractors.py` | 431-439 | `pmmolecule-id` | `pmcid` |
| `application/pipelines/semanticscholar/extractors.py` | 53 | `pmmolecule-id` | `pmcid` |

These corrupted field names will cause data to be written with wrong column names, which means **any VCR cassettes that test these fields will need to be re-recorded** after the field names are corrected. This is a **CRITICAL** issue that should be resolved before recording new cassettes.

---

## Priority Ordering

### P0 -- Critical (data correctness)
1. Fix corrupted field names (`ormolecule-id`, `pmmolecule-id`) across CrossRef, OpenAlex, and Semantic Scholar extractors
2. Re-record affected cassettes after field name fixes

### P1 -- High (test coverage gaps)
3. Record cassettes for the 2 skipped ChEMBL extraction-params tests
4. Create integration tests for the 5 ChEMBL entities with no test coverage
5. Create E2E tests for CrossRef, OpenAlex, Semantic Scholar, and UniProt ID Mapping pipelines

### P2 -- Medium (cassette maintenance)
6. Verify and update PubChem cassettes for `cid`/`molecule-id` compatibility
7. Verify UniProt cassettes include data for extended taxonomy/GO/PTM fields
8. Clean up 10 orphan cassettes

### P3 -- Low (housekeeping)
9. Remove 3 root-level duplicate cassettes
10. Consider migrating CrossRef respx tests to VCR for consistency
