# Contract Coverage Matrix

- snapshot_date: 2026-06-18
- row_count: 27
- gold_enabled_count: 27
- covered_gold_enabled_count: 18
- missing_gold_enabled_count: 9
- excluded_count: 0

| pipeline_name | layer | contract_ref | gold_enabled | parity_status | strict | properties | required | pk_fields | tests | missing_surfaces |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | --- |
| `chembl_activity` | `gold` | `chembl.activity` | True | `covered` | True | 72 | 7 | `activity_id` | 37 | - |
| `chembl_assay` | `gold` | `chembl.assay` | True | `covered` | True | 42 | 6 | `assay_id` | 24 | - |
| `chembl_assay_parameters` | `gold` | `chembl.assay_parameters` | True | `covered` | True | 26 | 8 | `assay_param_id` | 12 | - |
| `chembl_cell_line` | `gold` | `chembl.cell_line` | True | `covered` | True | 16 | 7 | `cell_id` | 11 | - |
| `chembl_compound_record` | `gold` | `chembl.compound_record` | True | `covered` | True | 12 | 9 | `record_id` | 7 | - |
| `chembl_molecule` | `gold` | `chembl.molecule` | True | `covered` | True | 57 | 6 | `molecule_id` | 20 | - |
| `chembl_protein_class` | `gold` | `chembl.protein_class` | True | `covered` | True | 15 | 6 | `protein_class_id` | 18 | - |
| `chembl_publication` | `gold` | `chembl.publication` | True | `covered` | True | 30 | 7 | `publication_id` | 79 | - |
| `chembl_publication_similarity` | `gold` | `chembl.publication_similarity` | True | `covered` | True | 14 | 8 | `sim_id` | 6 | - |
| `chembl_publication_term` | `gold` | `chembl.publication_term` | True | `covered` | True | 10 | 8 | `publication_id, term, term_type` | 13 | - |
| `chembl_subcellular_fraction` | `gold` | `chembl.subcellular_fraction` | True | `covered` | True | 8 | 6 | `subcellular_fraction` | 8 | - |
| `chembl_target` | `gold` | `chembl.target` | True | `covered` | True | 32 | 6 | `target_id` | 30 | - |
| `chembl_target_component` | `gold` | `chembl.target_component` | True | `covered` | True | 16 | 6 | `component_id` | 10 | - |
| `chembl_target_protein_classification` | `gold` | `chembl.target_protein_classification` | True | `covered` | True | 45 | 7 | `entity_id` | 8 | - |
| `chembl_tissue` | `gold` | `chembl.tissue` | True | `covered` | True | 11 | 7 | `tissue_id` | 13 | - |
| `composite_activity` | `gold` | `composite.activity` | True | `missing_surfaces` | False | 21 | 6 | `entity_id` | 37 | gold_strict_validation, pandera_contract_source |
| `composite_assay` | `gold` | `composite.assay` | True | `missing_surfaces` | False | 15 | 6 | `entity_id` | 24 | gold_strict_validation, pandera_contract_source |
| `composite_molecule` | `gold` | `composite.molecule` | True | `missing_surfaces` | False | 12 | 6 | `entity_id` | 20 | gold_strict_validation |
| `composite_publication` | `gold` | `composite.publication` | True | `missing_surfaces` | False | 15 | 7 | `entity_id` | 79 | gold_strict_validation, pandera_contract_source |
| `composite_target` | `gold` | `composite.target` | True | `missing_surfaces` | False | 41 | 6 | `entity_id` | 30 | gold_strict_validation, pandera_contract_source |
| `crossref_publication` | `gold` | `crossref.publication` | True | `missing_surfaces` | False | 51 | 9 | `doi` | 79 | gold_strict_validation, pandera_contract_source |
| `openalex_publication` | `gold` | `openalex.publication` | True | `missing_surfaces` | False | 53 | 10 | `openalex_id` | 79 | gold_strict_validation, pandera_contract_source |
| `pubchem_compound` | `gold` | `pubchem.compound` | True | `covered` | True | 39 | 6 | `molecule_id` | 16 | - |
| `pubmed_publication` | `gold` | `pubmed.publication` | True | `missing_surfaces` | False | 66 | 9 | `pmid` | 79 | gold_strict_validation, pandera_contract_source |
| `semanticscholar_publication` | `gold` | `semanticscholar.publication` | True | `missing_surfaces` | False | 54 | 9 | `paper_id` | 79 | gold_strict_validation, pandera_contract_source |
| `uniprot_idmapping` | `gold` | `uniprot.idmapping` | True | `covered` | True | 19 | 7 | `target_id` | 18 | - |
| `uniprot_protein` | `gold` | `uniprot.protein` | True | `covered` | True | 97 | 6 | `accession` | 27 | - |
