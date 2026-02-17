# Composite Target Pipeline

*Updated: 2026-02-17*

## Overview

Builds a composite target table by chaining ChEMBL target data with dependent pipelines
(target component, protein class) and UniProt mappings.

Current target pipeline remains a single-table composite contract, but is expected to follow ADR-035 decomposition strategy when provider-qualified extension volume or lineage complexity requires split contracts.

## Identity

| Field       | Value                                     |
| ----------- | ----------------------------------------- |
| Pipeline ID | `composite_target`                        |
| Provider    | `composite`                               |
| Entity      | `target`                                  |
| Version     | `1.3.0`                                   |
| Config      | `configs/pipelines/composite/target.yaml` |

## Seed and Dependencies

- **Seed**: `chembl_target`
- **Dependencies**:
  - `chembl_target_component` (join on `component_id`)
  - `chembl_protein_class` (chained via `key_source=chembl_target_component`)
  - `uniprot_idmapping` (join on `target_chembl_id`)
  - `uniprot_protein` (chained via `key_source=uniprot_idmapping`)
- **Enrichers**: none

## Outputs

| Layer  | Path                                  |
| ------ | ------------------------------------- |
| Silver | `data/output/silver/composite/target` |
| Gold   | `data/output/gold/composite/target`   |

## Related Configs

- Filters: `configs/filters/entities/composite/target.yaml`

## Related ADRs

- [ADR-026](../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)
- [ADR-028](../../02-architecture/decisions/ADR-028-filter-rules-externalization.md)
- [ADR-035](../../02-architecture/decisions/ADR-035-composite-decomposition-strategy.md)
