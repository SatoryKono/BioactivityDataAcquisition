______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# UniProt ID Mapping Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/uniprot/idmapping.md](../../providers/uniprot/idmapping.md)
> and
> `configs/entities/uniprot/idmapping.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value               |
| --------------------- | ------------------- |
| Pipeline ID           | `uniprot_idmapping` |
| Provider              | `uniprot`           |
| Entity                | `idmapping`         |
| Business Primary Keys | `["target_id"]`     |
| Silver Format         | `delta`             |
| Gold Format           | `delta`             |
| Gold Mode             | `scd2`              |

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

## Contract References

| Artifact             | Link                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Provider reference   | [idmapping.md](../../providers/uniprot/idmapping.md)                                     |
| Gold contract export | [uniprot_idmapping_v1.0.json](../../contracts/gold/uniprot_idmapping_v1.0.json)          |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                       |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md) |

## Compliance

| Control                       | Status | Evidence                                                                                 |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified` |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface |
| Contract linkage              | Pass   | [uniprot_idmapping_v1.0.json](../../contracts/gold/uniprot_idmapping_v1.0.json)          |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources             |
