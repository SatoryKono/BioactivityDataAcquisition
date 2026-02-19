# Composite Target Pipeline

*Updated: 2026-02-03*

## Overview

Builds a composite target table by chaining ChEMBL target data with dependent pipelines
(target component, protein class) and UniProt mappings.

## Identity

| Field       | Value                                     |
| ----------- | ----------------------------------------- |
| Pipeline ID | `composite-target`                        |
| Provider    | `composite`                               |
| Entity      | `target`                                  |
| Version     | `1.2.0`                                   |
| Config      | `configs/pipelines/composite/target.yaml` |

## Seed and Dependencies

- **Seed**: `chembl-target`
- **Dependencies**:
  - `chembl-target-component` (join on `component-id`)
  - `chembl-protein-class` (chained via `key-source=chembl-target-component`)
  - `uniprot-idmapping` (join on `target-id`)
  - `uniprot-protein` (chained via `key-source=uniprot-idmapping`)
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
