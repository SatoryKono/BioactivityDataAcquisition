______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-03'

______________________________________________________________________

# ChEMBL Subcellular Fraction Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/chembl/subcellular-fraction.md](../../providers/chembl/subcellular-fraction.md)
> and
> `configs/entities/chembl/subcellular_fraction.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value                         |
| --------------------- | ----------------------------- |
| Pipeline ID           | `chembl_subcellular_fraction` |
| Provider              | `chembl`                      |
| Entity                | `subcellular_fraction`        |
| Business Primary Keys | `["entity_id"]`               |
| Loading Strategy      | `full_scan_only`              |
| Silver Format         | `delta`                       |
| Gold Format           | `delta`                       |
| Gold Mode             | `scd2`                        |

## Notes

- Current canonical field names are snake_case, for example `entity_id`,
  `assay_subcellular_fraction`, `assay_id`, `target_id`, `assay_type`,
  `assay_organism`.
- This page no longer republishes older dashed labels such as
  `subcellular-fraction`, `assay-count`, or `example-assay-id` as the active
  contract.
- For derived-entity behavior, validation rules, and filter settings, use the
  provider reference and entity config above.

## Contract References

| Artifact             | Link                                                                                                |
| -------------------- | --------------------------------------------------------------------------------------------------- |
| Provider reference   | [subcellular-fraction.md](../../providers/chembl/subcellular-fraction.md)                           |
| Gold contract export | [chembl_subcellular_fraction_v1.0.json](../../contracts/gold/chembl_subcellular_fraction_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                                  |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)            |

## Compliance

| Control                       | Status | Evidence                                                                                            |
| ----------------------------- | ------ | --------------------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`            |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface            |
| Contract linkage              | Pass   | [chembl_subcellular_fraction_v1.0.json](../../contracts/gold/chembl_subcellular_fraction_v1.0.json) |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources                        |
