______________________________________________________________________

Version: 1.0.0
Status: Active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-23'

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
- Derived synonym projections now publish `target_protein_synonyms`, `target_gene_synonyms`, and `target_ec_numbers`.
- Missing derived synonym buckets emit `unknown`; raw `target_component_synonyms` stays forensic JSON.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [target.md](../../providers/chembl/target.md)                                            |
| Gold contract export | [chembl_target_v1.0.json](../../contracts/gold/chembl_target_v1.0.json)                  |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [chembl_target_v1.0.json](../../contracts/gold/chembl_target_v1.0.json)                  |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
