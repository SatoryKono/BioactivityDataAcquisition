______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-03'

______________________________________________________________________

# ChEMBL Assay Parameters Pipeline Specification

> **Status**: Canonical compact spec summary. Current detailed contract lives in
> [../../providers/chembl/assay-parameters.md](../../providers/chembl/assay-parameters.md)
> and
> `configs/entities/chembl/assay_parameters.yaml`.

## Current Canonical Contract Summary

| Parameter             | Value                     |
| --------------------- | ------------------------- |
| Pipeline ID           | `chembl_assay_parameters` |
| Provider              | `chembl`                  |
| Entity                | `assay_parameters`        |
| Business Primary Keys | `["assay_param_id"]`      |
| Silver Format         | `delta`                   |
| Gold Format           | `delta`                   |
| Gold Mode             | `scd2`                    |

## Notes

- Current canonical field names are snake_case, for example `assay_param_id`,
  `assay_id`, `type`, `relation`, `value`, `units`, `text_value`, `comments`,
  `standard_type`, `standard_relation`, `standard_value`, `standard_units`,
  `standard_text_value`.
- This page no longer republishes older dashed labels such as `assay-param-id`,
  `assay-id`, `text-value`, `standard-type`, or `standard-text-value` as the
  active contract.
- For required Gold fields, input filtering, and validation rules, use the
  provider reference and entity config above.

## Contract References

| Artifact             | Link                                                                                        |
| -------------------- | ------------------------------------------------------------------------------------------- |
| Provider reference   | [assay-parameters.md](../../providers/chembl/assay-parameters.md)                           |
| Gold contract export | [chembl_assay_parameters_v1.0.json](../../contracts/gold/chembl_assay_parameters_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                          |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)    |

## Compliance

| Control                       | Status | Evidence                                                                                    |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`    |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface    |
| Contract linkage              | Pass   | [chembl_assay_parameters_v1.0.json](../../contracts/gold/chembl_assay_parameters_v1.0.json) |
| Published-page role           | Pass   | Canonical compact summary is explicitly bounded by current canonical sources                |
