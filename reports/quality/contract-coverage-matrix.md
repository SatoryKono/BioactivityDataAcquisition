# Contract Coverage Matrix

- snapshot_date: 2026-06-18
- row_count: 27
- gold_enabled_count: 27
- covered_gold_enabled_count: 27
- missing_gold_enabled_count: 0
- excluded_count: 0

| pipeline_name | layer | contract_ref | gold_enabled | parity_status | strict | properties | required | pk_fields | tests | missing_surfaces |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | --- |
| `chembl_activity` | `gold` | `chembl.activity` | True | `covered` | True | 72 | 7 | `activity_id` | 21 | - |
| `chembl_assay` | `gold` | `chembl.assay` | True | `covered` | True | 42 | 6 | `assay_id` | 12 | - |
| `chembl_assay_parameters` | `gold` | `chembl.assay_parameters` | True | `covered` | True | 26 | 8 | `assay_param_id` | 6 | - |
| `chembl_cell_line` | `gold` | `chembl.cell_line` | True | `covered` | True | 16 | 7 | `cell_id` | 5 | - |
| `chembl_compound_record` | `gold` | `chembl.compound_record` | True | `covered` | True | 12 | 9 | `record_id` | 5 | - |
| `chembl_molecule` | `gold` | `chembl.molecule` | True | `covered` | True | 57 | 6 | `molecule_id` | 6 | - |
| `chembl_protein_class` | `gold` | `chembl.protein_class` | True | `covered` | True | 15 | 6 | `protein_class_id` | 15 | - |
| `chembl_publication` | `gold` | `chembl.publication` | True | `covered` | True | 30 | 7 | `publication_id` | 62 | - |
| `chembl_publication_similarity` | `gold` | `chembl.publication_similarity` | True | `covered` | True | 14 | 8 | `sim_id` | 4 | - |
| `chembl_publication_term` | `gold` | `chembl.publication_term` | True | `covered` | True | 10 | 8 | `publication_id, term, term_type` | 8 | - |
| `chembl_subcellular_fraction` | `gold` | `chembl.subcellular_fraction` | True | `covered` | True | 8 | 6 | `subcellular_fraction` | 6 | - |
| `chembl_target` | `gold` | `chembl.target` | True | `covered` | True | 32 | 6 | `target_id` | 15 | - |
| `chembl_target_component` | `gold` | `chembl.target_component` | True | `covered` | True | 16 | 6 | `component_id` | 4 | - |
| `chembl_target_protein_classification` | `gold` | `chembl.target_protein_classification` | True | `covered` | True | 45 | 7 | `entity_id` | 7 | - |
| `chembl_tissue` | `gold` | `chembl.tissue` | True | `covered` | True | 11 | 7 | `tissue_id` | 6 | - |
| `composite_activity` | `gold` | `composite.activity` | True | `covered` | True | 21 | 6 | `entity_id` | 21 | - |
| `composite_assay` | `gold` | `composite.assay` | True | `covered` | True | 15 | 6 | `entity_id` | 12 | - |
| `composite_molecule` | `gold` | `composite.molecule` | True | `covered` | True | 12 | 6 | `entity_id` | 6 | - |
| `composite_publication` | `gold` | `composite.publication` | True | `covered` | True | 15 | 7 | `entity_id` | 62 | - |
| `composite_target` | `gold` | `composite.target` | True | `covered` | True | 41 | 6 | `entity_id` | 15 | - |
| `crossref_publication` | `gold` | `crossref.publication` | True | `covered` | True | 51 | 9 | `doi` | 62 | - |
| `openalex_publication` | `gold` | `openalex.publication` | True | `covered` | True | 53 | 10 | `openalex_id` | 62 | - |
| `pubchem_compound` | `gold` | `pubchem.compound` | True | `covered` | True | 39 | 6 | `molecule_id` | 7 | - |
| `pubmed_publication` | `gold` | `pubmed.publication` | True | `covered` | True | 66 | 9 | `pmid` | 62 | - |
| `semanticscholar_publication` | `gold` | `semanticscholar.publication` | True | `covered` | True | 54 | 9 | `paper_id` | 62 | - |
| `uniprot_idmapping` | `gold` | `uniprot.idmapping` | True | `covered` | True | 19 | 7 | `target_id` | 12 | - |
| `uniprot_protein` | `gold` | `uniprot.protein` | True | `covered` | True | 97 | 6 | `accession` | 16 | - |
