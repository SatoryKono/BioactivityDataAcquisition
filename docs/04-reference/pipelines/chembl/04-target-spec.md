______________________________________________________________________

Version: 1.1.0
Status: Active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-01'

______________________________________________________________________

# ChEMBL Target Pipeline Specification

This page documents the current active ChEMBL Target pipeline specification.

Canonical sources:

- [ChEMBL target provider reference](../../providers/chembl/target.md)
- `configs/entities/chembl/target.yaml`

Current specification summary:

- Pipeline config and field names use snake_case.
- Canonical identifiers and business keys are defined in the entity config.
- Current target payloads use normalized fields such as `target_type`, `organism`, and provider-specific alias resolution configured via `field_aliases`.
- Composite and downstream enrichment behavior is defined in the live entity config and current application code.
- Derived projections now publish `target_protein_synonyms`, `target_gene_synonyms`, `target_ec_numbers`,
  and xref-derived fields `target_xref_pdb_ids`, `target_xref_go_component`, `target_xref_go_function`, `target_xref_go_process`, `target_xref_hgnc_ids`, `target_xref_reactome_ids`, `target_xref_uniprot_ids`.
- `chembl_target` no longer publishes `protein_classifications` or `target_protein_class_*` summary fields.
- `chembl_target_protein_classification` is the authoritative target-level protein-class relation surface.
- `composite_target` remains the canonical fully enriched target surface because
  it projects flattened protein-class summary only after joining the dedicated
  `chembl_target_protein_classification` relation pipeline.
- GO-derived columns use `xref_name`; `PDB`/`PDBe` and `Reactome` retain `xref_id`.
- Missing derived buckets emit `unknown`; raw `target_component_synonyms` and `cross_references` stay forensic JSON.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [target.md](../../providers/chembl/target.md)                                            |
| Gold contract export | [chembl_target_v3.0.json](../../contracts/gold/chembl_target_v3.0.json)                  |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [chembl_target_v3.0.json](../../contracts/gold/chembl_target_v3.0.json)                  |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
