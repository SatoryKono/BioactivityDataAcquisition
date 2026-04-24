______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# UniProt Protein Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/uniprot/protein.md](../../providers/uniprot/protein.md)
> and
> `configs/entities/uniprot/protein.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value             |
| --------------------- | ----------------- |
| Pipeline ID           | `uniprot_protein` |
| Provider              | `uniprot`         |
| Entity                | `protein`         |
| Business Primary Keys | `["accession"]`   |
| Silver Format         | `delta`           |
| Gold Format           | `delta`           |
| Gold Mode             | `scd2`            |

## Notes

- Current canonical field names are snake_case, for example `accession`,
  `entry_name`, `protein_name`, `protein_ec_numbers`, `gene_primary`,
  `taxonomy_id`, `sequence_length`, `sequence_mass`, `chembl_ids`,
  `drugbank_ids`.
- This page no longer republishes older API-shape and hyphenated labels such as
  `protein-name`, `gene-synonyms`, `taxonomy-id`, `sequence-mass`, or
  `chembl-ids` as the active contract.
- For DQ rules, cross-reference coverage, and implementation details, use the
  provider reference and entity config above.

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [protein.md](../../providers/uniprot/protein.md)                                         |
| Gold contract export | [uniprot_protein_v1.0.json](../../contracts/gold/uniprot_protein_v1.0.json)              |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [uniprot_protein_v1.0.json](../../contracts/gold/uniprot_protein_v1.0.json)              |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
