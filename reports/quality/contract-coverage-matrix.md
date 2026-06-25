# Contract Coverage Matrix

- snapshot_date: 2026-06-25
- row_count: 27
- gold_enabled_count: 27
- covered_gold_enabled_count: 27
- missing_gold_enabled_count: 0
- constraint_completeness_missing_count: 0
- golden_test_evidence_count: 27
- excluded_count: 0

| pipeline_name | layer | contract_ref | gold_enabled | parity_status | constraint_status | strict | properties | required | checks | pk_fields | tests | golden | missing_surfaces | missing_constraints |
| --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | --- |
| `chembl_activity` | `gold` | `chembl.activity` | True | `covered` | `covered` | True | 72 | 7 | 0 | `activity_id` | 21 | 2 | - | - |
| `chembl_assay` | `gold` | `chembl.assay` | True | `covered` | `covered` | True | 42 | 6 | 0 | `assay_id` | 12 | 2 | - | - |
| `chembl_assay_parameters` | `gold` | `chembl.assay_parameters` | True | `covered` | `covered` | True | 26 | 8 | 0 | `assay_param_id` | 6 | 2 | - | - |
| `chembl_cell_line` | `gold` | `chembl.cell_line` | True | `covered` | `covered` | True | 16 | 7 | 0 | `cell_id` | 5 | 2 | - | - |
| `chembl_compound_record` | `gold` | `chembl.compound_record` | True | `covered` | `covered` | True | 12 | 9 | 0 | `record_id` | 5 | 2 | - | - |
| `chembl_molecule` | `gold` | `chembl.molecule` | True | `covered` | `covered` | True | 57 | 6 | 0 | `molecule_id` | 6 | 2 | - | - |
| `chembl_protein_class` | `gold` | `chembl.protein_class` | True | `covered` | `covered` | True | 15 | 6 | 0 | `protein_class_id` | 15 | 2 | - | - |
| `chembl_publication` | `gold` | `chembl.publication` | True | `covered` | `covered` | True | 30 | 7 | 0 | `publication_id` | 62 | 2 | - | - |
| `chembl_publication_similarity` | `gold` | `chembl.publication_similarity` | True | `covered` | `covered` | True | 14 | 8 | 0 | `sim_id` | 4 | 2 | - | - |
| `chembl_publication_term` | `gold` | `chembl.publication_term` | True | `covered` | `covered` | True | 10 | 8 | 0 | `publication_id, term, term_type` | 8 | 2 | - | - |
| `chembl_subcellular_fraction` | `gold` | `chembl.subcellular_fraction` | True | `covered` | `covered` | True | 8 | 6 | 0 | `subcellular_fraction` | 6 | 2 | - | - |
| `chembl_target` | `gold` | `chembl.target` | True | `covered` | `covered` | True | 32 | 6 | 0 | `target_id` | 15 | 2 | - | - |
| `chembl_target_component` | `gold` | `chembl.target_component` | True | `covered` | `covered` | True | 16 | 6 | 0 | `component_id` | 4 | 2 | - | - |
| `chembl_target_protein_classification` | `gold` | `chembl.target_protein_classification` | True | `covered` | `covered` | True | 45 | 7 | 0 | `entity_id` | 7 | 2 | - | - |
| `chembl_tissue` | `gold` | `chembl.tissue` | True | `covered` | `covered` | True | 11 | 7 | 0 | `tissue_id` | 6 | 2 | - | - |
| `composite_activity` | `gold` | `composite.activity` | True | `covered` | `covered` | True | 21 | 6 | 0 | `entity_id` | 21 | 2 | - | - |
| `composite_assay` | `gold` | `composite.assay` | True | `covered` | `covered` | True | 15 | 6 | 0 | `entity_id` | 12 | 2 | - | - |
| `composite_molecule` | `gold` | `composite.molecule` | True | `covered` | `covered` | True | 12 | 6 | 0 | `entity_id` | 6 | 2 | - | - |
| `composite_publication` | `gold` | `composite.publication` | True | `covered` | `covered` | True | 15 | 7 | 0 | `entity_id` | 62 | 2 | - | - |
| `composite_target` | `gold` | `composite.target` | True | `covered` | `covered` | True | 41 | 6 | 0 | `entity_id` | 15 | 2 | - | - |
| `crossref_publication` | `gold` | `crossref.publication` | True | `covered` | `covered` | True | 51 | 9 | 0 | `doi` | 62 | 2 | - | - |
| `openalex_publication` | `gold` | `openalex.publication` | True | `covered` | `covered` | True | 53 | 10 | 0 | `openalex_id` | 62 | 2 | - | - |
| `pubchem_compound` | `gold` | `pubchem.compound` | True | `covered` | `covered` | True | 39 | 6 | 0 | `molecule_id` | 7 | 2 | - | - |
| `pubmed_publication` | `gold` | `pubmed.publication` | True | `covered` | `covered` | True | 66 | 9 | 0 | `pmid` | 62 | 2 | - | - |
| `semanticscholar_publication` | `gold` | `semanticscholar.publication` | True | `covered` | `covered` | True | 54 | 9 | 0 | `paper_id` | 62 | 2 | - | - |
| `uniprot_idmapping` | `gold` | `uniprot.idmapping` | True | `covered` | `covered` | True | 19 | 7 | 0 | `target_id` | 12 | 2 | - | - |
| `uniprot_protein` | `gold` | `uniprot.protein` | True | `covered` | `covered` | True | 97 | 6 | 0 | `accession` | 16 | 2 | - | - |
