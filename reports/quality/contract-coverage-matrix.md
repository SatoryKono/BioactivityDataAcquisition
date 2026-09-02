# Contract Coverage Matrix

- schema_version: `contract-coverage-matrix-v3`
- snapshot_date: 2026-09-02
- row_count: 27
- gold_enabled_count: 27
- gold_contract_available_count: 27
- covered_gold_enabled_count: 27
- missing_gold_enabled_count: 0
- constraint_completeness_missing_count: 0
- golden_test_evidence_count: 27
- excluded_count: 0

## Metric semantics

- `gold_enabled` is the effective runtime state of `pipeline.sink.gold.enabled` after hierarchical configuration resolution; an omitted `enabled` value defaults to `true`. Do not confuse this with unrelated flags such as `filters.input_filter.enabled`.
- `gold_contract_available` is independent contract/schema availability across five governance surfaces: contract YAML + registry entry + gold schema source + published artifact + Pandera declaration, **and** requires gold strict validation declaration (v3).
- Contract or Pandera schema availability must not be inferred from `gold_enabled`, and runtime enablement must not be inferred from `gold_contract_available`.
- Disabled Gold rows remain in the matrix with `parity_status=excluded` and `exclusion_reason=gold_runtime_disabled`; their contract artifacts are not reported as missing solely because runtime output is disabled.

| pipeline_name | layer | contract_ref | gold_enabled | gold_contract_available | parity_status | constraint_status | strict | properties | required | checks | pk_fields | tests | golden | missing_surfaces | missing_constraints |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | --- |
| `chembl_activity` | `gold` | `chembl.activity` | True | True | `covered` | `covered` | True | 72 | 7 | 0 | `activity_id, entity_id` | 24 | 2 | - | - |
| `chembl_assay` | `gold` | `chembl.assay` | True | True | `covered` | `covered` | True | 42 | 6 | 0 | `assay_id, entity_id` | 14 | 2 | - | - |
| `chembl_assay_parameters` | `gold` | `chembl.assay_parameters` | True | True | `covered` | `covered` | True | 26 | 8 | 0 | `assay_param_id, entity_id` | 6 | 2 | - | - |
| `chembl_cell_line` | `gold` | `chembl.cell_line` | True | True | `covered` | `covered` | True | 16 | 7 | 0 | `cell_id, entity_id` | 5 | 2 | - | - |
| `chembl_compound_record` | `gold` | `chembl.compound_record` | True | True | `covered` | `covered` | True | 12 | 9 | 0 | `entity_id, record_id` | 5 | 2 | - | - |
| `chembl_molecule` | `gold` | `chembl.molecule` | True | True | `covered` | `covered` | True | 57 | 6 | 0 | `entity_id, molecule_id` | 6 | 2 | - | - |
| `chembl_protein_class` | `gold` | `chembl.protein_class` | True | True | `covered` | `covered` | True | 15 | 6 | 0 | `entity_id, protein_class_id` | 15 | 2 | - | - |
| `chembl_publication` | `gold` | `chembl.publication` | True | True | `covered` | `covered` | True | 30 | 8 | 0 | `entity_id, publication_id` | 65 | 2 | - | - |
| `chembl_publication_similarity` | `gold` | `chembl.publication_similarity` | True | True | `covered` | `covered` | True | 14 | 8 | 0 | `entity_id, sim_id` | 4 | 2 | - | - |
| `chembl_publication_term` | `gold` | `chembl.publication_term` | True | True | `covered` | `covered` | True | 10 | 8 | 0 | `entity_id, publication_id, term, term_type` | 9 | 2 | - | - |
| `chembl_subcellular_fraction` | `gold` | `chembl.subcellular_fraction` | True | True | `covered` | `covered` | True | 8 | 6 | 0 | `entity_id, subcellular_fraction` | 7 | 2 | - | - |
| `chembl_target` | `gold` | `chembl.target` | True | True | `covered` | `covered` | True | 32 | 6 | 0 | `entity_id, target_id` | 17 | 2 | - | - |
| `chembl_target_component` | `gold` | `chembl.target_component` | True | True | `covered` | `covered` | True | 16 | 6 | 0 | `component_id, entity_id` | 4 | 2 | - | - |
| `chembl_target_protein_classification` | `gold` | `chembl.target_protein_classification` | True | True | `covered` | `covered` | True | 45 | 7 | 0 | `entity_id` | 7 | 2 | - | - |
| `chembl_tissue` | `gold` | `chembl.tissue` | True | True | `covered` | `covered` | True | 11 | 7 | 0 | `entity_id, tissue_id` | 6 | 2 | - | - |
| `composite_activity` | `gold` | `composite.activity` | True | True | `covered` | `covered` | True | 21 | 6 | 0 | `entity_id` | 24 | 2 | - | - |
| `composite_assay` | `gold` | `composite.assay` | True | True | `covered` | `covered` | True | 17 | 6 | 0 | `entity_id` | 14 | 2 | - | - |
| `composite_molecule` | `gold` | `composite.molecule` | True | True | `covered` | `covered` | True | 12 | 6 | 0 | `entity_id` | 6 | 2 | - | - |
| `composite_publication` | `gold` | `composite.publication` | True | True | `covered` | `covered` | True | 15 | 7 | 0 | `entity_id` | 65 | 2 | - | - |
| `composite_target` | `gold` | `composite.target` | True | True | `covered` | `covered` | True | 41 | 6 | 0 | `entity_id` | 17 | 2 | - | - |
| `crossref_publication` | `gold` | `crossref.publication` | True | True | `covered` | `covered` | True | 51 | 9 | 0 | `doi, entity_id` | 65 | 2 | - | - |
| `openalex_publication` | `gold` | `openalex.publication` | True | True | `covered` | `covered` | True | 53 | 10 | 0 | `entity_id, openalex_id` | 65 | 2 | - | - |
| `pubchem_compound` | `gold` | `pubchem.compound` | True | True | `covered` | `covered` | True | 39 | 6 | 0 | `entity_id, molecule_id` | 7 | 2 | - | - |
| `pubmed_publication` | `gold` | `pubmed.publication` | True | True | `covered` | `covered` | True | 66 | 9 | 0 | `entity_id, pmid` | 65 | 2 | - | - |
| `semanticscholar_publication` | `gold` | `semanticscholar.publication` | True | True | `covered` | `covered` | True | 54 | 9 | 0 | `entity_id, paper_id` | 65 | 2 | - | - |
| `uniprot_idmapping` | `gold` | `uniprot.idmapping` | True | True | `covered` | `covered` | True | 19 | 7 | 0 | `entity_id, target_id` | 13 | 2 | - | - |
| `uniprot_protein` | `gold` | `uniprot.protein` | True | True | `covered` | `covered` | True | 97 | 6 | 0 | `accession, entity_id` | 17 | 2 | - | - |
