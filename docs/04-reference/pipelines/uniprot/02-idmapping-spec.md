# UniProt ID Mapping Pipeline Specification

> **Status**: Historical deep spec. Current canonical contract lives in
> [../../providers/uniprot/idmapping.md](../../providers/uniprot/idmapping.md)
> and
> [../../../../configs/entities/uniprot/idmapping.yaml](../../../../configs/entities/uniprot/idmapping.yaml).

## Current Canonical Contract Summary

| Parameter | Value |
|-----------|-------|
| Pipeline ID | `uniprot_idmapping` |
| Provider | `uniprot` |
| Entity | `idmapping` |
| Business Primary Keys | `["target_id"]` |
| Silver Format | `delta` |
| Gold Format | `delta` |
| Gold Mode | `scd2` |

## Notes

- Current canonical field names are snake_case, for example `target_id`,
  `uniprot_accession`, `mapping_status`, `organism_scientific`,
  `organism_common`, `taxonomy_id`, `protein_name`, `gene_primary`,
  `sequence_length`, `sequence_mass`.
- This page no longer republishes older hyphenated field tables such as
  `target-id`, `uniprot-accession`, `mapping-status`, or `taxonomy-id` as the
  active contract.
- For filter settings, DQ thresholds, and API flow details, use the provider
  reference and entity config above.
