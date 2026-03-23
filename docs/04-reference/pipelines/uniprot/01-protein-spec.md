# UniProt Protein Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/uniprot/protein.md](../../providers/uniprot/protein.md)
> and
> `configs/entities/uniprot/protein.yaml`.

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `uniprot_protein` |
| Provider | `uniprot` |
| Entity | `protein` |
| Business Primary Keys | `["accession"]` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

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
