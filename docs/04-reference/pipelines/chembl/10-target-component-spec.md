______________________________________________________________________

Version: 1.0.0
Status: Active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-23'

______________________________________________________________________

# ChEMBL Target Component Pipeline Specification

This document describes the current active ChEMBL Target Component pipeline specification.

Canonical sources:

- [ChEMBL target component provider reference](../../providers/chembl/target-component.md)
- `configs/entities/chembl/target_component.yaml`

Current canonical summary:

- Active configs and reference examples use snake_case names.
- Component relationships, identifiers, and alias handling are defined in the current entity config and provider transformer logic.
- Use the provider reference plus the live config as the source of truth for target component fields and loading behavior.

## Contract References

| Artifact             | Link                                                                                        |
| -------------------- | ------------------------------------------------------------------------------------------- |
| Provider reference   | [target-component.md](../../providers/chembl/target-component.md)                           |
| Gold contract export | [chembl_target_component_v1.0.json](../../contracts/gold/chembl_target_component_v1.0.json) |
| Gold schemas index   | [gold-schemas.md](../../contracts/gold-schemas.md)                                          |
| Versioning policy    | [ADR-036](../../../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)    |

## Compliance

| Control                       | Status | Evidence                                                                                    |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------- |
| Metadata                      | Pass   | YAML header contains `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`    |
| Canonical source traceability | Pass   | Page delegates current contract to the linked canonical source and active config surface    |
| Contract linkage              | Pass   | [chembl_target_component_v1.0.json](../../contracts/gold/chembl_target_component_v1.0.json) |
| Published-page role           | Pass   | Historical deep spec or summary is explicitly bounded by current canonical sources          |
