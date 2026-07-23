______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-23'

______________________________________________________________________

# Cross-Pipeline Contract Facet Matrix

This matrix covers all 27 active pipeline configs. Primary keys, nullability
counts, and Gold contract paths come from
`reports/quality/contract-coverage-matrix.json`. Effective Silver `merge` is
resolved by
`src/bioetl/infrastructure/config/converters.py::_extract_write_modes`, which
uses explicit config or the `SilverWriteMode.MERGE` default. `Required /
nullable` is the published Gold contract field count.

| Pipeline | Primary key | Silver mode | Required / nullable | Gold contract |
| --- | --- | --- | --- | --- |
| `chembl_activity` | `activity_id, entity_id` | `merge` | `7 / 65` | `configs/contracts/chembl/activity.yaml` |
| `chembl_assay` | `assay_id, entity_id` | `merge` | `6 / 36` | `configs/contracts/chembl/assay.yaml` |
| `chembl_assay_parameters` | `assay_param_id, entity_id` | `merge` | `8 / 18` | `configs/contracts/chembl/assay_parameters.yaml` |
| `chembl_cell_line` | `cell_id, entity_id` | `merge` | `7 / 9` | `configs/contracts/chembl/cell_line.yaml` |
| `chembl_compound_record` | `entity_id, record_id` | `merge` | `9 / 3` | `configs/contracts/chembl/compound_record.yaml` |
| `chembl_molecule` | `entity_id, molecule_id` | `merge` | `6 / 51` | `configs/contracts/chembl/molecule.yaml` |
| `chembl_protein_class` | `entity_id, protein_class_id` | `merge` | `6 / 9` | `configs/contracts/chembl/protein_class.yaml` |
| `chembl_publication` | `entity_id, publication_id` | `merge` | `7 / 23` | `configs/contracts/chembl/publication.yaml` |
| `chembl_publication_similarity` | `entity_id, sim_id` | `merge` | `8 / 6` | `configs/contracts/chembl/publication_similarity.yaml` |
| `chembl_publication_term` | `entity_id, publication_id, term, term_type` | `merge` | `8 / 2` | `configs/contracts/chembl/publication_term.yaml` |
| `chembl_subcellular_fraction` | `entity_id, subcellular_fraction` | `merge` | `6 / 2` | `configs/contracts/chembl/subcellular_fraction.yaml` |
| `chembl_target` | `entity_id, target_id` | `merge` | `6 / 26` | `configs/contracts/chembl/target.yaml` |
| `chembl_target_component` | `component_id, entity_id` | `merge` | `6 / 10` | `configs/contracts/chembl/target_component.yaml` |
| `chembl_target_protein_classification` | `entity_id` | `merge` | `7 / 38` | `configs/contracts/chembl/target_protein_classification.yaml` |
| `chembl_tissue` | `entity_id, tissue_id` | `merge` | `7 / 4` | `configs/contracts/chembl/tissue.yaml` |
| `composite_activity` | `entity_id` | `merge` | `6 / 15` | `configs/contracts/composite/activity.yaml` |
| `composite_assay` | `entity_id` | `merge` | `6 / 11` | `configs/contracts/composite/assay.yaml` |
| `composite_molecule` | `entity_id` | `merge` | `6 / 6` | `configs/contracts/composite/molecule.yaml` |
| `composite_publication` | `entity_id` | `merge` | `7 / 8` | `configs/contracts/composite/publication.yaml` |
| `composite_target` | `entity_id` | `merge` | `6 / 35` | `configs/contracts/composite/target.yaml` |
| `crossref_publication` | `doi, entity_id` | `merge` | `9 / 42` | `configs/contracts/crossref/publication.yaml` |
| `openalex_publication` | `entity_id, openalex_id` | `merge` | `10 / 43` | `configs/contracts/openalex/publication.yaml` |
| `pubchem_compound` | `entity_id, molecule_id` | `merge` | `6 / 33` | `configs/contracts/pubchem/compound.yaml` |
| `pubmed_publication` | `entity_id, pmid` | `merge` | `9 / 57` | `configs/contracts/pubmed/publication.yaml` |
| `semanticscholar_publication` | `entity_id, paper_id` | `merge` | `9 / 45` | `configs/contracts/semanticscholar/publication.yaml` |
| `uniprot_idmapping` | `entity_id, target_id` | `merge` | `7 / 12` | `configs/contracts/uniprot/idmapping.yaml` |
| `uniprot_protein` | `accession, entity_id` | `merge` | `6 / 91` | `configs/contracts/uniprot/protein.yaml` |

`tests/architecture/test_documentation_issues_6497_6498_closeout.py` enforces
exact pipeline parity and verifies that every row has primary-key,
nullability-policy, strict-Gold, and contract evidence.
